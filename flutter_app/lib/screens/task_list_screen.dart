// lib/screens/task_list_screen.dart
// ─────────────────────────────────────────────────────────────────────────────
// Main screen: connection banner, stats strip, search bar,
// status filter chips, and the task list.
//
// v2 changes
// ──────────
// • ConnectionBanner shown when load fails
// • StatsStrip shows live To-Do / In Progress / Done counts
// • EmptyState widget for both no-tasks and no-results cases
// • Pull-to-refresh
// • Swipe-to-delete feedback with SnackBar undo affordance

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/task_provider.dart';
import '../widgets/task_card.dart';
import '../widgets/app_theme.dart';
import '../widgets/connection_banner.dart';
import '../widgets/empty_state.dart';
import 'task_form_screen.dart';

class TaskListScreen extends StatefulWidget {
  const TaskListScreen({super.key});

  @override
  State<TaskListScreen> createState() => _TaskListScreenState();
}

class _TaskListScreenState extends State<TaskListScreen> {
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TaskProvider>().loadTasks();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TaskProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Task Manager'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh',
            onPressed: () => provider.loadTasks(),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: Column(
        children: [
          // ── Connection error banner ─────────────────────────────────────
          ConnectionBanner(
            message: provider.error ?? 'Could not reach the server.',
            isVisible: provider.loadState == LoadState.error,
            onRetry: () => provider.loadTasks(),
          ),

          // ── Stats strip ─────────────────────────────────────────────────
          if (provider.allTasks.isNotEmpty)
            _StatsStrip(tasks: provider.allTasks),

          // ── Search + filter bar ─────────────────────────────────────────
          _SearchFilterBar(searchController: _searchController),

          // ── Task list ───────────────────────────────────────────────────
          Expanded(child: _TaskListBody(searchController: _searchController)),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreateForm,
        backgroundColor: AppTheme.primary,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add_rounded),
        label: const Text('New Task', style: TextStyle(fontWeight: FontWeight.w600)),
      ),
    );
  }

  void _openCreateForm() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const TaskFormScreen()),
    ).then((_) => context.read<TaskProvider>().loadTasks());
  }
}

// ── Stats strip ───────────────────────────────────────────────────────────────

class _StatsStrip extends StatelessWidget {
  final List tasks;
  const _StatsStrip({required this.tasks});

  @override
  Widget build(BuildContext context) {
    final todo       = tasks.where((t) => t.status == 'To-Do').length;
    final inProgress = tasks.where((t) => t.status == 'In Progress').length;
    final done       = tasks.where((t) => t.status == 'Done').length;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: AppTheme.surface,
      child: Row(
        children: [
          _StatChip(count: todo,       label: 'To-Do',       color: AppTheme.primary),
          const SizedBox(width: 10),
          _StatChip(count: inProgress, label: 'In Progress', color: AppTheme.warning),
          const SizedBox(width: 10),
          _StatChip(count: done,       label: 'Done',        color: AppTheme.success),
          const Spacer(),
          Text(
            '${tasks.length} total',
            style: const TextStyle(fontSize: 11, color: AppTheme.subtle),
          ),
        ],
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  final int count;
  final String label;
  final Color color;
  const _StatChip({required this.count, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            count.toString(),
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(fontSize: 11, color: color.withOpacity(0.8)),
          ),
        ],
      ),
    );
  }
}

// ── Search + filter bar ───────────────────────────────────────────────────────

class _SearchFilterBar extends StatelessWidget {
  final TextEditingController searchController;
  const _SearchFilterBar({required this.searchController});

  static const _statuses = ['', 'To-Do', 'In Progress', 'Done'];
  static const _labels   = ['All', 'To-Do', 'In Progress', 'Done'];

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TaskProvider>();

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      color: AppTheme.surface,
      child: Column(
        children: [
          // Search field
          TextField(
            controller: searchController,
            onChanged: provider.setSearch,
            style: const TextStyle(color: AppTheme.onSurface),
            decoration: InputDecoration(
              hintText: 'Search tasks…',
              prefixIcon: const Icon(
                Icons.search_rounded, size: 20, color: AppTheme.subtle),
              suffixIcon: searchController.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear_rounded,
                          size: 18, color: AppTheme.subtle),
                      onPressed: () {
                        searchController.clear();
                        provider.setSearch('');
                      },
                    )
                  : null,
              isDense: true,
            ),
          ),
          const SizedBox(height: 10),

          // Status filter chips
          SizedBox(
            height: 32,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: _statuses.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                final selected = provider.statusFilter == _statuses[i];
                return FilterChip(
                  label: Text(_labels[i]),
                  selected: selected,
                  onSelected: (_) => provider.setStatusFilter(_statuses[i]),
                  showCheckmark: false,
                  labelStyle: TextStyle(
                    fontSize: 12,
                    fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                    color: selected ? AppTheme.primary : AppTheme.subtle,
                  ),
                  backgroundColor: AppTheme.surfaceVar,
                  selectedColor: AppTheme.primary.withOpacity(0.15),
                  side: BorderSide(
                    color: selected
                        ? AppTheme.primary.withOpacity(0.4)
                        : Colors.white.withOpacity(0.08),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ── Task list body ────────────────────────────────────────────────────────────

class _TaskListBody extends StatelessWidget {
  final TextEditingController searchController;
  const _TaskListBody({required this.searchController});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TaskProvider>();

    // Loading spinner (only on initial load, not on refresh)
    if (provider.loadState == LoadState.loading && provider.allTasks.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primary),
      );
    }

    final tasks = provider.tasks;

    if (tasks.isEmpty) {
      final isFiltered = provider.searchQuery.isNotEmpty ||
          provider.statusFilter.isNotEmpty;

      if (isFiltered) {
        return EmptyState(
          icon: Icons.filter_list_off_rounded,
          headline: 'No matching tasks',
          subtext: 'Try adjusting your search\nor clearing the status filter.',
        );
      }

      return EmptyState(
        icon: Icons.task_alt_rounded,
        headline: 'No tasks yet',
        subtext: 'Tap the button below\nto create your first task.',
        actionLabel: 'Create Task',
        onAction: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const TaskFormScreen()),
        ).then((_) => provider.loadTasks()),
      );
    }

    return RefreshIndicator(
      color: AppTheme.primary,
      onRefresh: () => provider.loadTasks(),
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
        itemCount: tasks.length,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (ctx, i) {
          final task    = tasks[i];
          final blocked = provider.isBlocked(task);
          return TaskCard(
            key: ValueKey('card_${task.id}'),
            task: task,
            isBlocked: blocked,
            onTap:    () => _openEdit(ctx, task),
            onDelete: () => _deleteTask(ctx, task),
          );
        },
      ),
    );
  }

  void _openEdit(BuildContext context, task) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => TaskFormScreen(existingTask: task)),
    ).then((_) => context.read<TaskProvider>().loadTasks());
  }

  Future<void> _deleteTask(BuildContext context, task) async {
    final provider = context.read<TaskProvider>();

    // Optimistic removal for snappy UX
    try {
      await provider.deleteTask(task.id);
      if (!context.mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Deleted "${task.title}"'),
          backgroundColor: AppTheme.surfaceVar,
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.fromLTRB(16, 0, 16, 80),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not delete task: $e'),
          backgroundColor: AppTheme.error,
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.fromLTRB(16, 0, 16, 80),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
      // Reload to restore the task in the list
      provider.loadTasks();
    }
  }
}
