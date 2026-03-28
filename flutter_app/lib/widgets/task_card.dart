// lib/widgets/task_card.dart
// ─────────────────────────────────────────────────────────────────────────────
// Rich task card with visual blocking state, status badge, recurring icon,
// and swipe-to-delete gesture.

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/task.dart';
import 'app_theme.dart';

class TaskCard extends StatelessWidget {
  final Task task;
  final bool isBlocked;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const TaskCard({
    super.key,
    required this.task,
    required this.isBlocked,
    required this.onTap,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Dismissible(
      key: ValueKey('task_${task.id}'),
      direction: DismissDirection.endToStart,
      background: _DeleteBackground(),
      confirmDismiss: (_) => _confirmDelete(context),
      onDismissed: (_) => onDelete(),
      child: Opacity(
        opacity: isBlocked ? 0.45 : 1.0,
        child: Material(
          color: AppTheme.surfaceVar,
          borderRadius: BorderRadius.circular(14),
          child: InkWell(
            onTap: isBlocked ? null : onTap,
            borderRadius: BorderRadius.circular(14),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: isBlocked
                      ? Colors.white.withOpacity(0.04)
                      : Colors.white.withOpacity(0.06),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Row 1: Title + status badge ──────────────────────────
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          task.title,
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: isBlocked
                                ? AppTheme.subtle
                                : AppTheme.onSurface,
                            decoration: task.isDone
                                ? TextDecoration.lineThrough
                                : null,
                            decorationColor: AppTheme.subtle,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 12),
                      _StatusBadge(status: task.status),
                    ],
                  ),

                  // ── Description ──────────────────────────────────────────
                  if (task.description.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      task.description,
                      style: TextStyle(
                        fontSize: 13,
                        color: AppTheme.subtle.withOpacity(0.8),
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],

                  const SizedBox(height: 12),

                  // ── Row 2: Meta chips ─────────────────────────────────────
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      if (task.dueDate != null)
                        _MetaChip(
                          icon: Icons.calendar_today_rounded,
                          label: DateFormat('MMM d, y').format(task.dueDate!),
                          color: _dueDateColor(task.dueDate!),
                        ),
                      if (task.isRecurring)
                        _MetaChip(
                          icon: Icons.loop_rounded,
                          label: task.recurring,
                          color: AppTheme.primary,
                        ),
                      if (isBlocked)
                        _MetaChip(
                          icon: Icons.lock_outline_rounded,
                          label: 'Blocked',
                          color: AppTheme.error,
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Color _dueDateColor(DateTime date) {
    final now = DateTime.now();
    if (date.isBefore(now)) return AppTheme.error;
    if (date.difference(now).inDays <= 2) return AppTheme.warning;
    return AppTheme.subtle;
  }

  Future<bool?> _confirmDelete(BuildContext context) {
    return showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceVar,
        title: const Text('Delete Task'),
        content: Text('Delete "${task.title}"? This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: AppTheme.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}

// ── Sub-widgets ───────────────────────────────────────────────────────────────

class _StatusBadge extends StatelessWidget {
  final String status;
  const _StatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.statusBackground(status),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        status,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: AppTheme.statusColor(status),
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _MetaChip({required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 12, color: color),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 11, color: color)),
      ],
    );
  }
}

class _DeleteBackground extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      alignment: Alignment.centerRight,
      padding: const EdgeInsets.only(right: 20),
      decoration: BoxDecoration(
        color: AppTheme.error.withOpacity(0.15),
        borderRadius: BorderRadius.circular(14),
      ),
      child: const Icon(Icons.delete_outline_rounded, color: AppTheme.error, size: 24),
    );
  }
}
