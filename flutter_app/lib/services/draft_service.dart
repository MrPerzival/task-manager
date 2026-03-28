// lib/services/draft_service.dart
// ─────────────────────────────────────────────────────────────────────────────
// Persists form drafts to SharedPreferences so that partially-filled
// task creation/edit forms survive navigation away.
// Key format: "draft_task_<taskId>"  (taskId = 0 for new-task drafts)

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class DraftService {
  static const String _newTaskKey = 'draft_task_new';

  static String _editKey(int taskId) => 'draft_task_$taskId';

  // ── Save draft ─────────────────────────────────────────────────────────────
  static Future<void> saveDraft({
    required bool isNew,
    int? taskId,
    required Map<String, dynamic> data,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final key = isNew ? _newTaskKey : _editKey(taskId!);
    await prefs.setString(key, jsonEncode(data));
  }

  // ── Load draft ─────────────────────────────────────────────────────────────
  static Future<Map<String, dynamic>?> loadDraft({
    required bool isNew,
    int? taskId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final key = isNew ? _newTaskKey : _editKey(taskId!);
    final raw = prefs.getString(key);
    if (raw == null) return null;
    try {
      return jsonDecode(raw) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  // ── Clear draft ────────────────────────────────────────────────────────────
  static Future<void> clearDraft({required bool isNew, int? taskId}) async {
    final prefs = await SharedPreferences.getInstance();
    final key = isNew ? _newTaskKey : _editKey(taskId!);
    await prefs.remove(key);
  }
}
