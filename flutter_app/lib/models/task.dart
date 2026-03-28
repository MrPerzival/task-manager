// lib/models/task.dart
// ─────────────────────────────────────────────────────────────────────────────
// Mirrors the backend TaskResponse schema exactly.
// Provides fromJson / toJson / copyWith helpers.

class Task {
  final int id;
  final String title;
  final String description;
  final DateTime? dueDate;
  final String status;       // "To-Do" | "In Progress" | "Done"
  final int? blockedBy;
  final String recurring;    // "None" | "Daily" | "Weekly"

  const Task({
    required this.id,
    required this.title,
    required this.description,
    this.dueDate,
    required this.status,
    this.blockedBy,
    required this.recurring,
  });

  // ── De-serialise from API JSON ─────────────────────────────────────────────
  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id:          json['id'] as int,
      title:       json['title'] as String,
      description: json['description'] as String? ?? '',
      dueDate:     json['due_date'] != null
                     ? DateTime.parse(json['due_date'] as String)
                     : null,
      status:      json['status'] as String,
      blockedBy:   json['blocked_by'] as int?,
      recurring:   json['recurring'] as String? ?? 'None',
    );
  }

  // ── Serialise for POST / PUT body ─────────────────────────────────────────
  Map<String, dynamic> toJson() {
    return {
      'title':       title,
      'description': description,
      'due_date':    dueDate != null
                       ? '${dueDate!.year.toString().padLeft(4, '0')}-'
                         '${dueDate!.month.toString().padLeft(2, '0')}-'
                         '${dueDate!.day.toString().padLeft(2, '0')}'
                       : null,
      'status':      status,
      'blocked_by':  blockedBy,
      'recurring':   recurring,
    };
  }

  Task copyWith({
    int?      id,
    String?   title,
    String?   description,
    DateTime? dueDate,
    bool      clearDueDate = false,
    String?   status,
    int?      blockedBy,
    bool      clearBlockedBy = false,
    String?   recurring,
  }) {
    return Task(
      id:          id          ?? this.id,
      title:       title       ?? this.title,
      description: description ?? this.description,
      dueDate:     clearDueDate  ? null : (dueDate ?? this.dueDate),
      status:      status      ?? this.status,
      blockedBy:   clearBlockedBy ? null : (blockedBy ?? this.blockedBy),
      recurring:   recurring   ?? this.recurring,
    );
  }

  // ── Convenience ───────────────────────────────────────────────────────────
  bool get isDone         => status == 'Done';
  bool get isInProgress   => status == 'In Progress';
  bool get isTodo         => status == 'To-Do';
  bool get isRecurring    => recurring != 'None';

  @override
  String toString() => 'Task(id: $id, title: "$title", status: $status)';
}
