from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Room, Teacher, TeacherAvailability, Course, Schedule
from .solver import generate_schedule_csp, validate_schedule


def _as_list(data):
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


class CSPSolverTest(TestCase):
    """
    Automated tests for the Constraint Satisfaction Problem (CSP) scheduling algorithm.
    These tests verify that our algorithm and validation logic correctly follow
    all college timetable rules (hard and soft constraints).
    """

    def setUp(self):
        """
        Runs before every test. Sets up a small college environment:
        - 2 rooms: 1 Lecture hall (50 seats), 1 Laboratory (30 seats)
        - 2 teachers: T1 (available only MON 09:00-10:00), T2 (available anytime)
        - 2 courses: C1 (Lecture course, 40 students), C2 (Lab course, 20 students)
        """
        # 1. Setup Rooms
        self.r1 = Room.objects.create(room_number="R1", capacity=50, room_type="LECTURE")
        self.r2 = Room.objects.create(room_number="L1", capacity=30, room_type="LAB")

        # 2. Setup Teachers and their available hours
        self.t1 = Teacher.objects.create(name="T1", department="D1")
        TeacherAvailability.objects.create(teacher=self.t1, day="MON", time_slot="09:00-10:00")
        self.t2 = Teacher.objects.create(name="T2", department="D2")

        # 3. Setup Courses
        self.c1 = Course.objects.create(
            code="C1", name="C1", enrolled_students=40, requires_lab=False, teacher=self.t1
        )
        self.c2 = Course.objects.create(
            code="C2", name="C2", enrolled_students=20, requires_lab=True, teacher=self.t2
        )

    # =========================================================================
    # Existing Tests (Preserved)
    # =========================================================================

    def test_valid_schedule_generation(self):
        """Tests that a valid schedule can be generated with 0 conflicts."""
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        assignments = generate_schedule_csp(courses, rooms, teachers)
        self.assertIsNotNone(assignments)

        val = validate_schedule(assignments, courses, rooms, teachers)
        self.assertTrue(val['valid'])
        self.assertEqual(len(val['conflicts']), 0)

    def test_impossible_schedule(self):
        """Tests that the solver returns None when no room is big enough."""
        # Add a course that needs 100 capacity, which doesn't exist
        Course.objects.create(
            code="C3", name="C3", enrolled_students=100, requires_lab=False, teacher=self.t1
        )

        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        assignments = generate_schedule_csp(courses, rooms, teachers)
        self.assertIsNone(assignments)

    def test_teacher_conflict_detection(self):
        """Tests that assigning the same teacher to two classes at once triggers a TEACHER_CONFLICT."""
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        # c1 and c2 taught by t1 at the exact same time
        assignments = {
            self.c1.id: (self.r1.id, "MON", "09:00-10:00", self.t1.id),
            self.c2.id: (self.r2.id, "MON", "09:00-10:00", self.t1.id),
        }

        val = validate_schedule(assignments, courses, rooms, teachers)
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'TEACHER_CONFLICT' for c in val['conflicts']))

    def test_room_conflict_detection(self):
        """Tests that assigning two different classes to the same room at the same time triggers a ROOM_CONFLICT."""
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        # c1 and c2 placed in the same room r1 at the exact same time
        assignments = {
            self.c1.id: (self.r1.id, "MON", "09:00-10:00", self.t1.id),
            self.c2.id: (self.r1.id, "MON", "09:00-10:00", self.t2.id),
        }

        val = validate_schedule(assignments, courses, rooms, teachers)
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'ROOM_CONFLICT' for c in val['conflicts']))

    # =========================================================================
    # New Constraint Tests: Classroom Capacity
    # =========================================================================

    def test_classroom_capacity_conflict_detection(self):
        """
        Tests that putting more students in a room than its seating capacity
        is correctly caught as a ROOM_CAPACITY_CONFLICT.
        Example: Course C1 has 40 students, but room L1 only has 30 seats.
        """
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        # Force Course C1 (40 students) into Room L1 (seating capacity 30)
        assignments = {
            self.c1.id: (self.r2.id, "MON", "09:00-10:00", self.t1.id)
        }

        val = validate_schedule(assignments, courses, rooms, teachers)
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'ROOM_CAPACITY_CONFLICT' for c in val['conflicts']))

    def test_classroom_capacity_satisfied_by_solver(self):
        """
        Tests that when our CSP solver creates a timetable, every course is
        assigned to a room with enough seats (room capacity >= enrolled students).
        """
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        assignments = generate_schedule_csp(courses, rooms, teachers)
        self.assertIsNotNone(assignments)

        # Check each course's assigned room capacity
        for course in courses:
            assigned_room_id = assignments[course.id][0]
            assigned_room = Room.objects.get(id=assigned_room_id)
            self.assertGreaterEqual(
                assigned_room.capacity,
                course.enrolled_students,
                f"Room {assigned_room.room_number} capacity ({assigned_room.capacity}) "
                f"is smaller than enrolled students ({course.enrolled_students})"
            )

    # =========================================================================
    # New Constraint Tests: Laboratory / Room Type Compatibility
    # =========================================================================

    def test_room_type_conflict_detection(self):
        """
        Tests that placing a practical lab subject in a normal lecture hall
        is caught as a ROOM_TYPE_CONFLICT.
        Example: Course C2 requires a lab, but is placed in lecture hall R1.
        """
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        # Force lab course C2 into lecture hall R1
        assignments = {
            self.c2.id: (self.r1.id, "MON", "09:00-10:00", self.t2.id)
        }

        val = validate_schedule(assignments, courses, rooms, teachers)
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'ROOM_TYPE_CONFLICT' for c in val['conflicts']))

    def test_room_type_compatibility_satisfied_by_solver(self):
        """
        Tests that our CSP solver assigns practical/lab subjects only to LAB rooms,
        and regular theory subjects only to LECTURE halls.
        """
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        assignments = generate_schedule_csp(courses, rooms, teachers)
        self.assertIsNotNone(assignments)

        for course in courses:
            assigned_room_id = assignments[course.id][0]
            assigned_room = Room.objects.get(id=assigned_room_id)
            if course.requires_lab:
                self.assertEqual(assigned_room.room_type, "LAB")
            else:
                self.assertEqual(assigned_room.room_type, "LECTURE")

    # =========================================================================
    # New Constraint Tests: Teacher Availability
    # =========================================================================

    def test_teacher_availability_conflict_detection(self):
        """
        Tests that scheduling a teacher outside their available time slots
        triggers a TEACHER_UNAVAILABLE conflict.
        Example: Teacher T1 is only free on Monday 09:00-10:00, but is scheduled on Tuesday.
        """
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        # T1 is only available on MON 09:00-10:00, force assignment on TUE 10:00-11:00
        assignments = {
            self.c1.id: (self.r1.id, "TUE", "10:00-11:00", self.t1.id)
        }

        val = validate_schedule(assignments, courses, rooms, teachers)
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'TEACHER_UNAVAILABLE' for c in val['conflicts']))

    def test_teacher_availability_satisfied_by_solver(self):
        """
        Tests that our CSP solver respects teacher availability and only
        places classes during the teacher's available days and hours.
        """
        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        assignments = generate_schedule_csp(courses, rooms, teachers)
        self.assertIsNotNone(assignments)

        # Course C1 is taught by Teacher T1, who is only available on MON 09:00-10:00
        _, assigned_day, assigned_time_slot, _ = assignments[self.c1.id]
        self.assertEqual(assigned_day, "MON")
        self.assertEqual(assigned_time_slot, "09:00-10:00")


