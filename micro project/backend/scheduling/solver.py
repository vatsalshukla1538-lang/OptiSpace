"""
solver.py - Constraint Satisfaction Problem (CSP) Timetable Generator for MITS Gwalior.

Milestone 4 Improvements:
1. Pure Python Backtracking CSP solver with Forward Checking (prunes branches with domain wipeout).
2. Most Constrained Variable (MRV) course ordering heuristic (constrained courses scheduled first).
3. Greedy smallest-suitable-room selection (reduces unused seating without claiming global optimality).
4. Performance metrics tracking (recursion calls, backtracks, generation time, validation result).
5. Student group & batch collision handling (prevents overlapping classes for cohorts and sub-batches).
6. Soft-constraint bounded improvement step for reducing student group long gaps.
7. Independent validator that re-verifies every constraint from scratch.
"""

import time

# Shared standard definitions across backend and frontend (in chronological order)
TIME_SLOTS = [
    "09:00-10:00",
    "10:00-11:00",
    "11:00-12:00",
    "12:00-13:00",
    "13:00-14:00",
    "14:00-15:00",
    "15:00-16:00",
    "16:00-17:00",
    "17:00-18:00",
    "01:00-02:00",
    "02:00-03:00",
    "03:00-04:00",
    "04:00-05:00",
    "05:00-06:00",
]

DAYS = ["MON", "TUE", "WED", "THU", "FRI"]

SLOT_INDEX = {
    "09:00-10:00": 0,
    "10:00-11:00": 1,
    "11:00-12:00": 2,
    "12:00-13:00": 3,
    "13:00-14:00": 4,
    "01:00-02:00": 4,
    "14:00-15:00": 5,
    "02:00-03:00": 5,
    "15:00-16:00": 6,
    "03:00-04:00": 6,
    "16:00-17:00": 7,
    "04:00-05:00": 7,
    "17:00-18:00": 8,
    "05:00-06:00": 8,
}


class ScheduleResult(dict):
    """
    Result container returned by the solver.
    Inherits from dict so assignments[course_id] works for backward compatibility,
    while `.sessions` provides the full list of scheduled sessions across all credit hours,
    and `.metrics` holds execution performance counters.
    """
    def __init__(self, sessions, remaining_gaps=None, metrics=None):
        super().__init__()
        self.sessions = sessions
        self.remaining_gaps = remaining_gaps or []
        self.metrics = metrics or {}
        for s in sessions:
            cid = s['course_id']
            if cid not in self:
                self[cid] = (s['room_id'], s['day'], s['time_slot'], s.get('teacher_id'))


def get_candidate_rooms(course, rooms):
    """
    Finds rooms matching course requirements (capacity, room type, and availability).
    Rooms are sorted by (capacity, room_number):
    - Trying the smallest suitable room first reduces unused seating.
    - room_number provides a deterministic tie-breaker.
    Note: This is a greedy heuristic that improves room fit; it does not claim
    to find globally optimal room utilization across all possible combinations.
    """
    matching = []
    for r in rooms:
        if not r.is_available:
            continue
        if r.capacity < course.enrolled_students:
            continue
        if course.requires_lab and r.room_type != 'LAB':
            continue
        if not course.requires_lab and r.room_type != 'LECTURE':
            continue
        matching.append(r)

    # Sort primarily by capacity (smallest suitable room first) and room_number (deterministic)
    matching.sort(key=lambda r: (r.capacity, r.room_number))
    return matching


