"""
it_data.py - Authentic IT Branch Timetable Dataset (MITS Gwalior).

Source:
Reference timetable structure, course codes, rooms, and faculty names taken directly from:
"Revised Master TimeTable July-Dec 2026" (School of Information Technology, MITS Gwalior).

Scope:
All four undergraduate semesters present in the official document:
- Semester I (Sections A & B + Batches A1, A2, B1, B2)
- Semester III (Sections A & B + Batches A1, A2, B1, B2)
- Semester V (Sections A & B + Batches A1, A2, B1, B2)
- Semester VII (Final Year Cohort)

Clarifications applied:
1. Faculty names taken directly from the official PDF legend (Dr. Akhilesh Tiwari, Prof. Vikas Sejwar, etc.).
2. 'Language Lab' (Code 16261110) is an academic course, NOT a classroom/room.
3. Rooms are the official lecture halls ('SH-5', 'J013', '116', 'J127', '115', 'J118')
   and specialized laboratories ('DS Lab', 'CL Lab', 'PL Lab', 'PR Lab', 'H/W Lab').
"""

from .models import Room, Teacher, TeacherAvailability, StudentGroup, Course, Schedule

# Faculty legend mapping from MITS Time Table PDF (19 standard faculty)
FACULTY_LEGEND = [
    ("AT", "Dr. Akhilesh Tiwari"),
    ("SS", "Dr. Sanjiv Sharma"),
    ("PJ", "Dr. Punit Kumar Johari"),
    ("AS", "Dr. Abhilash Sonker"),
    ("VS", "Prof. Vikas Sejwar"),
    ("RKS", "Dr. Rajeev K. Singh"),
    ("NB", "Prof. Neha Bhardwaj"),
    ("VR", "Dr. Vikram Rajpoot"),
    ("GS", "Dr. Gulshan Soni"),
    ("AS1", "Dr. Aradhana Saxena"),
    ("SS1", "Prof. Shubham Sharma"),
    ("KD", "Prof. Kumud Dixit"),
    ("SG", "Prof. Surbhi Gupta"),
    ("TS", "Mrs. Tanuja Sharma"),
    ("SK", "Dr. Sanjiv Khanna"),
    ("GF", "Guest Faculty"),
    ("TJ", "Prof. T.J."),
    ("PSC", "Prof. P.S.C."),
    ("MATHS", "Department of Mathematics"),
]

# Complete faculty legend from Semester-I PDF page (NRGF is excluded because it is a classroom)
PDF_FACULTY_LEGEND = [abbr_name for abbr_name in FACULTY_LEGEND if abbr_name[0] not in ("NRGF", "GF")] + [
    ("JM", "Dr. J.K. Muthele"),
    ("DP", "Divya Pundhir"),
]

# Explicit synthetic assumptions for testing parameters not in PDF
SYNTHETIC_ASSUMPTIONS = {
    "data_source": "Official MITS IT Branch Timetable (July-Dec 2026, Pages 1-4: Semesters I, III, V, VII)",
    "room_capacities": {
        "SH-5": {"capacity": 70, "type": "LECTURE", "status": "Synthetic Assumption"},
        "J013": {"capacity": 70, "type": "LECTURE", "status": "Synthetic Assumption"},
        "116": {"capacity": 70, "type": "LECTURE", "status": "Synthetic Assumption"},
        "J127": {"capacity": 70, "type": "LECTURE", "status": "Synthetic Assumption"},
        "115": {"capacity": 70, "type": "LECTURE", "status": "Synthetic Assumption"},
        "J118": {"capacity": 70, "type": "LECTURE", "status": "Synthetic Assumption"},
        "DS Lab": {"capacity": 35, "type": "LAB", "status": "Synthetic Assumption"},
        "CL Lab": {"capacity": 35, "type": "LAB", "status": "Synthetic Assumption"},
        "PL Lab": {"capacity": 35, "type": "LAB", "status": "Synthetic Assumption"},
        "PR Lab": {"capacity": 35, "type": "LAB", "status": "Synthetic Assumption"},
        "H/W Lab": {"capacity": 35, "type": "LAB", "status": "Synthetic Assumption"},
    },
    "group_strengths": {
        "Whole Section Cohorts (Sem I, III, V, VII)": 60,
        "Laboratory Sub-Batches (A1, A2, B1, B2)": 30,
    },
    "course_credits_synthetic": {
        "Theory": 3,
        "Labs / Practicals": 2,
        "Language Lab": 1,
    },
}

ALL_ROOMS_DATA = [
    ("SH-5", 70, "LECTURE"),
    ("J013", 70, "LECTURE"),
    ("NRGF", 70, "LECTURE"),
    ("116", 70, "LECTURE"),
    ("J127", 70, "LECTURE"),
    ("115", 70, "LECTURE"),
    ("DS Lab", 35, "LAB"),
    ("CL Lab", 35, "LAB"),
    ("PL Lab", 35, "LAB"),
    ("PR Lab", 35, "LAB"),
    ("H/W Lab", 35, "LAB"),
]


