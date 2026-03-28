// lib/main.dart
// ─────────────────────────────────────────────────────────────────────────────
// App entry point. Wires up Provider state management and global theming.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/task_provider.dart';
import 'screens/task_list_screen.dart';
import 'widgets/app_theme.dart';

void main() {
  runApp(const TaskManagerApp());
}

class TaskManagerApp extends StatelessWidget {
  const TaskManagerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => TaskProvider(),
      child: MaterialApp(
        title: 'Task Manager',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.dark,
        home: const TaskListScreen(),
      ),
    );
  }
}