def compute_course_constraint_score(course, candidate_rooms_map, teacher_availabilities):
    """
    Computes a deterministic constraint score for course ordering (MRV heuristic).
    Courses with higher scores are scheduled earlier in the backtracking search.
    Considers:
    - Lab requirement (scarce specialized lab rooms)
    - Restricted teacher availability windows (fewer free hours)
    - Room scarcity (fewer valid rooms capable of hosting the course)
    - Enrolled students (large classes fit in fewer rooms)
    - Credit hours (more sessions to place)
    - Difficulty (soft constraint for early-day placement)
    """
    # 1. Specialized lab requirement
    score = 150 if course.requires_lab else 0

    # 2. Teacher availability scarcity
    tid = course.teacher_id if course.teacher else None
    avails = teacher_availabilities.get(tid) if tid else None
    if avails is not None:
        total_institution_slots = len(DAYS) * len(TIME_SLOTS)  # 35 slots
        free_slots = len(avails)
        # More points if the teacher has very few available slots
        score += max(0, total_institution_slots - free_slots) * 3

    # 3. Candidate room scarcity
    matching_rooms = candidate_rooms_map.get(course.id, [])
    score += max(0, 10 - len(matching_rooms)) * 10

    # 4. Large class size (enrollment)
    score += min(50, course.enrolled_students)

    # 5. Required weekly sessions (credit hours)
    score += (course.credit_hours or 1) * 5

    # 6. Difficulty
    diff_scores = {'HARD': 20, 'MEDIUM': 10, 'EASY': 0}
    score += diff_scores.get(course.difficulty, 5)

    return score


def groups_clash(group_a, group_b):
    """
    Determines if two student groups/batches clash.
    Returns True if:
    - Same group ID
    - Same group code
    - Parent section and sub-batch relationship (e.g., 'IT-I-A' and 'IT-I-A1')
    Returns False if they are disjoint batches of the same section (e.g., 'IT-I-A1' and 'IT-I-A2').
    """
    if not group_a or not group_b:
        return False
    if group_a.id == group_b.id:
        return True
    code_a = getattr(group_a, 'code', str(group_a))
    code_b = getattr(group_b, 'code', str(group_b))
    if code_a == code_b:
        return True

    # If code_a is a prefix of code_b and code_b continues with batch suffix (e.g. IT-I-A and IT-I-A1)
    # or vice versa:
    if code_a.startswith(code_b) and (len(code_a) == len(code_b) or code_a[len(code_b)] in ('-', '_', '1', '2', '3', '4', 'B', 'b')):
        return True
    if code_b.startswith(code_a) and (len(code_b) == len(code_a) or code_b[len(code_a)] in ('-', '_', '1', '2', '3', '4', 'B', 'b')):
        return True

    return False


def compute_long_gaps(assignments, courses):
    """
    Calculates long gaps for student groups.
    A long gap is defined as at least 3 consecutive empty teaching slots
    between a group's scheduled classes on the same weekday.
    """
    courses_map = {c.id: c for c in courses}
    group_day_slots = {}

    for item in assignments:
        course = courses_map.get(item['course_id'])
        if not course or not course.group_id:
            continue

        gid = course.group_id
        day = item['day']
        slot_idx = SLOT_INDEX.get(item['time_slot'])
        if slot_idx is None:
            continue

        if gid not in group_day_slots:
            group_day_slots[gid] = {}
        if day not in group_day_slots[gid]:
            group_day_slots[gid][day] = []
        group_day_slots[gid][day].append(slot_idx)

    long_gaps = []
    for gid, day_dict in group_day_slots.items():
        sample_course = next((c for c in courses if c.group_id == gid), None)
        group_label = sample_course.group.code if (sample_course and sample_course.group) else f"Group-{gid}"

        for day, slots in day_dict.items():
            sorted_slots = sorted(set(slots))
            for i in range(len(sorted_slots) - 1):
                empty_count = sorted_slots[i + 1] - sorted_slots[i] - 1
                if empty_count >= 3:
                    long_gaps.append({
                        "group_id": gid,
                        "group": group_label,
                        "day": day,
                        "start_slot": TIME_SLOTS[sorted_slots[i]],
                        "end_slot": TIME_SLOTS[sorted_slots[i + 1]],
                        "empty_slots": empty_count,
                    })

    return long_gaps