def seed_it_all_semesters_data():
    """
    Seeds the complete IT department curriculum from all 4 pages of the MITS timetable PDF:
    - Semester I (Sec A, Sec B, Batches A1, A2, B1, B2)
    - Semester III (Sec A, Sec B, Batches A1, A2, B1, B2)
    - Semester V (Sec A, Sec B, Batches A1, A2, B1, B2)
    - Semester VII (Final Year cohort)
    """
    # 1. Clear previous records
    Schedule.objects.all().delete()
    Course.objects.all().delete()
    TeacherAvailability.objects.all().delete()
    Teacher.objects.all().delete()
    StudentGroup.objects.all().delete()
    Room.objects.all().delete()

    # 2. Rooms from all semesters
    rooms = {}
    for r_num, cap, r_type in ALL_ROOMS_DATA:
        rooms[r_num] = Room.objects.create(
            room_number=r_num,
            capacity=cap,
            room_type=r_type,
            is_available=True,
        )

    # 3. Faculty members from official PDF legend
    teachers = {}
    for abbr, full_name in FACULTY_LEGEND:
        t_obj = Teacher.objects.create(name=full_name, department="Information Technology")
        teachers[abbr] = t_obj

    # 4. Student Groups & Batches across Semesters I, III, V, VII
    groups = {
        # Sem I
        "IT-I-A": StudentGroup.objects.create(code="IT-I-A", name="B.Tech IT Sem-I (Sec A)"),
        "IT-I-B": StudentGroup.objects.create(code="IT-I-B", name="B.Tech IT Sem-I (Sec B)"),
        "IT-I-A1": StudentGroup.objects.create(code="IT-I-A1", name="B.Tech IT Sem-I (Sec A - Batch 1)"),
        "IT-I-A2": StudentGroup.objects.create(code="IT-I-A2", name="B.Tech IT Sem-I (Sec A - Batch 2)"),
        "IT-I-B1": StudentGroup.objects.create(code="IT-I-B1", name="B.Tech IT Sem-I (Sec B - Batch 1)"),
        "IT-I-B2": StudentGroup.objects.create(code="IT-I-B2", name="B.Tech IT Sem-I (Sec B - Batch 2)"),

        # Sem III
        "IT-III-A": StudentGroup.objects.create(code="IT-III-A", name="B.Tech IT Sem-III (Sec A)"),
        "IT-III-B": StudentGroup.objects.create(code="IT-III-B", name="B.Tech IT Sem-III (Sec B)"),
        "IT-III-A1": StudentGroup.objects.create(code="IT-III-A1", name="B.Tech IT Sem-III (Sec A - Batch 1)"),
        "IT-III-A2": StudentGroup.objects.create(code="IT-III-A2", name="B.Tech IT Sem-III (Sec A - Batch 2)"),
        "IT-III-B1": StudentGroup.objects.create(code="IT-III-B1", name="B.Tech IT Sem-III (Sec B - Batch 1)"),
        "IT-III-B2": StudentGroup.objects.create(code="IT-III-B2", name="B.Tech IT Sem-III (Sec B - Batch 2)"),

        # Sem V
        "IT-V-A": StudentGroup.objects.create(code="IT-V-A", name="B.Tech IT Sem-V (Sec A)"),
        "IT-V-B": StudentGroup.objects.create(code="IT-V-B", name="B.Tech IT Sem-V (Sec B)"),
        "IT-V-A1": StudentGroup.objects.create(code="IT-V-A1", name="B.Tech IT Sem-V (Sec A - Batch 1)"),
        "IT-V-A2": StudentGroup.objects.create(code="IT-V-A2", name="B.Tech IT Sem-V (Sec A - Batch 2)"),
        "IT-V-B1": StudentGroup.objects.create(code="IT-V-B1", name="B.Tech IT Sem-V (Sec B - Batch 1)"),
        "IT-V-B2": StudentGroup.objects.create(code="IT-V-B2", name="B.Tech IT Sem-V (Sec B - Batch 2)"),

        # Sem VII
        "IT-VII": StudentGroup.objects.create(code="IT-VII", name="B.Tech IT Sem-VII"),
    }

    # 5. Teaching Availability Windows across standard slots
    days = ["MON", "TUE", "WED", "THU", "FRI"]
    time_slots = [
        "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00",
        "13:00-14:00", "14:00-15:00", "15:00-16:00"
    ]
    for t in teachers.values():
        for d in days:
            for ts in time_slots:
                TeacherAvailability.objects.create(teacher=t, day=d, time_slot=ts)

    courses = []

    # ================= SEMESTER I (Page 1) =================
    # Section A Theory
    courses.append(Course.objects.create(code="16261101-A", name="Introduction to IT (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["VS"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261102-A", name="Computer Programming (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["AS1"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261103-A", name="Digital Logic Design (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["RKS"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261104-A", name="Discrete Structures (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["VR"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261105-A", name="Statistical Techniques (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["GS"], group=groups["IT-I-A"]))
    # Section A Labs
    courses.append(Course.objects.create(code="16261106-A1", name="Computer Programming Lab (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["AS1"], group=groups["IT-I-A1"]))
    courses.append(Course.objects.create(code="16261106-A2", name="Computer Programming Lab (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SG"], group=groups["IT-I-A2"]))
    courses.append(Course.objects.create(code="16261107-A1", name="IT Workshop (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-I-A1"]))
    courses.append(Course.objects.create(code="16261107-A2", name="IT Workshop (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["TS"], group=groups["IT-I-A2"]))
    courses.append(Course.objects.create(code="16261109-A1", name="Micro Project-I (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["GS"], group=groups["IT-I-A1"]))
    courses.append(Course.objects.create(code="16261109-A2", name="Micro Project-I (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-I-A2"]))
    courses.append(Course.objects.create(code="16261110-A", name="Language Lab (Sec A)", credit_hours=1, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SK"], group=groups["IT-I-A"]))

    # Section B Theory
    courses.append(Course.objects.create(code="16261101-B", name="Introduction to IT (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["VS"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261102-B", name="Computer Programming (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["AS1"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261103-B", name="Digital Logic Design (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["RKS"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261104-B", name="Discrete Structures (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["VR"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261105-B", name="Statistical Techniques (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["GS"], group=groups["IT-I-B"]))
    # Section B Labs
    courses.append(Course.objects.create(code="16261106-B1", name="Computer Programming Lab (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["AS1"], group=groups["IT-I-B1"]))
    courses.append(Course.objects.create(code="16261106-B2", name="Computer Programming Lab (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SG"], group=groups["IT-I-B2"]))
    courses.append(Course.objects.create(code="16261107-B1", name="IT Workshop (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-I-B1"]))
    courses.append(Course.objects.create(code="16261107-B2", name="IT Workshop (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["TS"], group=groups["IT-I-B2"]))
    courses.append(Course.objects.create(code="16261109-B1", name="Micro Project-I (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["AS"], group=groups["IT-I-B1"]))
    courses.append(Course.objects.create(code="16261109-B2", name="Micro Project-I (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-I-B2"]))
    courses.append(Course.objects.create(code="16261110-B", name="Language Lab (Sec B)", credit_hours=1, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SK"], group=groups["IT-I-B"]))

    # ================= SEMESTER III (Page 2) =================
    # Section A Theory
    courses.append(Course.objects.create(code="16252101-A", name="Transforms & Vector Calculus (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["MATHS"], group=groups["IT-III-A"]))
    courses.append(Course.objects.create(code="16252102-A", name="Design & Analysis of Algorithms (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["KD"], group=groups["IT-III-A"]))
    courses.append(Course.objects.create(code="16252103-A", name="Database Management System (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["PJ"], group=groups["IT-III-A"]))
    courses.append(Course.objects.create(code="16252104-A", name="Operating Systems (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["SS"], group=groups["IT-III-A"]))
    courses.append(Course.objects.create(code="16252105-A", name="Computer Networks (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["GS"], group=groups["IT-III-A"]))
    courses.append(Course.objects.create(code="16252112-A", name="Cyber Security (Sec A)", credit_hours=2, enrolled_students=60, difficulty="EASY", requires_lab=False, teacher=teachers["SG"], group=groups["IT-III-A"]))
    # Section A Labs
    courses.append(Course.objects.create(code="16252106-A1", name="DAA Lab (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="HARD", requires_lab=True, teacher=teachers["KD"], group=groups["IT-III-A1"]))
    courses.append(Course.objects.create(code="16252106-A2", name="DAA Lab (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="HARD", requires_lab=True, teacher=teachers["AS"], group=groups["IT-III-A2"]))
    courses.append(Course.objects.create(code="16252107-A1", name="DBMS Lab (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["PJ"], group=groups["IT-III-A1"]))
    courses.append(Course.objects.create(code="16252107-A2", name="DBMS Lab (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VR"], group=groups["IT-III-A2"]))
    courses.append(Course.objects.create(code="16252108-A1", name="Python Programming Lab (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SS"], group=groups["IT-III-A1"]))
    courses.append(Course.objects.create(code="16252108-A2", name="Python Programming Lab (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SG"], group=groups["IT-III-A2"]))
    courses.append(Course.objects.create(code="16252110-A1", name="Macro Project-I (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VR"], group=groups["IT-III-A1"]))
    courses.append(Course.objects.create(code="16252110-A2", name="Macro Project-I (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["SS1"], group=groups["IT-III-A2"]))

    # Section B Theory
    courses.append(Course.objects.create(code="16252101-B", name="Transforms & Vector Calculus (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["MATHS"], group=groups["IT-III-B"]))
    courses.append(Course.objects.create(code="16252102-B", name="Design & Analysis of Algorithms (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["KD"], group=groups["IT-III-B"]))
    courses.append(Course.objects.create(code="16252103-B", name="Database Management System (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["PJ"], group=groups["IT-III-B"]))
    courses.append(Course.objects.create(code="16252104-B", name="Operating Systems (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["SS"], group=groups["IT-III-B"]))
    courses.append(Course.objects.create(code="16252105-B", name="Computer Networks (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["GS"], group=groups["IT-III-B"]))
    courses.append(Course.objects.create(code="16252112-B", name="Cyber Security (Sec B)", credit_hours=2, enrolled_students=60, difficulty="EASY", requires_lab=False, teacher=teachers["SG"], group=groups["IT-III-B"]))
    # Section B Labs
    courses.append(Course.objects.create(code="16252106-B1", name="DAA Lab (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="HARD", requires_lab=True, teacher=teachers["KD"], group=groups["IT-III-B1"]))
    courses.append(Course.objects.create(code="16252106-B2", name="DAA Lab (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="HARD", requires_lab=True, teacher=teachers["RKS"], group=groups["IT-III-B2"]))
    courses.append(Course.objects.create(code="16252107-B1", name="DBMS Lab (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["PJ"], group=groups["IT-III-B1"]))
    courses.append(Course.objects.create(code="16252107-B2", name="DBMS Lab (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VR"], group=groups["IT-III-B2"]))
    courses.append(Course.objects.create(code="16252108-B1", name="Python Programming Lab (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SS"], group=groups["IT-III-B1"]))
    courses.append(Course.objects.create(code="16252108-B2", name="Python Programming Lab (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SG"], group=groups["IT-III-B2"]))
    courses.append(Course.objects.create(code="16252110-B1", name="Macro Project-I (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VR"], group=groups["IT-III-B1"]))
    courses.append(Course.objects.create(code="16252110-B2", name="Macro Project-I (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["PJ"], group=groups["IT-III-B2"]))

    # ================= SEMESTER V (Page 3) =================
    # Section A Theory
    courses.append(Course.objects.create(code="16243101-A", name="Mobile Computing & Wireless (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["AT"], group=groups["IT-V-A"]))
    courses.append(Course.objects.create(code="16243102-A", name="Theory of Computation (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["AS"], group=groups["IT-V-A"]))
    courses.append(Course.objects.create(code="16243103-A", name="Soft Computing Techniques (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["SS1"], group=groups["IT-V-A"]))
    courses.append(Course.objects.create(code="16243104-A", name="Network & Web Security (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["NB"], group=groups["IT-V-A"]))
    courses.append(Course.objects.create(code="16243110-A", name="Supply Chain Management (Sec A)", credit_hours=2, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["TS"], group=groups["IT-V-A"]))
    courses.append(Course.objects.create(code="162431XX-A", name="Departmental Elective DE-1 (Sec A)", credit_hours=2, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["AS"], group=groups["IT-V-A"]))
    # Section A Labs
    courses.append(Course.objects.create(code="16243105-A1", name="Java Programming Lab (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["GS"], group=groups["IT-V-A1"]))
    courses.append(Course.objects.create(code="16243105-A2", name="Java Programming Lab (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["KD"], group=groups["IT-V-A2"]))
    courses.append(Course.objects.create(code="16243106-A1", name="Soft Computing Lab (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["SS1"], group=groups["IT-V-A1"]))
    courses.append(Course.objects.create(code="16243106-A2", name="Soft Computing Lab (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["AT"], group=groups["IT-V-A2"]))
    courses.append(Course.objects.create(code="16243107-A1", name="Network & Web Security Lab (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="HARD", requires_lab=True, teacher=teachers["NB"], group=groups["IT-V-A1"]))
    courses.append(Course.objects.create(code="16243107-A2", name="Network & Web Security Lab (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="HARD", requires_lab=True, teacher=teachers["AS1"], group=groups["IT-V-A2"]))
    courses.append(Course.objects.create(code="16243109-A1", name="Cornerstone Project (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["TJ"], group=groups["IT-V-A1"]))
    courses.append(Course.objects.create(code="16243109-A2", name="Cornerstone Project (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-V-A2"]))

    # Section B Theory
    courses.append(Course.objects.create(code="16243101-B", name="Mobile Computing & Wireless (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["AT"], group=groups["IT-V-B"]))
    courses.append(Course.objects.create(code="16243102-B", name="Theory of Computation (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["AS"], group=groups["IT-V-B"]))
    courses.append(Course.objects.create(code="16243103-B", name="Soft Computing Techniques (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["SS1"], group=groups["IT-V-B"]))
    courses.append(Course.objects.create(code="16243104-B", name="Network & Web Security (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["NB"], group=groups["IT-V-B"]))
    courses.append(Course.objects.create(code="16243110-B", name="Supply Chain Management (Sec B)", credit_hours=2, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["TS"], group=groups["IT-V-B"]))
    courses.append(Course.objects.create(code="162431XX-B", name="Departmental Elective DE-1 (Sec B)", credit_hours=2, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["TJ"], group=groups["IT-V-B"]))
    # Section B Labs
    courses.append(Course.objects.create(code="16243105-B1", name="Java Programming Lab (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["GS"], group=groups["IT-V-B1"]))
    courses.append(Course.objects.create(code="16243105-B2", name="Java Programming Lab (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["TS"], group=groups["IT-V-B2"]))
    courses.append(Course.objects.create(code="16243106-B1", name="Soft Computing Lab (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["SS1"], group=groups["IT-V-B1"]))
    courses.append(Course.objects.create(code="16243106-B2", name="Soft Computing Lab (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["AT"], group=groups["IT-V-B2"]))
    courses.append(Course.objects.create(code="16243107-B1", name="Network & Web Security Lab (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="HARD", requires_lab=True, teacher=teachers["NB"], group=groups["IT-V-B1"]))
    courses.append(Course.objects.create(code="16243107-B2", name="Network & Web Security Lab (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="HARD", requires_lab=True, teacher=teachers["SG"], group=groups["IT-V-B2"]))
    courses.append(Course.objects.create(code="16243109-B1", name="Cornerstone Project (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["AS"], group=groups["IT-V-B1"]))
    courses.append(Course.objects.create(code="16243109-B2", name="Cornerstone Project (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VR"], group=groups["IT-V-B2"]))

    # ================= SEMESTER VII (Page 4) =================
    courses.append(Course.objects.create(code="DE-2-VII", name="Departmental Elective (DE-2)", credit_hours=2, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["RKS"], group=groups["IT-VII"]))
    courses.append(Course.objects.create(code="DE-3-VII", name="Departmental Elective (DE-3)", credit_hours=2, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["AS1"], group=groups["IT-VII"]))
    courses.append(Course.objects.create(code="OC-2-VII", name="Open Category (OC-2)", credit_hours=2, enrolled_students=60, difficulty="EASY", requires_lab=False, teacher=teachers["GF"], group=groups["IT-VII"]))
    courses.append(Course.objects.create(code="1000008-VII", name="Universal Human Values (UHVPE)", credit_hours=2, enrolled_students=60, difficulty="EASY", requires_lab=False, teacher=teachers["RKS"], group=groups["IT-VII"]))
    courses.append(Course.objects.create(code="3160714-VII", name="Professional Skills & Competencies", credit_hours=2, enrolled_students=60, difficulty="EASY", requires_lab=False, teacher=teachers["PSC"], group=groups["IT-VII"]))
    courses.append(Course.objects.create(code="3160711-VII", name="Departmental Lab (Net Security)", credit_hours=2, enrolled_students=35, difficulty="HARD", requires_lab=True, teacher=teachers["NB"], group=groups["IT-VII"]))
    courses.append(Course.objects.create(code="3160712-VII", name="Creative Problem Solving Lab", credit_hours=2, enrolled_students=35, difficulty="MEDIUM", requires_lab=True, teacher=teachers["SS1"], group=groups["IT-VII"]))

    total_sessions = sum(c.credit_hours for c in courses)

    return {
        "rooms": rooms,
        "teachers": teachers,
        "groups": groups,
        "courses": courses,
        "total_courses": len(courses),
        "total_required_sessions": total_sessions,
        "semesters_included": ["I", "III", "V", "VII"],
    }


def seed_it_semester1_data():
    """
    Seeds only IT Semester-I (Section A & Section B) for focused testing.
    """
    Schedule.objects.all().delete()
    Course.objects.all().delete()
    TeacherAvailability.objects.all().delete()
    Teacher.objects.all().delete()
    StudentGroup.objects.all().delete()
    Room.objects.all().delete()

    rooms_data = [
        ("SH-5", 70, "LECTURE"),
        ("J013", 70, "LECTURE"),
        ("DS Lab", 35, "LAB"),
        ("CL Lab", 35, "LAB"),
        ("PL Lab", 35, "LAB"),
    ]
    rooms = {}
    for r_num, cap, r_type in rooms_data:
        rooms[r_num] = Room.objects.create(
            room_number=r_num,
            capacity=cap,
            room_type=r_type,
            is_available=True,
        )

    teachers = {}
    for abbr, full_name in FACULTY_LEGEND:
        t_obj = Teacher.objects.create(name=full_name, department="Information Technology")
        teachers[abbr] = t_obj

    groups = {
        "IT-I-A": StudentGroup.objects.create(code="IT-I-A", name="B.Tech IT Sem-I (Section A)"),
        "IT-I-B": StudentGroup.objects.create(code="IT-I-B", name="B.Tech IT Sem-I (Section B)"),
        "IT-I-A1": StudentGroup.objects.create(code="IT-I-A1", name="B.Tech IT Sem-I (Sec A - Batch 1)"),
        "IT-I-A2": StudentGroup.objects.create(code="IT-I-A2", name="B.Tech IT Sem-I (Sec A - Batch 2)"),
        "IT-I-B1": StudentGroup.objects.create(code="IT-I-B1", name="B.Tech IT Sem-I (Sec B - Batch 1)"),
        "IT-I-B2": StudentGroup.objects.create(code="IT-I-B2", name="B.Tech IT Sem-I (Sec B - Batch 2)"),
    }

    days = ["MON", "TUE", "WED", "THU", "FRI"]
    time_slots = [
        "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00",
        "13:00-14:00", "14:00-15:00", "15:00-16:00"
    ]
    for t in teachers.values():
        for d in days:
            for ts in time_slots:
                TeacherAvailability.objects.create(teacher=t, day=d, time_slot=ts)

    courses = []
    # Section A
    courses.append(Course.objects.create(code="16261101-A", name="Introduction to Information Technology (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["VS"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261102-A", name="Computer Programming (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["AS1"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261103-A", name="Digital Logic Design (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["RKS"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261104-A", name="Discrete Structures (Sec A)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["VR"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261105-A", name="Statistical Techniques (Sec A)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["GS"], group=groups["IT-I-A"]))
    courses.append(Course.objects.create(code="16261106-A1", name="Computer Programming Lab (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["AS1"], group=groups["IT-I-A1"]))
    courses.append(Course.objects.create(code="16261106-A2", name="Computer Programming Lab (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SG"], group=groups["IT-I-A2"]))
    courses.append(Course.objects.create(code="16261107-A1", name="IT Workshop (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-I-A1"]))
    courses.append(Course.objects.create(code="16261107-A2", name="IT Workshop (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["TS"], group=groups["IT-I-A2"]))
    courses.append(Course.objects.create(code="16261109-A1", name="Micro Project-I (Batch A1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["GS"], group=groups["IT-I-A1"]))
    courses.append(Course.objects.create(code="16261109-A2", name="Micro Project-I (Batch A2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-I-A2"]))
    courses.append(Course.objects.create(code="16261110-A", name="Language Lab (Sec A)", credit_hours=1, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SK"], group=groups["IT-I-A"]))

    # Section B
    courses.append(Course.objects.create(code="16261101-B", name="Introduction to Information Technology (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["VS"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261102-B", name="Computer Programming (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["AS1"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261103-B", name="Digital Logic Design (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["RKS"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261104-B", name="Discrete Structures (Sec B)", credit_hours=3, enrolled_students=60, difficulty="HARD", requires_lab=False, teacher=teachers["VR"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261105-B", name="Statistical Techniques (Sec B)", credit_hours=3, enrolled_students=60, difficulty="MEDIUM", requires_lab=False, teacher=teachers["GS"], group=groups["IT-I-B"]))
    courses.append(Course.objects.create(code="16261106-B1", name="Computer Programming Lab (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["AS1"], group=groups["IT-I-B1"]))
    courses.append(Course.objects.create(code="16261106-B2", name="Computer Programming Lab (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SG"], group=groups["IT-I-B2"]))
    courses.append(Course.objects.create(code="16261107-B1", name="IT Workshop (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-I-B1"]))
    courses.append(Course.objects.create(code="16261107-B2", name="IT Workshop (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["TS"], group=groups["IT-I-B2"]))
    courses.append(Course.objects.create(code="16261109-B1", name="Micro Project-I (Batch B1)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["AS"], group=groups["IT-I-B1"]))
    courses.append(Course.objects.create(code="16261109-B2", name="Micro Project-I (Batch B2)", credit_hours=2, enrolled_students=30, difficulty="MEDIUM", requires_lab=True, teacher=teachers["VS"], group=groups["IT-I-B2"]))
    courses.append(Course.objects.create(code="16261110-B", name="Language Lab (Sec B)", credit_hours=1, enrolled_students=30, difficulty="EASY", requires_lab=True, teacher=teachers["SK"], group=groups["IT-I-B"]))

    return {
        "rooms": rooms,
        "teachers": teachers,
        "groups": groups,
        "courses": courses,
        "total_courses": len(courses),
        "total_required_sessions": sum(c.credit_hours for c in courses),
    }


def seed_it_pdf_data():
    """
    Seeds the EXACT IT Semester-I Time-Table from the official MITS PDF:
    - Section A (Theory in SH-5, Labs in DS Lab, CL Lab, PL Lab)
    - Section B (Theory in J013, Labs in DS Lab, CL Lab, PL Lab)
    - All 19 faculty members from the official PDF legend
    - All 11 course titles and codes
    - Exactly populates all 62 scheduled class sessions with 0 conflicts.
    """
    Schedule.objects.all().delete()
    Course.objects.all().delete()
    TeacherAvailability.objects.all().delete()
    Teacher.objects.all().delete()
    StudentGroup.objects.all().delete()
    Room.objects.all().delete()

    # 1. Rooms from PDF (including NRGF as a lecture classroom)
    rooms_data = [
        ("SH-5", 70, "LECTURE"),
        ("J013", 70, "LECTURE"),
        ("NRGF", 70, "LECTURE"),
        ("DS Lab", 35, "LAB"),
        ("CL Lab", 35, "LAB"),
        ("PL Lab", 35, "LAB"),
    ]
    rooms = {}
    for r_num, cap, r_type in rooms_data:
        rooms[r_num] = Room.objects.create(room_number=r_num, capacity=cap, room_type=r_type, is_available=True)

    # 2. Faculty from PDF Legend (including JM and DP)
    teachers = {}
    for abbr, full_name in PDF_FACULTY_LEGEND:
        teachers[abbr] = Teacher.objects.create(name=full_name, department="Information Technology")

    # 3. Student Groups & Batches
    groups = {
        "IT-I-A": StudentGroup.objects.create(code="IT-I-A", name="B.Tech IT Sem-I (Sec A)"),
        "IT-I-B": StudentGroup.objects.create(code="IT-I-B", name="B.Tech IT Sem-I (Sec B)"),
        "Batch-A1": StudentGroup.objects.create(code="Batch-A1", name="B.Tech IT Sem-I (Sec A - Batch 1)"),
        "Batch-A2": StudentGroup.objects.create(code="Batch-A2", name="B.Tech IT Sem-I (Sec A - Batch 2)"),
        "Batch-B1": StudentGroup.objects.create(code="Batch-B1", name="B.Tech IT Sem-I (Sec B - Batch 1)"),
        "Batch-B2": StudentGroup.objects.create(code="Batch-B2", name="B.Tech IT Sem-I (Sec B - Batch 2)"),
    }

    # 4. Teacher Availabilities across PDF slots
    pdf_slots = [
        "10:00-11:00", "11:00-12:00", "01:00-02:00", "02:00-03:00",
        "03:00-04:00", "04:00-05:00", "05:00-06:00"
    ]
    days = ["MON", "TUE", "WED", "THU", "FRI"]
    for t in teachers.values():
        for d in days:
            for ts in pdf_slots:
                TeacherAvailability.objects.create(teacher=t, day=d, time_slot=ts)

    # 5. Courses from PDF
    courses = {}
    # Section A Courses
    courses["16261101-A"] = Course.objects.create(code="16261101-A", name="Introduction to Information Technology", credit_hours=3, enrolled_students=60, requires_lab=False, teacher=teachers["VS"], group=groups["IT-I-A"])
    courses["16261102-A"] = Course.objects.create(code="16261102-A", name="Computer Programming", credit_hours=2, enrolled_students=60, requires_lab=False, teacher=teachers["AS1"], group=groups["IT-I-A"])
    courses["16261103-A"] = Course.objects.create(code="16261103-A", name="Digital Logic Design", credit_hours=3, enrolled_students=60, requires_lab=False, teacher=teachers["RKS"], group=groups["IT-I-A"])
    courses["16261104-A"] = Course.objects.create(code="16261104-A", name="Discrete Structures", credit_hours=3, enrolled_students=60, requires_lab=False, teacher=teachers["VR"], group=groups["IT-I-A"])
    courses["16261105-A"] = Course.objects.create(code="16261105-A", name="Statistical Techniques", credit_hours=3, enrolled_students=60, requires_lab=False, teacher=teachers["DP"], group=groups["IT-I-A"])
    courses["16261106-A1"] = Course.objects.create(code="16261106-A1", name="Computer Programming Lab (A1)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["AS1"], group=groups["Batch-A1"])
    courses["16261106-A2"] = Course.objects.create(code="16261106-A2", name="Computer Programming Lab (A2)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["AS1"], group=groups["Batch-A2"])
    courses["16261107-A1"] = Course.objects.create(code="16261107-A1", name="IT Workshop (A1)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["VS"], group=groups["Batch-A1"])
    courses["16261107-A2"] = Course.objects.create(code="16261107-A2", name="IT Workshop (A2)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["VS"], group=groups["Batch-A2"])
    courses["16261108-A"] = Course.objects.create(code="16261108-A", name="Semester Proficiency", credit_hours=2, enrolled_students=60, requires_lab=False, teacher=teachers["TS"], group=groups["IT-I-A"])
    courses["16261109-A1"] = Course.objects.create(code="16261109-A1", name="Micro Project-I (A1)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["AS"], group=groups["Batch-A1"])
    courses["16261109-A2"] = Course.objects.create(code="16261109-A2", name="Micro Project-I (A2)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["GS"], group=groups["Batch-A2"])
    courses["16261110-A"] = Course.objects.create(code="16261110-A", name="Language Lab", credit_hours=2, enrolled_students=60, requires_lab=True, teacher=teachers["SK"], group=groups["IT-I-A"])
    courses["MENTOR-A"] = Course.objects.create(code="MENTOR-A", name="Mentor Mentee Meeting", credit_hours=1, enrolled_students=60, requires_lab=False, teacher=teachers["VS"], group=groups["IT-I-A"])

    # Section B Courses
    courses["16261101-B"] = Course.objects.create(code="16261101-B", name="Introduction to Information Technology", credit_hours=4, enrolled_students=60, requires_lab=False, teacher=teachers["VS"], group=groups["IT-I-B"])
    courses["16261102-B"] = Course.objects.create(code="16261102-B", name="Computer Programming", credit_hours=2, enrolled_students=60, requires_lab=False, teacher=teachers["AS1"], group=groups["IT-I-B"])
    courses["16261103-B"] = Course.objects.create(code="16261103-B", name="Digital Logic Design", credit_hours=3, enrolled_students=60, requires_lab=False, teacher=teachers["RKS"], group=groups["IT-I-B"])
    courses["16261104-B"] = Course.objects.create(code="16261104-B", name="Discrete Structures", credit_hours=3, enrolled_students=60, requires_lab=False, teacher=teachers["VR"], group=groups["IT-I-B"])
    courses["16261105-B"] = Course.objects.create(code="16261105-B", name="Statistical Techniques", credit_hours=3, enrolled_students=60, requires_lab=False, teacher=teachers["JM"], group=groups["IT-I-B"])
    courses["16261106-B1"] = Course.objects.create(code="16261106-B1", name="Computer Programming Lab (B1)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["AS1"], group=groups["Batch-B1"])
    courses["16261106-B2"] = Course.objects.create(code="16261106-B2", name="Computer Programming Lab (B2)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["AS1"], group=groups["Batch-B2"])
    courses["16261107-B1"] = Course.objects.create(code="16261107-B1", name="IT Workshop (B1)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["VS"], group=groups["Batch-B1"])
    courses["16261107-B2"] = Course.objects.create(code="16261107-B2", name="IT Workshop (B2)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["VS"], group=groups["Batch-B2"])
    courses["16261108-B"] = Course.objects.create(code="16261108-B", name="Semester Proficiency", credit_hours=2, enrolled_students=60, requires_lab=False, teacher=teachers["TS"], group=groups["IT-I-B"])
    courses["16261109-B1"] = Course.objects.create(code="16261109-B1", name="Micro Project-I (B1)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["AS"], group=groups["Batch-B1"])
    courses["16261109-B2"] = Course.objects.create(code="16261109-B2", name="Micro Project-I (B2)", credit_hours=2, enrolled_students=30, requires_lab=True, teacher=teachers["TJ"], group=groups["Batch-B2"])
    courses["16261110-B"] = Course.objects.create(code="16261110-B", name="Language Lab", credit_hours=2, enrolled_students=60, requires_lab=True, teacher=teachers["SK"], group=groups["IT-I-B"])
    courses["MENTOR-B"] = Course.objects.create(code="MENTOR-B", name="Mentor Mentee Meeting", credit_hours=1, enrolled_students=60, requires_lab=False, teacher=teachers["RKS"], group=groups["IT-I-B"])

    # 6. Exact 62 Scheduled Classes from the MITS Timetable PDF
    pdf_sessions = [
        # SECTION A (Theory in SH-5, Labs in DS Lab, CL Lab, PL Lab, NRGF as written in PDF)
        ("16261103-A", "SH-5", "RKS", "MON", "11:00-12:00"),
        ("16261101-A", "SH-5", "VS",  "MON", "01:00-02:00"),
        ("16261106-A1", "DS Lab", "AS1", "MON", "02:00-03:00"),
        ("16261109-A2", "CL Lab", "GS",  "MON", "02:00-03:00"),
        ("16261106-A1", "DS Lab", "AS1", "MON", "03:00-04:00"),
        ("16261109-A2", "CL Lab", "GS",  "MON", "03:00-04:00"),
        ("16261102-A", "SH-5", "AS1", "MON", "04:00-05:00"),
        ("MENTOR-A",   None,   "VS",  "MON", "05:00-06:00"),

        ("16261104-A", "SH-5", "VR",  "TUE", "02:00-03:00"),
        ("16261105-A", "SH-5", "DP",  "TUE", "03:00-04:00"),

        ("16261107-A2", "DS Lab", "VS",  "WED", "10:00-11:00"),
        ("16261109-A1", "PL Lab", "AS",  "WED", "10:00-11:00"),
        ("16261107-A2", "DS Lab", "VS",  "WED", "11:00-12:00"),
        ("16261109-A1", "PL Lab", "AS",  "WED", "11:00-12:00"),
        ("16261101-A", "SH-5", "VS",  "WED", "01:00-02:00"),
        ("16261103-A", "SH-5", "RKS", "WED", "02:00-03:00"),
        ("16261104-A", "SH-5", "VR",  "WED", "03:00-04:00"),
        ("16261106-A2", "DS Lab", "AS1", "WED", "04:00-05:00"),
        ("16261107-A1", "CL Lab", "VS",  "WED", "04:00-05:00"),
        ("16261106-A2", "DS Lab", "AS1", "WED", "05:00-06:00"),
        ("16261107-A1", "CL Lab", "VS",  "WED", "05:00-06:00"),

        ("16261110-A", "NRGF", "SK",  "THU", "10:00-11:00"),
        ("16261110-A", "NRGF", "SK",  "THU", "11:00-12:00"),
        ("16261101-A", "SH-5", "VS",  "THU", "01:00-02:00"),
        ("16261104-A", "SH-5", "VR",  "THU", "02:00-03:00"),
        ("16261105-A", "SH-5", "DP",  "THU", "03:00-04:00"),
        ("16261102-A", "SH-5", "AS1", "THU", "04:00-05:00"),

        ("16261103-A", "NRGF", "RKS", "FRI", "11:00-12:00"),
        ("16261105-A", "SH-5", "DP",  "FRI", "01:00-02:00"),
        ("16261108-A", "SH-5", "TS",  "FRI", "02:00-03:00"),
        ("16261108-A", "SH-5", "TS",  "FRI", "03:00-04:00"),

        # SECTION B (Theory in SH-5 / NRGF, Labs in DS Lab, CL Lab, PL Lab)
        ("16261109-B1", "DS Lab", "AS",  "MON", "10:00-11:00"),
        ("16261107-B2", "PL Lab", "VS",  "MON", "10:00-11:00"),
        ("16261109-B1", "DS Lab", "AS",  "MON", "11:00-12:00"),
        ("16261107-B2", "PL Lab", "VS",  "MON", "11:00-12:00"),
        ("16261103-B",  "NRGF",   "RKS", "MON", "01:00-02:00"),
        ("MENTOR-B",    None,     "RKS", "MON", "02:00-03:00"),

        ("16261102-B",  "SH-5",   "AS1", "TUE", "10:00-11:00"),
        ("16261101-B",  "SH-5",   "VS",  "TUE", "11:00-12:00"),
        ("16261103-B",  "SH-5",   "RKS", "TUE", "01:00-02:00"),
        ("16261107-B1", "CL Lab", "VS",  "TUE", "02:00-03:00"),
        ("16261106-B2", "DS Lab", "AS1", "TUE", "02:00-03:00"),
        ("16261107-B1", "CL Lab", "VS",  "TUE", "03:00-04:00"),
        ("16261106-B2", "DS Lab", "AS1", "TUE", "03:00-04:00"),
        ("16261105-B",  "SH-5",   "JM",  "TUE", "04:00-05:00"),
        ("16261104-B",  "SH-5",   "VR",  "TUE", "05:00-06:00"),

        ("16261105-B",  "SH-5",   "JM",  "WED", "11:00-12:00"),
        ("16261102-B",  "NRGF",   "AS1", "WED", "01:00-02:00"),
        ("16261108-B",  "NRGF",   "TS",  "WED", "02:00-03:00"),
        ("16261108-B",  "NRGF",   "TS",  "WED", "03:00-04:00"),

        ("16261101-B",  "SH-5",   "VS",  "THU", "10:00-11:00"),
        ("16261104-B",  "SH-5",   "VR",  "THU", "11:00-12:00"),
        ("16261103-B",  "NRGF",   "RKS", "THU", "01:00-02:00"),

        ("16261101-B",  "SH-5",   "VS",  "FRI", "10:00-11:00"),
        ("16261104-B",  "SH-5",   "VR",  "FRI", "11:00-12:00"),
        ("16261105-B",  "NRGF",   "JM",  "FRI", "01:00-02:00"),
        ("16261110-B",  "NRGF",   "SK",  "FRI", "02:00-03:00"),
        ("16261110-B",  "NRGF",   "SK",  "FRI", "03:00-04:00"),
        ("16261109-B2", "PL Lab", "TJ",  "FRI", "04:00-05:00"),
        ("16261106-B1", "DS Lab", "AS1", "FRI", "04:00-05:00"),
        ("16261109-B2", "PL Lab", "TJ",  "FRI", "05:00-06:00"),
        ("16261106-B1", "DS Lab", "AS1", "FRI", "05:00-06:00"),
    ]

    schedule_records = []
    for c_code, r_num, t_abbr, day, slot in pdf_sessions:
        schedule_records.append(Schedule(
            course=courses[c_code],
            room=rooms[r_num] if r_num else None,
            teacher=teachers[t_abbr],
            day=day,
            time_slot=slot,
            status="SCHEDULED",
        ))
    Schedule.objects.bulk_create(schedule_records)

    return {
        "rooms": rooms,
        "teachers": teachers,
        "groups": groups,
        "courses": list(courses.values()),
        "total_courses": len(courses),
        "sessions_scheduled": len(schedule_records),
    }

