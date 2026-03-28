// lib/services/task_provider.dart
// ─────────────────────────────────────────────────────────────────────────────
// Central state container (ChangeNotifier).
// Holds the full task list and notifies listeners on every mutation.

import 'package:flutter/material.dart';
import '../models/task.dart';
import 'api_service.dart';

enum LoadState { idle, loading, error }

class TaskProvider extends ChangeNotifier {
  List<Task>  _tasks     = [];
  LoadState   _loadState = LoadState.idle;
  String?     _error;

  // ── Search / filter state ─────────────────────────────────────────────────
  String _searchQuery = '';
  String _statusFilter = '';   // '' means "all"

  List<Task>  get tasks      => _filtered;
  List<Task>  get allTasks   => _tasks;   // unfiltered (for blocked-by dropdown)
  LoadState   get loadState  => _loadState;
  String?     get error      => _error;
  String      get searchQuery   => _searchQuery;
  String      get statusFilter  => _statusFilter;

  // ── Filtered view ─────────────────────────────────────────────────────────
  List<Task> get _filtered {
    return _tasks.where((t) {
      final matchesSearch = _searchQuery.isEmpty ||
          t.title.toLowerCase().contains(_searchQuery.toLowerCase());
      final matchesStatus = _statusFilter.isEmpty || t.status == _statusFilter;
      return matchesSearch && matchesStatus;
    }).toList();
  }

  void setSearch(String query) {
    _searchQuery = query;
    notifyListeners();
  }

  void setStatusFilter(String status) {
    _statusFilter = status;
    notifyListeners();
  }

  // ── Fetch all tasks ────────────────────────────────────────────────────────
  Future<void> loadTasks() async {
    _loadState = LoadState.loading;
    _error = null;
    notifyListeners();

    try {
      _tasks = await ApiService.fetchTasks();
      _loadState = LoadState.idle;
    } on ApiException catch (e) {
      _error = e.message;
      _loadState = LoadState.error;
    } catch (e) {
      _error = e.toString();
      _loadState = LoadState.error;
    }
    notifyListeners();
  }

  // ── Create task ────────────────────────────────────────────────────────────
  /// Returns the created task, or throws ApiException on failure.
  Future<Task> createTask(Task task) async {
    final created = await ApiService.createTask(task);
    // Reload to also pick up any auto-spawned recurring tasks
    await loadTasks();
    return created;
  }

  // ── Update task ────────────────────────────────────────────────────────────
  Future<Task> updateTask(Task task) async {
    final updated = await ApiService.updateTask(task);
    await loadTasks();
    return updated;
  }

  // ── Delete task ────────────────────────────────────────────────────────────
  Future<void> deleteTask(int id) async {
    await ApiService.deleteTask(id);
    _tasks.removeWhere((t) => t.id == id);
    notifyListeners();
  }

  // ── Blocking helper ───────────────────────────────────────────────────────
  /// Returns true if [task] is blocked (its blocker is not Done).
  bool isBlocked(Task task) {
    if (task.blockedBy == null) return false;
    final blocker = _tasks.where((t) => t.id == task.blockedBy).firstOrNull;
    if (blocker == null) return false;   // missing blocker → treat as unblocked
    return !blocker.isDone;
  }
}