def generate_schedule_csp(courses, rooms, teachers, enable_forward_checking=True):
    """
    Constraint Satisfaction Problem (CSP) Backtracking Solver:
    - Schedules 1 weekly session per credit hour for every course.
    - Enforces hard constraints: room capacity, room type, teacher availability,
      no double-booking of rooms/teachers, and student group / batch conflict prevention.
    - Most Constrained Variable (MRV) course ordering: handles constrained courses first.
    - Forward Checking: prunes search branches when any remaining unscheduled task has no possible placement.
    - Smallest suitable room preference: tries smallest fitting room first.
    - Soft preferences: hard courses earlier, spread multi-session courses across different days.
    - Tracks and returns execution performance metrics.
    """
    start_time = time.perf_counter()

    # 1. Pre-build lookup for teacher availability windows
    teacher_availabilities = {}
    for teacher in teachers:
        avails = teacher.availabilities.all()
        if len(avails) > 0:
            teacher_availabilities[teacher.id] = set((a.day, a.time_slot) for a in avails)
        else:
            teacher_availabilities[teacher.id] = None

    courses_map = {c.id: c for c in courses}

    # 2. Pre-compute candidate rooms for each course
    candidate_rooms_map = {c.id: get_candidate_rooms(c, rooms) for c in courses}

    # If any course has zero candidate rooms matching capacity & type, generation is impossible
    for c in courses:
        if not candidate_rooms_map[c.id]:
            elapsed = time.perf_counter() - start_time
            return None

    # 3. Simple Heuristic Course Ordering: Most Constrained Variable (MRV)
    # Sort courses so that the most constrained ones are scheduled first.
    # Deterministic tie-breaker: (-score, -credit_hours, code) guarantees identical output for identical inputs.
    sorted_courses = sorted(
        courses,
        key=lambda c: (
            -compute_course_constraint_score(c, candidate_rooms_map, teacher_availabilities),
            -c.credit_hours,
            c.code,
        )
    )

    # 4. Expand courses into individual weekly session tasks based on credit_hours
    session_tasks = []
    for c in sorted_courses:
        sessions_needed = max(1, c.credit_hours)
        for s_idx in range(sessions_needed):
            session_tasks.append({
                "course_id": c.id,
                "session_num": s_idx + 1,
                "total_sessions": sessions_needed,
            })

    assignments = []

    # Performance metrics tracking
    metrics = {
        "recursion_calls": 0,
        "backtracks": 0,
        "forward_checks_failed": 0,
        "total_required_sessions": len(session_tasks),
        "total_scheduled_sessions": 0,
        "generation_time_seconds": 0.0,
        "algorithm": "CSP Backtracking with Forward Checking & MRV Heuristic",
    }

    def is_valid_assignment(course, room, day, time_slot, teacher_id):
        # 1. Room availability & capacity
        if not room.is_available:
            return False
        if room.capacity < course.enrolled_students:
            return False

        # 2. Room type compatibility
        if course.requires_lab and room.room_type != 'LAB':
            return False
        if not course.requires_lab and room.room_type != 'LECTURE':
            return False

        # 3. Teacher availability window
        if teacher_id:
            allowed = teacher_availabilities.get(teacher_id)
            if allowed is not None and (day, time_slot) not in allowed:
                return False

        # 4. Check conflicts against already assigned sessions
        for existing in assignments:
            if existing['day'] == day and existing['time_slot'] == time_slot:
                # Room collision
                if existing['room_id'] == room.id:
                    return False
                # Teacher collision
                if teacher_id and existing['teacher_id'] == teacher_id:
                    return False
                # Same course collision
                if existing['course_id'] == course.id:
                    return False
                # Student group & batch collision
                if course.group_id:
                    other_course = courses_map.get(existing['course_id'])
                    if other_course and other_course.group_id:
                        if groups_clash(course.group, other_course.group):
                            return False

        return True

    def forward_check(next_task_idx):
        """
        Forward Checking:
        Checks whether every unscheduled session task (from next_task_idx onward)
        still has at least one valid candidate placement remaining.
        If any remaining task has 0 valid placements (domain wipeout), returns False early.
        """
        if not enable_forward_checking or next_task_idx >= len(session_tasks):
            return True

        # Check distinct unscheduled courses
        remaining_course_ids = set(session_tasks[k]['course_id'] for k in range(next_task_idx, len(session_tasks)))

        for rem_cid in remaining_course_ids:
            rem_course = courses_map[rem_cid]
            rem_cand_rooms = candidate_rooms_map.get(rem_cid, [])
            if not rem_cand_rooms:
                return False

            rem_tid = rem_course.teacher.id if rem_course.teacher else None
            rem_allowed = teacher_availabilities.get(rem_tid) if rem_tid else None

            has_valid_slot = False
            for r in rem_cand_rooms:
                for d in DAYS:
                    for ts in TIME_SLOTS:
                        if rem_allowed is not None and (d, ts) not in rem_allowed:
                            continue
                        if is_valid_assignment(rem_course, r, d, ts, rem_tid):
                            has_valid_slot = True
                            break
                    if has_valid_slot:
                        break
                if has_valid_slot:
                    break

            if not has_valid_slot:
                return False

        return True

    def backtrack(task_idx):
        metrics["recursion_calls"] += 1

        if task_idx == len(session_tasks):
            return True

        task = session_tasks[task_idx]
        course = courses_map[task['course_id']]
        teacher_id = course.teacher.id if course.teacher else None

        candidate_rooms = candidate_rooms_map.get(course.id, [])
        if not candidate_rooms:
            metrics["backtracks"] += 1
            return False

        # Soft preference: Spread sessions of the same course across different days
        used_days = {a['day'] for a in assignments if a['course_id'] == course.id}
        ordered_days = sorted(DAYS, key=lambda d: 1 if d in used_days else 0)

        for room in candidate_rooms:
            for day in ordered_days:
                for time_slot in TIME_SLOTS:
                    if is_valid_assignment(course, room, day, time_slot, teacher_id):
                        assignment = {
                            "course_id": course.id,
                            "room_id": room.id,
                            "day": day,
                            "time_slot": time_slot,
                            "teacher_id": teacher_id,
                        }
                        assignments.append(assignment)

                        # Forward checking: Verify future tasks still have possible placements
                        if forward_check(task_idx + 1):
                            if backtrack(task_idx + 1):
                                return True
                        else:
                            metrics["forward_checks_failed"] += 1

                        assignments.pop()
                        metrics["backtracks"] += 1

        return False

    success = backtrack(0)
    elapsed = time.perf_counter() - start_time
    metrics["generation_time_seconds"] = round(elapsed, 5)
    metrics["total_scheduled_sessions"] = len(assignments)

    if not success:
        return None

    # Apply soft-constraint improvements (minimizing student group long gaps)
    improved_assignments, remaining_gaps = improve_schedule_soft_constraints(
        assignments, courses, rooms, teachers, teacher_availabilities
    )

    metrics["total_scheduled_sessions"] = len(improved_assignments)
    return ScheduleResult(improved_assignments, remaining_gaps, metrics=metrics)