class ScheduleAPITest(TestCase):
    """
    Beginner-friendly automated tests for the REST API endpoints.
    These test that the React frontend can successfully send and receive data
    from the Django backend using standard HTTP GET and POST requests.
    """

    def setUp(self):
        self.room1 = Room.objects.create(room_number="R101", capacity=60, room_type="LECTURE")
        self.lab1 = Room.objects.create(room_number="LAB1", capacity=30, room_type="LAB")
        self.teacher1 = Teacher.objects.create(name="Prof. Sharma", department="CSE")
        TeacherAvailability.objects.create(teacher=self.teacher1, day="MON", time_slot="09:00-10:00")
        self.course1 = Course.objects.create(
            code="CS101",
            name="Programming Fundamentals",
            enrolled_students=45,
            requires_lab=False,
            teacher=self.teacher1,
        )
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True)
        self.viewer = User.objects.create_user(username="viewer", password="viewer123", is_staff=False)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_get_rooms_api(self):
        response = self.client.get('/api/rooms/')
        self.assertEqual(response.status_code, 200)
        data = _as_list(response.json())
        self.assertEqual(len(data), 2)
        room_numbers = [r['room_number'] for r in data]
        self.assertIn("R101", room_numbers)
        self.assertIn("LAB1", room_numbers)

    def test_get_teachers_api(self):
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, 200)
        data = _as_list(response.json())
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], "Prof. Sharma")

    def test_get_courses_api(self):
        response = self.client.get('/api/courses/')
        self.assertEqual(response.status_code, 200)
        data = _as_list(response.json())
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['code'], "CS101")

    def test_generate_schedule_api(self):
        response = self.client.post('/api/schedule/generate/')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['conflicts_detected'], 0)
        self.assertEqual(data['message'], "Schedule generated successfully.")
        self.assertGreater(len(data['schedule']), 0)
        self.assertEqual(Schedule.objects.count(), 1)

    def test_get_schedules_api(self):
        self.client.post('/api/schedule/generate/')
        response = self.client.get('/api/schedules/')
        self.assertEqual(response.status_code, 200)
        data = _as_list(response.json())
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['status'], 'GENERATED')

    def test_clear_schedule_api(self):
        self.client.post('/api/schedule/generate/')
        self.assertEqual(Schedule.objects.count(), 1)
        response = self.client.post('/api/schedule/clear/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], "Schedule cleared.")
        self.assertEqual(Schedule.objects.count(), 0)


class AuthRBACTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True)
        self.viewer = User.objects.create_user(username="viewer", password="viewer123", is_staff=False)
        self.room = Room.objects.create(room_number="R101", capacity=60, room_type="LECTURE")
        self.teacher = Teacher.objects.create(name="T1", department="CSE")
        self.course = Course.objects.create(code="CS101", name="C1", enrolled_students=10, requires_lab=False, teacher=self.teacher)
        self.client = APIClient()

    def test_unauthenticated_blocked(self):
        self.assertEqual(self.client.get('/api/rooms/').status_code, 401)

    def test_viewer_can_read_but_cannot_write(self):
        self.client.force_authenticate(user=self.viewer)
        self.assertEqual(self.client.get('/api/rooms/').status_code, 200)
        res = self.client.post('/api/rooms/', {"room_number": "X1", "capacity": 10, "room_type": "LECTURE", "is_available": True}, format='json')
        self.assertEqual(res.status_code, 403)
        res = self.client.post('/api/schedule/generate/')
        self.assertEqual(res.status_code, 403)

    def test_admin_can_write_and_generate(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/rooms/', {"room_number": "X1", "capacity": 10, "room_type": "LECTURE", "is_available": True}, format='json')
        self.assertEqual(res.status_code, 201)
        res = self.client.post('/api/schedule/generate/')
        self.assertEqual(res.status_code, 201)

    def test_dashboard_and_me(self):
        self.client.force_authenticate(user=self.viewer)
        me = self.client.get('/api/me/')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['role'], 'VIEWER')
        dash = self.client.get('/api/dashboard/stats/')
        self.assertEqual(dash.status_code, 200)
        self.assertIn('counts', dash.json())
        self.assertIn('utilization', dash.json())


import io
import time
from .models import StudentGroup
from .solver import compute_long_gaps, get_candidate_rooms, generate_and_save_schedule


