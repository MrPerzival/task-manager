// lib/widgets/empty_state.dart
// ─────────────────────────────────────────────────────────────────────────────
// Reusable empty-state widget shown when the task list is empty.
// Accepts an icon, headline, subtext, and optional action button.

import 'package:flutter/material.dart';
import 'app_theme.dart';

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String headline;
  final String subtext;
  final String? actionLabel;
  final VoidCallback? onAction;

  const EmptyState({
    super.key,
    required this.icon,
    required this.headline,
    required this.subtext,
    this.actionLabel,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // ── Illustrated icon ─────────────────────────────────────────
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: AppTheme.primary.withOpacity(0.08),
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                size: 36,
                color: AppTheme.primary.withOpacity(0.4),
              ),
            ),
            const SizedBox(height: 20),

            // ── Headline ─────────────────────────────────────────────────
            Text(
              headline,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w600,
                color: AppTheme.onSurface,
              ),
            ),
            const SizedBox(height: 8),

            // ── Subtext ──────────────────────────────────────────────────
            Text(
              subtext,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 14,
                color: AppTheme.subtle,
                height: 1.5,
              ),
            ),

            // ── Optional action button ───────────────────────────────────
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: onAction,
                icon: const Icon(Icons.add_rounded, size: 18),
                label: Text(actionLabel!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