def calculate_schedule_score(assignments, courses):
    courses_map = {c.id: c for c in courses}
    long_gaps = compute_long_gaps(assignments, courses)
    gap_penalty = len(long_gaps) * 100

    earliness_penalty = 0
    for item in assignments:
        course = courses_map.get(item['course_id'])
        slot_idx = SLOT_INDEX.get(item['time_slot'], 0)
        if course and course.difficulty == 'HARD':
            earliness_penalty += slot_idx * 5

    return gap_penalty + earliness_penalty


def improve_schedule_soft_constraints(assignments, courses, rooms, teachers, teacher_availabilities):
    """
    A small, bounded improvement step that tries valid moves to reduce student group
    long gaps (>= 3 consecutive empty slots) and place harder subjects earlier.
    Always preserves hard constraints; every candidate move is validated.
    """
    courses_map = {c.id: c for c in courses}
    current_assignments = [dict(a) for a in assignments]
    current_score = calculate_schedule_score(current_assignments, courses)

    # If there are no long gaps and penalty is minimal, nothing to improve
    initial_gaps = compute_long_gaps(current_assignments, courses)
    if not initial_gaps:
        # Check if all HARD courses are already in early slots (slot index <= 1)
        hard_in_late_slot = any(
            courses_map.get(a['course_id']) and courses_map[a['course_id']].difficulty == 'HARD'
            and SLOT_INDEX.get(a['time_slot'], 0) > 1
            for a in current_assignments
        )
        if not hard_in_late_slot:
            return current_assignments, []

    def is_move_valid(cand_idx, room, day, time_slot):
        item = current_assignments[cand_idx]
        course = courses_map[item['course_id']]
        teacher_id = item['teacher_id']

        if not room.is_available or room.capacity < course.enrolled_students:
            return False
        if course.requires_lab and room.room_type != 'LAB':
            return False
        if not course.requires_lab and room.room_type != 'LECTURE':
            return False

        if teacher_id:
            allowed = teacher_availabilities.get(teacher_id)
            if allowed is not None and (day, time_slot) not in allowed:
                return False

        for idx, other in enumerate(current_assignments):
            if idx == cand_idx:
                continue
            if other['day'] == day and other['time_slot'] == time_slot:
                if other['room_id'] == room.id:
                    return False
                if teacher_id and other['teacher_id'] == teacher_id:
                    return False
                if other['course_id'] == course.id:
                    return False
                if course.group_id:
                    other_c = courses_map.get(other['course_id'])
                    if other_c and other_c.group_id:
                        if groups_clash(course.group, other_c.group):
                            return False
        return True

    # Bounded iterations: at most 3 focused passes
    for _ in range(3):
        improved = False
        for idx in range(len(current_assignments)):
            orig = dict(current_assignments[idx])
            course = courses_map[orig['course_id']]
            candidate_rooms = get_candidate_rooms(course, rooms)

            for room in candidate_rooms:
                for day in DAYS:
                    for slot in TIME_SLOTS:
                        if day == orig['day'] and slot == orig['time_slot'] and room.id == orig['room_id']:
                            continue
                        if is_move_valid(idx, room, day, slot):
                            current_assignments[idx] = {
                                "course_id": course.id,
                                "room_id": room.id,
                                "day": day,
                                "time_slot": slot,
                                "teacher_id": orig['teacher_id'],
                            }
                            new_score = calculate_schedule_score(current_assignments, courses)
                            if new_score < current_score:
                                current_score = new_score
                                improved = True
                                break
                            else:
                                current_assignments[idx] = orig
                    if improved:
                        break
                if improved:
                    break
        if not improved:
            break

    remaining_gaps = compute_long_gaps(current_assignments, courses)
    return current_assignments, remaining_gaps