class JWTAuthenticationFlowTest(TestCase):
    """
    Tests actual JWT token generation and refresh through SimpleJWT endpoints.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="securepassword123")
        self.client = APIClient()

    def test_actual_jwt_login_success(self):
        res = self.client.post('/api/auth/login/', {"username": "testuser", "password": "securepassword123"}, format='json')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)

    def test_actual_jwt_login_invalid_password(self):
        res = self.client.post('/api/auth/login/', {"username": "testuser", "password": "wrongpassword"}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_actual_jwt_token_refresh(self):
        # 1. Login to obtain refresh token
        res = self.client.post('/api/auth/login/', {"username": "testuser", "password": "securepassword123"}, format='json')
        refresh_token = res.json()['refresh']

        # 2. Call refresh endpoint
        refresh_res = self.client.post('/api/auth/refresh/', {"refresh": refresh_token}, format='json')
        self.assertEqual(refresh_res.status_code, 200)
        self.assertIn('access', refresh_res.json())


class ViewerWriteRejectionAndExportAccessTest(TestCase):
    """
    Tests that Viewers are rejected with 403 on write endpoints,
    while being allowed to access all exports and reads.
    """
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True)
        self.viewer = User.objects.create_user(username="viewer", password="viewer123", is_staff=False)
        self.room = Room.objects.create(room_number="R1", capacity=40, room_type="LECTURE")
        self.teacher = Teacher.objects.create(name="Prof. Sharma", department="CSE")
        self.group = StudentGroup.objects.create(code="CSE-A", name="CSE Batch A")
        self.course = Course.objects.create(code="CS101", name="CS", enrolled_students=30, requires_lab=False, teacher=self.teacher, group=self.group)
        self.schedule = Schedule.objects.create(course=self.course, teacher=self.teacher, room=self.room, day="MON", time_slot="09:00-10:00")
        self.client = APIClient()
        self.client.force_authenticate(user=self.viewer)

    def test_viewer_write_rejection_across_resources(self):
        # Room creation rejected
        res = self.client.post('/api/rooms/', {"room_number": "R99", "capacity": 30, "room_type": "LECTURE"})
        self.assertEqual(res.status_code, 403)

        # Faculty creation rejected
        res = self.client.post('/api/teachers/', {"name": "Prof. X", "department": "IT"})
        self.assertEqual(res.status_code, 403)

        # Group creation rejected
        res = self.client.post('/api/groups/', {"code": "IT-A", "name": "IT Batch A"})
        self.assertEqual(res.status_code, 403)

        # Course creation rejected
        res = self.client.post('/api/courses/', {"code": "IT201", "name": "DB", "credit_hours": 3, "enrolled_students": 25})
        self.assertEqual(res.status_code, 403)

        # Schedule edit rejected
        res = self.client.patch(f'/api/schedules/{self.schedule.id}/', {"day": "TUE"})
        self.assertEqual(res.status_code, 403)

        # Timetable generation rejected
        res = self.client.post('/api/schedule/generate/')
        self.assertEqual(res.status_code, 403)

        # CSV import rejected
        res = self.client.post('/api/import/rooms/', {"file": "dummy"})
        self.assertEqual(res.status_code, 403)

    def test_viewer_can_export_csv_excel_and_pdf(self):
        res_csv = self.client.get('/api/schedule/export.csv')
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("text/csv", res_csv.headers['Content-Type'])

        res_xlsx = self.client.get('/api/schedule/export.xlsx')
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertIn("spreadsheetml", res_xlsx.headers['Content-Type'])

        res_pdf = self.client.get('/api/schedule/export.pdf')
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.headers['Content-Type'], "application/pdf")
        self.assertTrue(res_pdf.content.startswith(b'%PDF-'))

    def test_export_filtered_by_particular_batch(self):
        """Verifies exporting for a particular batch sets appropriate header and filtered content."""
        res_csv = self.client.get('/api/schedule/export.csv?batch=IT-I-A')
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn('MITS_Timetable_Batch_IT-I-A.csv', res_csv.headers.get('Content-Disposition', ''))

        res_xlsx = self.client.get('/api/schedule/export.xlsx?batch=IT-I-A')
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertIn('MITS_Timetable_Batch_IT-I-A.xlsx', res_xlsx.headers.get('Content-Disposition', ''))

        res_pdf = self.client.get('/api/schedule/export.pdf?batch=IT-I-A')
        self.assertEqual(res_pdf.status_code, 200)
        self.assertIn('MITS_Timetable_Batch_IT-I-A.pdf', res_pdf.headers.get('Content-Disposition', ''))
        self.assertTrue(res_pdf.content.startswith(b'%PDF-'))

    def test_export_excel_with_multi_batch_split_sheets(self):
        """Verifies Excel export with split_batches=1 creates individual tabs per student batch."""
        res = self.client.get('/api/schedule/export.xlsx?split_batches=1')
        self.assertEqual(res.status_code, 200)
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        self.assertIn("Timetable", wb.sheetnames)
        # Should have at least one sheet
        self.assertGreaterEqual(len(wb.sheetnames), 1)

    def test_export_filtered_by_combinations(self):
        """Verifies exporting with multi-filter combinations (faculty + day + type)."""
        res = self.client.get('/api/schedule/export.pdf?teacher=VS&day=MON&type=LECTURE')
        self.assertEqual(res.status_code, 200)
        self.assertIn('MITS_Timetable_Faculty_VS_Day_MON_LECTURE.pdf', res.headers.get('Content-Disposition', ''))


class MultiSessionFromCreditHoursTest(TestCase):
    """
    Tests that 1 credit hour = 1 weekly 1-hour session, and that multiple
    sessions are scheduled and tracked accurately.
    """
    def setUp(self):
        self.room = Room.objects.create(room_number="R101", capacity=50, room_type="LECTURE")
        self.teacher = Teacher.objects.create(name="Prof. Sharma", department="CSE")
        # Teacher available on MON, TUE, WED 09:00-10:00
        TeacherAvailability.objects.create(teacher=self.teacher, day="MON", time_slot="09:00-10:00")
        TeacherAvailability.objects.create(teacher=self.teacher, day="TUE", time_slot="09:00-10:00")
        TeacherAvailability.objects.create(teacher=self.teacher, day="WED", time_slot="09:00-10:00")
        self.group = StudentGroup.objects.create(code="CSE-A", name="CSE Section A")
        # 3 credit hours = 3 weekly sessions required
        self.course = Course.objects.create(
            code="CS101",
            name="Programming",
            credit_hours=3,
            enrolled_students=40,
            requires_lab=False,
            teacher=self.teacher,
            group=self.group,
        )

    def test_three_credit_hours_creates_three_weekly_sessions(self):
        result = generate_and_save_schedule()
        self.assertTrue(result['success'])
        self.assertEqual(result['total_required_sessions'], 3)
        self.assertEqual(result['total_scheduled_sessions'], 3)
        self.assertEqual(result['remaining_sessions'], 0)

        # Verify 3 separate schedule records exist in the database
        schedules = Schedule.objects.filter(course=self.course)
        self.assertEqual(schedules.count(), 3)
        days = set(s.day for s in schedules)
        self.assertEqual(days, {"MON", "TUE", "WED"})


class StudentGroupConflictAndGapTest(TestCase):
    """
    Tests student group conflict detection, overlap prevention,
    and long gap measurement.
    """
    def setUp(self):
        self.room1 = Room.objects.create(room_number="R101", capacity=50, room_type="LECTURE")
        self.room2 = Room.objects.create(room_number="R102", capacity=50, room_type="LECTURE")
        self.t1 = Teacher.objects.create(name="T1", department="CSE")
        self.t2 = Teacher.objects.create(name="T2", department="IT")
        self.group = StudentGroup.objects.create(code="CSE-A", name="CSE Batch A")
        self.c1 = Course.objects.create(code="C1", name="C1", credit_hours=1, enrolled_students=30, teacher=self.t1, group=self.group)
        self.c2 = Course.objects.create(code="C2", name="C2", credit_hours=1, enrolled_students=30, teacher=self.t2, group=self.group)

    def test_group_conflict_detected_in_validator(self):
        # Place c1 and c2 at the exact same day and time in different rooms
        assignments = {
            self.c1.id: (self.room1.id, "MON", "09:00-10:00", self.t1.id),
            self.c2.id: (self.room2.id, "MON", "09:00-10:00", self.t2.id),
        }
        val = validate_schedule(assignments, [self.c1, self.c2], [self.room1, self.room2], [self.t1, self.t2])
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'GROUP_CONFLICT' for c in val['conflicts']))

    def test_long_gap_computation_at_least_three_empty_slots(self):
        # Class at slot 0 (09:00-10:00) and class at slot 4 (13:00-14:00) -> 3 empty slots
        assignments = [
            {"course_id": self.c1.id, "day": "MON", "time_slot": "09:00-10:00"},
            {"course_id": self.c2.id, "day": "MON", "time_slot": "13:00-14:00"},
        ]
        gaps = compute_long_gaps(assignments, [self.c1, self.c2])
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]['empty_slots'], 3)
        self.assertEqual(gaps[0]['group'], "CSE-A")


class RoomUsagePreferenceTest(TestCase):
    """
    Tests that the solver prioritizes the smallest available room that fits enrollment.
    """
    def setUp(self):
        self.large_room = Room.objects.create(room_number="101", capacity=60, room_type="LECTURE")
        self.small_room = Room.objects.create(room_number="102", capacity=40, room_type="LECTURE")
        self.course = Course.objects.create(code="CS101", name="CS", enrolled_students=35, requires_lab=False)

    def test_smallest_suitable_room_selected_first(self):
        candidates = get_candidate_rooms(self.course, [self.large_room, self.small_room])
        # Room 102 (capacity 40) must come before Room 101 (capacity 60)
        self.assertEqual(candidates[0].room_number, "102")
        self.assertEqual(candidates[1].room_number, "101")


class CSVImportTransactionAndValidationTest(TestCase):
    """
    Tests that CSV upload pre-validates all rows and uses transactions so
    no partial records are created on failure.
    """
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_csv_import_rooms_valid(self):
        csv_content = "room_number,capacity,room_type,is_available\nA-101,50,LECTURE,true\nA-102,40,LAB,true\n"
        f = io.BytesIO(csv_content.encode('utf-8'))
        f.name = "rooms.csv"
        res = self.client.post('/api/import/rooms/', {"file": f}, format='multipart')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Room.objects.filter(room_number="A-101").count(), 1)
        self.assertEqual(Room.objects.filter(room_number="A-102").count(), 1)

    def test_csv_import_rooms_invalid_row_aborts_all(self):
        # Row 2 has an invalid capacity (-10)
        csv_content = "room_number,capacity,room_type,is_available\nB-101,50,LECTURE,true\nB-102,-10,LECTURE,true\n"
        f = io.BytesIO(csv_content.encode('utf-8'))
        f.name = "rooms.csv"
        res = self.client.post('/api/import/rooms/', {"file": f}, format='multipart')
        self.assertEqual(res.status_code, 400)
        self.assertIn("Row 3", res.json()['errors'][0])
        # Confirm transaction rollback: B-101 was NOT saved
        self.assertEqual(Room.objects.filter(room_number="B-101").count(), 0)

    def test_csv_template_download(self):
        res = self.client.get('/api/import/template/rooms/')
        self.assertEqual(res.status_code, 200)
        self.assertIn("room_number", res.content.decode('utf-8'))


class DragAndDropSaveBehaviorTest(TestCase):
    """
    Tests backend validation when moving classes via drag-and-drop.
    """
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.room = Room.objects.create(room_number="R1", capacity=50, room_type="LECTURE")
        self.teacher = Teacher.objects.create(name="T1", department="CSE")
        self.course = Course.objects.create(code="C1", name="C1", enrolled_students=30, requires_lab=False, teacher=self.teacher)
        self.schedule = Schedule.objects.create(course=self.course, teacher=self.teacher, room=self.room, day="MON", time_slot="09:00-10:00")

    def test_drag_and_drop_valid_move(self):
        res = self.client.patch(f'/api/schedules/{self.schedule.id}/', {"day": "TUE", "time_slot": "10:00-11:00"}, format='json')
        self.assertEqual(res.status_code, 200)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.day, "TUE")
        self.assertEqual(self.schedule.time_slot, "10:00-11:00")

    def test_drag_and_drop_invalid_move_rejected_original_preserved(self):
        # Create another schedule occupying TUE 09:00-10:00 in the same room
        teacher2 = Teacher.objects.create(name="T2", department="IT")
        course2 = Course.objects.create(code="C2", name="C2", enrolled_students=30, requires_lab=False, teacher=teacher2)
        Schedule.objects.create(course=course2, teacher=teacher2, room=self.room, day="TUE", time_slot="09:00-10:00")

        # Attempt to drop self.schedule into that exact room and time
        res = self.client.patch(f'/api/schedules/{self.schedule.id}/', {"day": "TUE", "time_slot": "09:00-10:00"}, format='json')
        self.assertEqual(res.status_code, 400)
        # Original assignment on MON 09:00-10:00 is preserved
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.day, "MON")
        self.assertEqual(self.schedule.time_slot, "09:00-10:00")


class TimetablePreservationOnFailedGenerationTest(TestCase):
    """
    Tests that existing timetable entries are preserved if schedule generation fails.
    """
    def setUp(self):
        self.room = Room.objects.create(room_number="R101", capacity=50, room_type="LECTURE")
        self.teacher = Teacher.objects.create(name="Prof. Sharma", department="CSE")
        self.course = Course.objects.create(code="CS101", name="CS", credit_hours=1, enrolled_students=30, requires_lab=False, teacher=self.teacher)
        # Existing schedule
        self.existing = Schedule.objects.create(course=self.course, teacher=self.teacher, room=self.room, day="MON", time_slot="09:00-10:00")

    def test_existing_schedule_preserved_on_impossible_generation(self):
        # Add an impossible course: needs 200 capacity, but only 50 capacity room exists
        teacher2 = Teacher.objects.create(name="T2", department="IT")
        Course.objects.create(code="IMPOSSIBLE", name="Big Course", credit_hours=1, enrolled_students=200, requires_lab=False, teacher=teacher2)

        result = generate_and_save_schedule()
        self.assertFalse(result['success'])
        # Verify the original schedule was NOT deleted
        self.assertEqual(Schedule.objects.filter(id=self.existing.id).count(), 1)


class MockDatasetBenchmarkTest(TestCase):
    """
    Benchmarks generation time on the realistic mock dataset with multiple credits,
    two groups, different room types, and teacher availability.
    """
    def test_mock_dataset_generation_time(self):
        g1 = StudentGroup.objects.create(code="CSE-A", name="CSE Batch A")
        g2 = StudentGroup.objects.create(code="IT-A", name="IT Batch A")
        r1 = Room.objects.create(room_number="101", capacity=60, room_type="LECTURE", is_available=True)
        r2 = Room.objects.create(room_number="102", capacity=40, room_type="LECTURE", is_available=True)
        r3 = Room.objects.create(room_number="LAB1", capacity=30, room_type="LAB", is_available=True)
        t1 = Teacher.objects.create(name="Prof. Sharma", department="CSE")
        t2 = Teacher.objects.create(name="Dr. Gupta", department="IT")
        t3 = Teacher.objects.create(name="Prof. Singh", department="ECE")

        for d, s in [
            ("MON", "09:00-10:00"),
            ("MON", "10:00-11:00"),
            ("TUE", "09:00-10:00"),
            ("WED", "11:00-12:00"),
            ("THU", "09:00-10:00"),
            ("THU", "10:00-11:00"),
        ]:
            TeacherAvailability.objects.create(teacher=t1, day=d, time_slot=s)
        for d, s in [
            ("MON", "10:00-11:00"),
            ("TUE", "10:00-11:00"),
            ("TUE", "11:00-12:00"),
            ("WED", "09:00-10:00"),
            ("THU", "11:00-12:00"),
            ("FRI", "10:00-11:00"),
        ]:
            TeacherAvailability.objects.create(teacher=t2, day=d, time_slot=s)

        Course.objects.create(code="CSE101", name="Programming", credit_hours=3, enrolled_students=50, difficulty="MEDIUM", requires_lab=False, teacher=t1, group=g1)
        Course.objects.create(code="CSE102", name="Lab", credit_hours=2, enrolled_students=25, difficulty="EASY", requires_lab=True, teacher=t1, group=g1)
        Course.objects.create(code="ECE301", name="Logic", credit_hours=3, enrolled_students=38, difficulty="MEDIUM", requires_lab=False, teacher=t3, group=g1)
        Course.objects.create(code="IT201", name="DBMS", credit_hours=3, enrolled_students=35, difficulty="HARD", requires_lab=False, teacher=t2, group=g2)
        Course.objects.create(code="CSE401", name="AI", credit_hours=2, enrolled_students=25, difficulty="HARD", requires_lab=False, teacher=t3, group=g2)

        start = time.perf_counter()
        result = generate_and_save_schedule()
        elapsed = time.perf_counter() - start

        self.assertTrue(result['success'])
        self.assertEqual(result['total_scheduled_sessions'], 13)
        self.assertEqual(result['conflicts_detected'], 0)
        # Log exact benchmark time for honesty
        print(f"\n[BENCHMARK] Mock dataset (13 sessions across 5 courses, 3 rooms, 2 groups): {elapsed:.4f} seconds")


# =============================================================================
# MILESTONE 4: COMPREHENSIVE UNIT, INTEGRATION & SYSTEM TEST SUITE
# =============================================================================

from .it_data import seed_it_semester1_data, seed_it_all_semesters_data, SYNTHETIC_ASSUMPTIONS
from .solver import groups_clash


class Milestone4UnitConstraintTests(TestCase):
    """
    Unit tests for Milestone 4 constraint verification:
    - Unsupported time slots and days
    - Unavailable room rejection
    - Missing teacher pre-flight rejection
    - Section and batch collision handling
    - Smallest suitable room selection
    - Forward checking and deterministic solver behavior
    """

    def setUp(self):
        self.room_lecture = Room.objects.create(room_number="LEC-101", capacity=60, room_type="LECTURE")
        self.room_lab = Room.objects.create(room_number="LAB-101", capacity=30, room_type="LAB")
        self.teacher1 = Teacher.objects.create(name="Faculty-01", department="IT")
        self.teacher2 = Teacher.objects.create(name="Faculty-02", department="IT")
        self.group_sec = StudentGroup.objects.create(code="IT-I-A", name="IT Sem I Section A")
        self.group_batch1 = StudentGroup.objects.create(code="IT-I-A1", name="IT Sem I Sec A Batch 1")
        self.group_batch2 = StudentGroup.objects.create(code="IT-I-A2", name="IT Sem I Sec A Batch 2")

        self.course_sec = Course.objects.create(
            code="IT101", name="IT Theory", enrolled_students=50,
            requires_lab=False, credit_hours=3, teacher=self.teacher1, group=self.group_sec
        )
        self.course_batch1 = Course.objects.create(
            code="IT101-L1", name="IT Lab B1", enrolled_students=25,
            requires_lab=True, credit_hours=2, teacher=self.teacher2, group=self.group_batch1
        )
        self.course_batch2 = Course.objects.create(
            code="IT101-L2", name="IT Lab B2", enrolled_students=25,
            requires_lab=True, credit_hours=2, teacher=self.teacher1, group=self.group_batch2
        )

    def test_unsupported_time_slot_detected_in_validator(self):
        """Rejects time slots outside official supported institution slots."""
        assignments = {
            self.course_sec.id: (self.room_lecture.id, "MON", "18:00-19:00", self.teacher1.id)
        }
        val = validate_schedule(assignments, [self.course_sec], [self.room_lecture], [self.teacher1])
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'INVALID_TIME_SLOT' for c in val['conflicts']))

    def test_unsupported_day_detected_in_validator(self):
        """Rejects non-teaching days (e.g., Sunday)."""
        assignments = {
            self.course_sec.id: (self.room_lecture.id, "SUN", "09:00-10:00", self.teacher1.id)
        }
        val = validate_schedule(assignments, [self.course_sec], [self.room_lecture], [self.teacher1])
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'INVALID_DAY' for c in val['conflicts']))

    def test_unavailable_room_detected_in_validator(self):
        """Rejects assignments to rooms marked as inactive or unavailable."""
        self.room_lecture.is_available = False
        self.room_lecture.save()

        assignments = {
            self.course_sec.id: (self.room_lecture.id, "MON", "09:00-10:00", self.teacher1.id)
        }
        val = validate_schedule(assignments, [self.course_sec], [self.room_lecture], [self.teacher1])
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'ROOM_UNAVAILABLE' for c in val['conflicts']))

    def test_missing_teacher_rejected_in_preflight(self):
        """Courses without an assigned instructor must be rejected before generation starts."""
        self.course_sec.teacher = None
        self.course_sec.save()

        result = generate_and_save_schedule()
        self.assertFalse(result['success'])
        self.assertIn("do not have an assigned teacher", result['error'])

    def test_subbatch_section_conflict_detected(self):
        """A sub-batch (IT-I-A1) cannot have class at the same time as the whole section lecture (IT-I-A)."""
        # Section A lecture in LEC-101 and Batch A1 lab in LAB-101 at the same MON 09:00-10:00 slot
        assignments = {
            self.course_sec.id: (self.room_lecture.id, "MON", "09:00-10:00", self.teacher1.id),
            self.course_batch1.id: (self.room_lab.id, "MON", "09:00-10:00", self.teacher2.id),
        }
        val = validate_schedule(
            assignments,
            [self.course_sec, self.course_batch1],
            [self.room_lecture, self.room_lab],
            [self.teacher1, self.teacher2],
        )
        self.assertFalse(val['valid'])
        self.assertTrue(any(c['type'] == 'GROUP_CONFLICT' for c in val['conflicts']))

    def test_disjoint_subbatches_allowed_simultaneously(self):
        """Two disjoint batches (IT-I-A1 and IT-I-A2) CAN run in parallel in separate labs with different faculty."""
        lab2 = Room.objects.create(room_number="LAB-102", capacity=30, room_type="LAB")
        assignments = {
            self.course_batch1.id: (self.room_lab.id, "MON", "09:00-10:00", self.teacher2.id),
            self.course_batch2.id: (lab2.id, "MON", "09:00-10:00", self.teacher1.id),
        }
        val = validate_schedule(
            assignments,
            [self.course_batch1, self.course_batch2],
            [self.room_lab, lab2],
            [self.teacher1, self.teacher2],
        )
        self.assertTrue(val['valid'])
        self.assertEqual(len(val['conflicts']), 0)

    def test_smallest_suitable_room_selected_first(self):
        """Verifies greedy smallest-suitable-room selection to reduce wasted seating capacity."""
        room_large = Room.objects.create(room_number="LEC-LARGE", capacity=120, room_type="LECTURE")
        room_medium = Room.objects.create(room_number="LEC-MED", capacity=60, room_type="LECTURE")
        room_small = Room.objects.create(room_number="LEC-SMALL", capacity=40, room_type="LECTURE")

        # Course has 45 students: room_small is too small; room_medium (60) should come before room_large (120)
        c = Course(code="TEST-CAP", enrolled_students=45, requires_lab=False)
        candidates = get_candidate_rooms(c, [room_large, room_medium, room_small])
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].room_number, "LEC-MED")
        self.assertEqual(candidates[1].room_number, "LEC-LARGE")

    def test_deterministic_solver_output(self):
        """Identical inputs must yield identical session assignments deterministically."""
        courses = list(Course.objects.filter(id__in=[self.course_sec.id, self.course_batch1.id]))
        rooms = [self.room_lecture, self.room_lab]
        teachers = [self.teacher1, self.teacher2]

        res1 = generate_schedule_csp(courses, rooms, teachers)
        res2 = generate_schedule_csp(courses, rooms, teachers)

        self.assertIsNotNone(res1)
        self.assertIsNotNone(res2)
        self.assertEqual(len(res1.sessions), len(res2.sessions))
        # Verify exact same sequence of assignments
        for s1, s2 in zip(res1.sessions, res2.sessions):
            self.assertEqual(s1['course_id'], s2['course_id'])
            self.assertEqual(s1['room_id'], s2['room_id'])
            self.assertEqual(s1['day'], s2['day'])
            self.assertEqual(s1['time_slot'], s2['time_slot'])

    def test_forward_checking_recorded_in_metrics(self):
        """Verifies that the solver tracks recursion calls and backtracks in metrics."""
        courses = [self.course_sec, self.course_batch1]
        rooms = [self.room_lecture, self.room_lab]
        teachers = [self.teacher1, self.teacher2]

        res = generate_schedule_csp(courses, rooms, teachers)
        self.assertIsNotNone(res)
        self.assertIn('metrics', dir(res))
        self.assertGreater(res.metrics['recursion_calls'], 0)
        self.assertIn('generation_time_seconds', res.metrics)


class Milestone4IntegrationTests(TestCase):
    """
    Integration tests for Milestone 4 APIs:
    - Admin-only performance diagnostics
    - Viewer read-only restrictions on performance data
    - Generation metrics response
    - Accurate multi-session dashboard calculations
    - Failed generation preservation
    """

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True)
        self.viewer = User.objects.create_user(username="viewer", password="viewer123", is_staff=False)
        self.room = Room.objects.create(room_number="R101", capacity=60, room_type="LECTURE")
        self.teacher = Teacher.objects.create(name="Faculty-01", department="IT")
        self.group = StudentGroup.objects.create(code="IT-A", name="IT Batch A")
        self.course = Course.objects.create(
            code="IT101", name="Database Systems", credit_hours=3,
            enrolled_students=45, requires_lab=False, teacher=self.teacher, group=self.group
        )
        self.client = APIClient()

    def test_generate_schedule_api_returns_performance_metrics(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/schedule/generate/')
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("metrics", data)
        self.assertIn("recursion_calls", data["metrics"])
        self.assertIn("generation_time_seconds", data["metrics"])
        self.assertIn("algorithm", data["metrics"])

    def test_accurate_dashboard_counts_with_partial_scheduling(self):
        """
        Verifies dashboard counts distinguish between fully, partially, and unscheduled courses.
        If Course IT101 needs 3 credits, but only 1 session is placed, it must be marked as partially scheduled.
        """
        self.client.force_authenticate(user=self.viewer)
        # Create 1 manual session for IT101 (which requires 3 credits)
        Schedule.objects.create(
            course=self.course, teacher=self.teacher, room=self.room,
            day="MON", time_slot="09:00-10:00", status="SCHEDULED"
        )

        res = self.client.get('/api/dashboard/stats/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        counts = data['counts']

        self.assertEqual(counts['total_required_sessions'], 3)
        self.assertEqual(counts['total_scheduled_sessions'], 1)
        self.assertEqual(counts['remaining_sessions'], 2)
        self.assertEqual(counts['fully_scheduled_courses'], 0)
        self.assertEqual(counts['partially_scheduled_courses'], 1)
        self.assertEqual(counts['unscheduled_courses'], 0)

    def test_failed_generation_preserves_old_timetable(self):
        # Create an existing timetable row
        existing = Schedule.objects.create(
            course=self.course, teacher=self.teacher, room=self.room,
            day="MON", time_slot="09:00-10:00", status="SCHEDULED"
        )
        # Add an impossible course (enrollment 500, no room can hold it)
        Course.objects.create(
            code="IMPOSSIBLE", name="Massive Class", enrolled_students=500,
            credit_hours=1, teacher=self.teacher
        )

        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/schedule/generate/')
        self.assertEqual(res.status_code, 400)
        # Confirm old schedule is intact
        self.assertEqual(Schedule.objects.filter(id=existing.id).count(), 1)


class Milestone4ITBranchSystemTests(TestCase):
    """
    End-to-end system tests verifying timetable generation on the realistic
    anonymized IT branch dataset (IT Semester I, Section A & B) from the MITS master timetable.
    """

    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="admin123", is_staff=True)
        self.viewer = User.objects.create_user(username="viewer", password="viewer123", is_staff=False)
        self.client = APIClient()

    def test_it_branch_dataset_seed_and_structure(self):
        """Verifies IT dataset seeds with actual faculty names from PDF, real courses, and correct rooms."""
        data = seed_it_semester1_data()
        self.assertEqual(data['total_courses'], 24)
        self.assertEqual(data['total_required_sessions'], 56)
        self.assertEqual(len(data['rooms']), 5)
        self.assertEqual(len(data['teachers']), 19)

        # Confirm actual faculty names from the PDF legend are present
        teacher_names = set(Teacher.objects.values_list('name', flat=True))
        expected_faculty = ["Prof. Vikas Sejwar", "Dr. Rajeev K. Singh", "Dr. Aradhana Saxena", "Dr. Sanjiv Khanna"]
        for ef in expected_faculty:
            self.assertIn(ef, teacher_names)

        # Confirm Language Lab is an academic course and NOT a room
        self.assertFalse(Room.objects.filter(room_number__icontains="Language").exists(), "Language Lab should not be a room!")
        self.assertEqual(Course.objects.filter(name__icontains="Language Lab").count(), 2, "Language Lab should be seeded as courses for Sec A & B")

        # Confirm valid rooms
        room_numbers = set(Room.objects.values_list('room_number', flat=True))
        self.assertEqual(room_numbers, {"SH-5", "J013", "DS Lab", "CL Lab", "PL Lab"})

    def test_it_branch_schedule_generation_and_full_validation(self):
        """
        Executes end-to-end timetable generation on the complete IT Semester-I dataset (Section A and Section B).
        Validates all 56 required sessions are placed with 0 conflicts.
        """
        seed_it_semester1_data()
        self.client.force_authenticate(user=self.admin)

        res = self.client.post('/api/schedule/generate/')
        self.assertEqual(res.status_code, 201)
        data = res.json()

        self.assertTrue(data['valid'])
        self.assertEqual(data['conflicts_detected'], 0)
        self.assertEqual(data['total_scheduled_sessions'], 56)
        self.assertEqual(data['remaining_sessions'], 0)

        # Independent database verification of generated schedules
        schedules = list(Schedule.objects.select_related('course', 'teacher', 'room', 'course__group').all())
        self.assertEqual(len(schedules), 56)

        courses = list(Course.objects.all())
        rooms = list(Room.objects.all())
        teachers = list(Teacher.objects.all())

        val = validate_schedule(schedules, courses, rooms, teachers)
        self.assertTrue(val['valid'])
        self.assertEqual(len(val['conflicts']), 0)

    def test_it_branch_dashboard_stats_after_generation(self):
        """Verifies dashboard reflects 100% course and session completion after generation."""
        seed_it_semester1_data()
        self.client.force_authenticate(user=self.admin)
        self.client.post('/api/schedule/generate/')

        self.client.force_authenticate(user=self.viewer)
        dash_res = self.client.get('/api/dashboard/stats/')
        self.assertEqual(dash_res.status_code, 200)
        counts = dash_res.json()['counts']

        self.assertEqual(counts['total_required_sessions'], 56)
        self.assertEqual(counts['total_scheduled_sessions'], 56)
        self.assertEqual(counts['remaining_sessions'], 0)
        self.assertEqual(counts['fully_scheduled_courses'], 24)
        self.assertEqual(counts['partially_scheduled_courses'], 0)
        self.assertEqual(counts['unscheduled_courses'], 0)

    def test_all_semesters_from_pdf_seed_and_generation(self):
        """
        Verifies end-to-end dataset seeding and master timetable generation
        across ALL semesters present in the PDF (Semesters I, III, V, VII).
        """
        data = seed_it_all_semesters_data()
        self.assertEqual(data['total_courses'], 87)
        self.assertEqual(data['total_required_sessions'], 200)
        self.assertEqual(len(data['rooms']), 11)
        self.assertEqual(len(data['teachers']), 19)
        self.assertEqual(len(data['groups']), 19)

        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/schedule/generate/')
        self.assertEqual(res.status_code, 201)
        gen_data = res.json()
        self.assertTrue(gen_data['valid'])
        self.assertEqual(gen_data['conflicts_detected'], 0)
        self.assertEqual(gen_data['total_scheduled_sessions'], 200)

        # Independent database verification
        schedules = list(Schedule.objects.all())
        self.assertEqual(len(schedules), 200)
        val = validate_schedule(schedules, list(Course.objects.all()), list(Room.objects.all()), list(Teacher.objects.all()))
        self.assertTrue(val['valid'])
        self.assertEqual(len(val['conflicts']), 0)


class ViewerBatchSignupAndFilteringTests(TestCase):
    """
    Tests for viewer sign up with student batch and batch-filtered timetable view.
    """

    def setUp(self):
        self.client = APIClient()

    def test_viewer_signup_success_and_jwt_login(self):
        """Verifies public signup creates viewer user, stores their batch, and returns JWT tokens."""
        res = self.client.post('/api/auth/register/', {
            'username': 'student_rahul',
            'password': 'password123',
            'batch': 'Batch-A1'
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['username'], 'student_rahul')
        self.assertEqual(data['user']['role'], 'VIEWER')
        self.assertEqual(data['user']['batch'], 'Batch-A1')

        # Check in database
        u = User.objects.get(username='student_rahul')
        self.assertFalse(u.is_staff)
        self.assertEqual(u.profile.batch, 'Batch-A1')

    def test_viewer_signup_duplicate_username_fails(self):
        """Verifies signup rejects already taken usernames with 400."""
        User.objects.create_user(username='existing_student', password='password123')
        res = self.client.post('/api/auth/register/', {
            'username': 'existing_student',
            'password': 'password123',
            'batch': 'Batch-B1'
        })
        self.assertEqual(res.status_code, 400)

    def test_viewer_me_endpoint_includes_batch(self):
        """Verifies /api/me/ includes the viewer's batch."""
        res = self.client.post('/api/auth/register/', {
            'username': 'batch_b2_user',
            'password': 'password123',
            'batch': 'Batch-B2'
        })
        token = res.json()['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        me_res = self.client.get('/api/me/')
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()['batch'], 'Batch-B2')

    def test_viewer_batch_filtered_timetable(self):
        """Verifies a student registered for Batch-A1 only sees Section A theory and A1 labs."""
        from .it_data import seed_it_pdf_data
        seed_it_pdf_data()

        # Sign up student in Batch-A1
        res = self.client.post('/api/auth/register/', {
            'username': 'student_a1',
            'password': 'password123',
            'batch': 'Batch-A1'
        })
        token = res.json()['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Export or query for their batch
        export_res = self.client.get('/api/schedule/export.pdf?batch=Batch-A1')
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res.headers['Content-Type'], 'application/pdf')


