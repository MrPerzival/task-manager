// lib/services/api_service.dart
// ─────────────────────────────────────────────────────────────────────────────
// HTTP client layer for the Task Manager backend (v2).
//
// Changes from v1
// ───────────────
// • _parseError now handles the v2 error envelope { "error": true, "detail": "..." }
//   as well as the legacy Pydantic v2 list format [ { "msg": "..." } ].
// • ApiConfig class centralises baseUrl so it can be overridden for testing
//   or swapped between dev / staging / prod without touching call sites.
// • Retry logic with exponential back-off on transient network errors (5xx).
// • All timeouts documented and consistent across methods.

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../models/task.dart';

// ── Configuration ─────────────────────────────────────────────────────────────

class ApiConfig {
  /// Base URL of the FastAPI backend.
  ///
  /// • Android emulator  → 10.0.2.2:8000
  /// • iOS simulator     → 127.0.0.1:8000
  /// • Physical device   → your machine's LAN IP, e.g. 192.168.1.10:8000
  /// • Docker Compose    → the service name is resolved by Android emulator
  ///                       the same as above from the host machine.
  static const String baseUrl = 'http://127.0.0.1:8000';

  /// Timeout for read-only requests (GET, DELETE).
  static const Duration readTimeout = Duration(seconds: 15);

  /// Timeout for write requests (POST, PUT).
  /// Must exceed the backend's 2-second processing delay with headroom.
  static const Duration writeTimeout = Duration(seconds: 30);

  /// Number of retry attempts for recoverable errors (503, network hiccups).
  static const int maxRetries = 2;
}

// ── Exception type ────────────────────────────────────────────────────────────

class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException({required this.statusCode, required this.message});

  /// Whether this is a client error (4xx) — not worth retrying.
  bool get isClientError => statusCode >= 400 && statusCode < 500;

  /// Whether this is a server error (5xx) — may be worth retrying.
  bool get isServerError => statusCode >= 500;

  /// Human-readable label for SnackBar / error banners.
  String get userFacingMessage {
    if (statusCode == 0)   return 'Could not reach the server. Check your connection.';
    if (statusCode == 404) return message;
    if (statusCode == 422) return message;
    if (isServerError)     return 'Server error. Please try again later.';
    return message;
  }

  @override
  String toString() => 'ApiException($statusCode): $message';
}

// ── Service ───────────────────────────────────────────────────────────────────

class ApiService {
  static final http.Client _client = http.Client();

  static Map<String, String> get _headers => const {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  // ── Error parsing ─────────────────────────────────────────────────────────
  //
  // v2 backend always returns:  { "error": true, "detail": "<string>" }
  // Pydantic validation errors: { "detail": [ { "msg": "...", "loc": [...] } ] }
  // Fallback: raw response body as the message.

  static ApiException _parseError(http.Response response) {
    try {
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final detail = body['detail'];

      String message;
      if (detail is String) {
        message = detail;
      } else if (detail is List) {
        // Pydantic v2 validation error list
        message = detail
            .whereType<Map>()
            .map((e) => e['msg']?.toString() ?? '')
            .where((s) => s.isNotEmpty)
            .join('; ');
        if (message.isEmpty) message = 'Validation error.';
      } else {
        message = response.body;
      }

      return ApiException(statusCode: response.statusCode, message: message);
    } catch (_) {
      return ApiException(
        statusCode: response.statusCode,
        message: response.body.isEmpty
            ? 'HTTP ${response.statusCode}'
            : response.body,
      );
    }
  }

  // ── Retry wrapper ─────────────────────────────────────────────────────────
  //
  // Retries [fn] up to [ApiConfig.maxRetries] times on:
  //   • SocketException   (no network)
  //   • HttpException     (connection reset)
  //   • 503 responses     (server temporarily unavailable)
  //
  // Client errors (4xx) are never retried.

  static Future<T> _withRetry<T>(Future<T> Function() fn) async {
    int attempts = 0;
    while (true) {
      try {
        return await fn();
      } on ApiException catch (e) {
        if (e.isClientError || attempts >= ApiConfig.maxRetries) rethrow;
        attempts++;
        await Future.delayed(Duration(milliseconds: 500 * attempts));
      } on SocketException catch (e) {
        if (attempts >= ApiConfig.maxRetries) {
          throw ApiException(statusCode: 0, message: 'Network error: ${e.message}');
        }
        attempts++;
        await Future.delayed(Duration(milliseconds: 500 * attempts));
      } catch (e) {
        throw ApiException(statusCode: 0, message: e.toString());
      }
    }
  }

  // ── GET /tasks ─────────────────────────────────────────────────────────────

  static Future<List<Task>> fetchTasks({
    String? status,
    String? search,
  }) async {
    return _withRetry(() async {
      final queryParams = <String, String>{};
      if (status != null && status.isNotEmpty) queryParams['status'] = status;
      if (search  != null && search.isNotEmpty)  queryParams['search'] = search;

      final uri = Uri.parse('${ApiConfig.baseUrl}/tasks')
          .replace(queryParameters: queryParams);

      final response = await _client
          .get(uri, headers: _headers)
          .timeout(ApiConfig.readTimeout);

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data
            .map((e) => Task.fromJson(e as Map<String, dynamic>))
            .toList();
      }
      throw _parseError(response);
    });
  }

  // ── POST /tasks ────────────────────────────────────────────────────────────

  static Future<Task> createTask(Task task) async {
    // No retry on create — idempotency not guaranteed; avoid duplicate inserts.
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}/tasks');
      final response = await _client
          .post(uri, headers: _headers, body: jsonEncode(task.toJson()))
          .timeout(ApiConfig.writeTimeout);

      if (response.statusCode == 201) {
        return Task.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      }
      throw _parseError(response);
    } on ApiException {
      rethrow;
    } on SocketException catch (e) {
      throw ApiException(statusCode: 0, message: 'Network error: ${e.message}');
    } catch (e) {
      throw ApiException(statusCode: 0, message: e.toString());
    }
  }

  // ── PUT /tasks/{id} ────────────────────────────────────────────────────────

  static Future<Task> updateTask(Task task) async {
    // PUT is idempotent per HTTP spec — safe to retry.
    return _withRetry(() async {
      final uri = Uri.parse('${ApiConfig.baseUrl}/tasks/${task.id}');
      final response = await _client
          .put(uri, headers: _headers, body: jsonEncode(task.toJson()))
          .timeout(ApiConfig.writeTimeout);

      if (response.statusCode == 200) {
        return Task.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      }
      throw _parseError(response);
    });
  }

  // ── DELETE /tasks/{id} ────────────────────────────────────────────────────

  static Future<void> deleteTask(int id) async {
    // DELETE is idempotent — safe to retry.
    return _withRetry(() async {
      final uri = Uri.parse('${ApiConfig.baseUrl}/tasks/$id');
      final response = await _client
          .delete(uri, headers: _headers)
          .timeout(ApiConfig.readTimeout);

      if (response.statusCode == 204) return;
      throw _parseError(response);
    });
  }

  // ── Health check ──────────────────────────────────────────────────────────

  /// Pings the backend health endpoint.
  /// Returns true if reachable, false otherwise.
  static Future<bool> isReachable() async {
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}/');
      final response = await _client
          .get(uri, headers: _headers)
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