def validate_schedule(schedule_assignments, courses, rooms, teachers):
    """
    Independently re-verifies that a schedule strictly satisfies every rule.
    Supports ScheduleResult, list of session dicts, or dictionary of assignments.
    Checks:
    1. Room double-booking (ROOM_CONFLICT)
    2. Teacher double-booking & availability (TEACHER_CONFLICT, TEACHER_UNAVAILABLE)
    3. Student group & batch overlap (GROUP_CONFLICT)
    4. Same course at same time (COURSE_CONFLICT)
    5. Room seating capacity (ROOM_CAPACITY_CONFLICT)
    6. Room type compatibility (ROOM_TYPE_CONFLICT)
    7. Room availability status (ROOM_UNAVAILABLE)
    8. Valid supported days & time slots (INVALID_DAY, INVALID_TIME_SLOT)
    """
    conflicts = []

    courses_map = {c.id: c for c in courses}
    rooms_map = {r.id: r for r in rooms}
    teachers_map = {t.id: t for t in teachers}

    # Normalize input
    if hasattr(schedule_assignments, 'sessions'):
        sessions_raw = schedule_assignments.sessions
    elif isinstance(schedule_assignments, list):
        sessions_raw = schedule_assignments
    elif isinstance(schedule_assignments, dict):
        sessions_raw = []
        for k, v in schedule_assignments.items():
            cid = k[0] if isinstance(k, tuple) else k
            if isinstance(v, (list, tuple)):
                rid = v[0]
                day = v[1]
                slot = v[2]
                tid = v[3] if len(v) > 3 else None
                sessions_raw.append({
                    'course_id': cid,
                    'room_id': rid,
                    'day': day,
                    'time_slot': slot,
                    'teacher_id': tid,
                })
            elif isinstance(v, dict):
                sessions_raw.append(v)
    else:
        sessions_raw = []

    sessions_to_check = []
    for item in sessions_raw:
        if isinstance(item, dict):
            sessions_to_check.append(item)
        elif hasattr(item, 'course_id'):
            sessions_to_check.append({
                'course_id': item.course_id,
                'room_id': item.room_id,
                'day': item.day,
                'time_slot': item.time_slot,
                'teacher_id': getattr(item, 'teacher_id', None),
            })


    time_room_map = {}
    time_teacher_map = {}
    time_group_map = {}
    time_course_map = {}

    for details in sessions_to_check:
        course_id = details['course_id']
        room_id = details['room_id']
        day = details['day']
        time_slot = details['time_slot']
        teacher_id = details.get('teacher_id')

        course = courses_map.get(course_id)
        room = rooms_map.get(room_id)
        teacher = teachers_map.get(teacher_id) if teacher_id else None

        if not course or not room:
            conflicts.append({"type": "INVALID_DATA", "detail": "Missing course or room."})
            continue

        # Day & time slot validity
        if day not in DAYS:
            conflicts.append({
                "type": "INVALID_DAY",
                "day": day,
                "course": course.code,
            })
        if time_slot not in TIME_SLOTS:
            conflicts.append({
                "type": "INVALID_TIME_SLOT",
                "time_slot": time_slot,
                "course": course.code,
            })

        time_key = f"{day}_{time_slot}"

        # 1. Room double-booking
        room_key = f"{time_key}_{room_id}"
        if room_key in time_room_map:
            conflicts.append({
                "type": "ROOM_CONFLICT",
                "room": room.room_number,
                "time_slot": f"{day} {time_slot}",
            })
        time_room_map[room_key] = course.code

        # 2. Teacher double-booking & availability
        if teacher:
            teacher_key = f"{time_key}_{teacher_id}"
            if teacher_key in time_teacher_map:
                conflicts.append({
                    "type": "TEACHER_CONFLICT",
                    "teacher": teacher.name,
                    "time_slot": f"{day} {time_slot}",
                })
            time_teacher_map[teacher_key] = course.code

            avails = teacher.availabilities.all()
            if len(avails) > 0:
                is_available = any(a.day == day and a.time_slot == time_slot for a in avails)
                if not is_available:
                    conflicts.append({
                        "type": "TEACHER_UNAVAILABLE",
                        "teacher": teacher.name,
                        "time_slot": f"{day} {time_slot}",
                    })

        # 3. Student group & batch overlap
        if course.group_id:
            for (assigned_day, assigned_slot, other_gid), other_c_code in list(time_group_map.items()):
                if assigned_day == day and assigned_slot == time_slot:
                    other_group = next((c.group for c in courses if c.group_id == other_gid), None)
                    if groups_clash(course.group, other_group):
                        conflicts.append({
                            "type": "GROUP_CONFLICT",
                            "group": course.group.code if course.group else str(course.group_id),
                            "time_slot": f"{day} {time_slot}",
                        })
            time_group_map[(day, time_slot, course.group_id)] = course.code

        # 4. Same course at same time
        course_time_key = f"{time_key}_{course.id}"
        if course_time_key in time_course_map:
            conflicts.append({
                "type": "COURSE_CONFLICT",
                "course": course.code,
                "time_slot": f"{day} {time_slot}",
            })
        time_course_map[course_time_key] = course.code

        # 5. Room capacity
        if room.capacity < course.enrolled_students:
            conflicts.append({
                "type": "ROOM_CAPACITY_CONFLICT",
                "room": room.room_number,
                "capacity": room.capacity,
                "enrolled": course.enrolled_students,
            })

        # 6. Room type
        if course.requires_lab and room.room_type != 'LAB':
            conflicts.append({
                "type": "ROOM_TYPE_CONFLICT",
                "room": room.room_number,
                "expected": "LAB",
            })
        if not course.requires_lab and room.room_type != 'LECTURE':
            conflicts.append({
                "type": "ROOM_TYPE_CONFLICT",
                "room": room.room_number,
                "expected": "LECTURE",
            })

        # 7. Room availability
        if not room.is_available:
            conflicts.append({
                "type": "ROOM_UNAVAILABLE",
                "room": room.room_number,
            })

    return {
        "valid": len(conflicts) == 0,
        "conflicts": conflicts,
    }


def generate_and_save_schedule():
    """
    Fetches scheduling inputs, validates completeness, runs the CSP algorithm,
    validates the output independently, and safely replaces the timetable inside
    a database transaction.

    If generation or validation fails, existing timetable data is strictly preserved.
    """
    from django.db import transaction
    from .models import Room, Teacher, Course, Schedule

    courses = list(Course.objects.select_related('teacher', 'group').all())
    rooms = list(Room.objects.filter(is_available=True))
    teachers = list(Teacher.objects.prefetch_related('availabilities').all())

    if not courses:
        return {"success": False, "error": "Missing courses data. Please add courses first."}
    if not rooms:
        return {"success": False, "error": "Missing rooms data. Please add active/available rooms first."}

    missing_teachers = [c.code for c in courses if not c.teacher]
    if missing_teachers:
        return {
            "success": False,
            "error": (
                f"Incomplete input: The following courses do not have an assigned teacher: "
                f"{', '.join(missing_teachers)}. Assign faculty to every course before generating timetable."
            )
        }

    invalid_credits = [c.code for c in courses if c.credit_hours <= 0]
    if invalid_credits:
        return {"success": False, "error": f"Courses with invalid credit hours (must be at least 1): {', '.join(invalid_credits)}"}

    invalid_enrollments = [c.code for c in courses if c.enrolled_students <= 0]
    if invalid_enrollments:
        return {"success": False, "error": f"Courses with invalid student enrollment (must be at least 1): {', '.join(invalid_enrollments)}"}

    lab_rooms = [r for r in rooms if r.room_type == 'LAB']
    lecture_rooms = [r for r in rooms if r.room_type == 'LECTURE']

    for c in courses:
        target_rooms = lab_rooms if c.requires_lab else lecture_rooms
        room_type_str = "Laboratory" if c.requires_lab else "Lecture Hall"
        if not target_rooms:
            return {"success": False, "error": f"Incomplete infrastructure: Course {c.code} requires a {room_type_str}, but no active {room_type_str} rooms exist."}
        max_cap = max(r.capacity for r in target_rooms)
        if c.enrolled_students > max_cap:
            return {
                "success": False,
                "error": (
                    f"Room capacity exceeded: Course {c.code} has {c.enrolled_students} enrolled students, "
                    f"but the largest available {room_type_str} has only {max_cap} seats."
                )
            }

    assignments = generate_schedule_csp(courses, rooms, teachers)
    if assignments is None:
        return {
            "success": False,
            "error": "No valid schedule could be generated with current constraints. Previous timetable was preserved."
        }

    validation_result = validate_schedule(assignments, courses, rooms, teachers)
    if not validation_result['valid']:
        return {
            "success": False,
            "error": "Generated schedule failed constraint validation. Previous timetable was preserved.",
            "conflicts": validation_result['conflicts']
        }

    sessions_list = assignments.sessions if hasattr(assignments, 'sessions') else assignments
    if isinstance(sessions_list, dict):
        sessions_list = [
            {'course_id': cid, 'room_id': val[0], 'day': val[1], 'time_slot': val[2], 'teacher_id': val[3] if len(val) > 3 else None}
            for cid, val in sessions_list.items()
        ]

    try:
        with transaction.atomic():
            Schedule.objects.all().delete()
            schedule_records = [
                Schedule(
                    course_id=item['course_id'],
                    room_id=item['room_id'],
                    teacher_id=item['teacher_id'],
                    day=item['day'],
                    time_slot=item['time_slot'],
                    status='GENERATED',
                )
                for item in sessions_list
            ]
            Schedule.objects.bulk_create(schedule_records)
    except Exception as exc:
        return {"success": False, "error": f"Database error saving schedule: {str(exc)}."}

    total_required = sum(c.credit_hours for c in courses)
    total_scheduled = len(schedule_records)
    remaining_gaps = getattr(assignments, 'remaining_gaps', [])
    metrics = getattr(assignments, 'metrics', {})
    metrics["valid"] = True
    metrics["conflicts_detected"] = 0
    metrics["total_scheduled_sessions"] = total_scheduled
    metrics["total_required_sessions"] = total_required

    return {
        "success": True,
        "message": "Schedule generated successfully.",
        "conflicts_detected": 0,
        "valid": True,
        "total_required_sessions": total_required,
        "total_scheduled_sessions": total_scheduled,
        "remaining_sessions": max(0, total_required - total_scheduled),
        "remaining_gaps": remaining_gaps,
        "remaining_gaps_count": len(remaining_gaps),
        "metrics": metrics,
        "assignments": assignments,
        "courses": courses,
        "rooms": rooms,
        "teachers": teachers,
    }


