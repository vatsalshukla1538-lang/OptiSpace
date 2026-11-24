"""
views.py - REST API endpoints for MITS Gwalior Classroom Scheduling System.
Provides ViewSets, schedule generation, CSV/Excel/PDF exports, CSV imports, and dashboard analytics.
"""

from collections import Counter
import csv
import io
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .models import Room, Teacher, TeacherAvailability, StudentGroup, Course, Schedule, TIME_SLOTS, DAYS_OF_WEEK
from .serializers import (
    RoomSerializer,
    TeacherSerializer,
    TeacherAvailabilitySerializer,
    StudentGroupSerializer,
    CourseSerializer,
    ScheduleSerializer,
    UserSerializer,
    RegisterSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from .solver import generate_and_save_schedule, compute_long_gaps


class IsAdminOrReadOnly(permissions.BasePermission):
    """Authenticated users can read; only staff (Admin) can write."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff


class IsAdmin(permissions.BasePermission):
    """Only staff users (Admin role)."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


VALID_DAYS = [d[0] for d in DAYS_OF_WEEK]

LATEST_PERFORMANCE_METRICS = {
    "generation_time_seconds": None,
    "recursion_calls": None,
    "backtracks": None,
    "forward_checks_failed": None,
    "valid": None,
    "total_scheduled_sessions": None,
    "total_required_sessions": None,
    "algorithm": "CSP Backtracking with Forward Checking & MRV Heuristic",
    "is_constrained_warning": False,
    "constraint_warning_message": "",
    "timestamp": None,
}


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all().order_by('room_number')
    serializer_class = RoomSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['room_type', 'is_available']
    search_fields = ['room_number']
    ordering_fields = ['capacity', 'room_number']


class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all().order_by('name')
    serializer_class = TeacherSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['department']
    search_fields = ['name', 'department']
    ordering_fields = ['name']


class TeacherAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = TeacherAvailability.objects.select_related('teacher').all().order_by('day', 'time_slot')
    serializer_class = TeacherAvailabilitySerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['teacher', 'day']
    search_fields = ['time_slot']


class StudentGroupViewSet(viewsets.ModelViewSet):
    queryset = StudentGroup.objects.all().order_by('code')
    serializer_class = StudentGroupSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['name', 'code']
    ordering_fields = ['code', 'name']


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.select_related('teacher', 'group').all().order_by('code')
    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['difficulty', 'requires_lab', 'group']
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'enrolled_students', 'credit_hours']


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.select_related('course', 'teacher', 'room', 'course__group').all().order_by('day', 'time_slot')
    serializer_class = ScheduleSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['day', 'teacher', 'room', 'course']
    ordering_fields = ['day', 'time_slot']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Returns current user details and role (ADMIN or VIEWER), including batch."""
    return Response(UserSerializer(request.user).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    Public registration endpoint for students/viewers.
    Asks for username, password, and student batch/section.
    Returns JWT tokens and user payload for immediate login.
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    user = serializer.save()
    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
        'message': 'Registration successful!'
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdmin])
def generate_schedule(request):
    """
    Triggers automated CSP timetable generation.
    Returns 201 on success, 400 on bad/incomplete input, 409 if no schedule fits constraints,
    or 500 on validation failure. The existing timetable is preserved if generation fails.
    """
    result = generate_and_save_schedule()
    if not result['success']:
        status_code = status.HTTP_409_CONFLICT
        error_msg = result.get("error", "")
        if "Missing" in error_msg or "Incomplete" in error_msg or "invalid" in error_msg or "exceeded" in error_msg:
            status_code = status.HTTP_400_BAD_REQUEST
        elif "conflicts" in result:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return Response({
            "error": result.get("error"),
            "conflicts": result.get("conflicts", []),
        }, status=status_code)

    metrics = result.get("metrics", {})
    from datetime import datetime
    LATEST_PERFORMANCE_METRICS.update({
        "generation_time_seconds": metrics.get("generation_time_seconds", 0.0),
        "recursion_calls": metrics.get("recursion_calls", 0),
        "backtracks": metrics.get("backtracks", 0),
        "forward_checks_failed": metrics.get("forward_checks_failed", 0),
        "valid": result.get("valid", True),
        "total_scheduled_sessions": result.get("total_scheduled_sessions", 0),
        "total_required_sessions": result.get("total_required_sessions", 0),
        "algorithm": metrics.get("algorithm", "CSP Backtracking with Forward Checking & MRV Heuristic"),
        "is_constrained_warning": metrics.get("is_constrained_warning", False),
        "constraint_warning_message": metrics.get("constraint_warning_message", ""),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    new_schedules = Schedule.objects.select_related('course', 'teacher', 'room', 'course__group').all()
    serializer = ScheduleSerializer(new_schedules, many=True)
    return Response({
        "message": result["message"],
        "conflicts_detected": result["conflicts_detected"],
        "valid": result["valid"],
        "total_required_sessions": result["total_required_sessions"],
        "total_scheduled_sessions": result["total_scheduled_sessions"],
        "remaining_sessions": result["remaining_sessions"],
        "remaining_gaps": result.get("remaining_gaps", []),
        "remaining_gaps_count": result.get("remaining_gaps_count", 0),
        "metrics": LATEST_PERFORMANCE_METRICS,
        "schedule": serializer.data,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdmin])
def clear_schedule(request):
    """Clears all scheduled classes."""
    Schedule.objects.all().delete()
    return Response({"message": "Schedule cleared."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdmin])
def validate_manual(request):
    """Validates a proposed class placement before saving."""
    ser = ScheduleSerializer(data=request.data)
    if ser.is_valid():
        return Response({"valid": True, "message": "Slot is valid and conflict-free."})
    return Response({"valid": False, "errors": ser.errors}, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# EXPORTS: CSV, Real Excel (.xlsx), and PDF with Multi-Combination Filtering
# Both Admins and Viewers have permission to export.
# Supports exporting for a particular batch, teacher, room, semester, day, type,
# or all batches with dedicated sheets/sections.
# =============================================================================

def filter_schedules_from_request(request):
    """
    Filters Schedule queryset based on query parameters:
    - group / batch: ID or code/name (e.g., 'IT-I-A', 'IT-I-A1')
    - semester: Roman numeral e.g. 'I', 'III', 'V', 'VII'
    - teacher / faculty: ID or name substring
    - room: ID or room_number substring
    - day: MON, TUE, WED, THU, FRI
    - type / kind: LECTURE or LAB
    - search / q: keyword matching course code, name, teacher, room, or group
    """
    qs = Schedule.objects.select_related('course', 'teacher', 'room', 'course__group').order_by('day', 'time_slot', 'room__room_number')

    group_param = request.GET.get('group') or request.GET.get('batch')
    if not group_param and request.user and request.user.is_authenticated and not request.user.is_staff:
        try:
            if hasattr(request.user, 'profile') and request.user.profile.batch:
                group_param = request.user.profile.batch
        except Exception:
            pass

    if group_param and group_param.upper() != 'ALL':
        up = group_param.upper()
        if group_param.isdigit():
            qs = qs.filter(course__group_id=int(group_param))
        elif up in ('SEC-A', 'A', 'SECTION-A', 'SECTION A', 'IT-I-A'):
            qs = qs.filter(
                Q(course__group__code__icontains='-A') |
                Q(course__group__code__endswith='A') |
                Q(course__group__name__icontains='Sec A') |
                Q(course__code__icontains='-A')
            ).exclude(course__group__code__icontains='-B').exclude(course__code__icontains='-B')
        elif up in ('SEC-B', 'B', 'SECTION-B', 'SECTION B', 'IT-I-B'):
            qs = qs.filter(
                Q(course__group__code__icontains='-B') |
                Q(course__group__code__endswith='B') |
                Q(course__group__name__icontains='Sec B') |
                Q(course__code__icontains='-B')
            ).exclude(course__group__code__icontains='-A').exclude(course__code__icontains='-A')
        elif up in ('BATCH-A1', 'A1'):
            qs = qs.filter(
                Q(course__group__code__iexact='Batch-A1') |
                Q(course__group__code__iexact='IT-I-A') |
                Q(course__code__startswith='16261110-A') |
                Q(course__code__startswith='MENTOR-A') |
                (Q(course__code__icontains='-A') & Q(course__requires_lab=False))
            ).exclude(course__group__code__icontains='A2')
        elif up in ('BATCH-A2', 'A2'):
            qs = qs.filter(
                Q(course__group__code__iexact='Batch-A2') |
                Q(course__group__code__iexact='IT-I-A') |
                Q(course__code__startswith='16261110-A') |
                Q(course__code__startswith='MENTOR-A') |
                (Q(course__code__icontains='-A') & Q(course__requires_lab=False))
            ).exclude(course__group__code__icontains='A1')
        elif up in ('BATCH-B1', 'B1'):
            qs = qs.filter(
                Q(course__group__code__iexact='Batch-B1') |
                Q(course__group__code__iexact='IT-I-B') |
                Q(course__code__startswith='16261110-B') |
                Q(course__code__startswith='MENTOR-B') |
                (Q(course__code__icontains='-B') & Q(course__requires_lab=False))
            ).exclude(course__group__code__icontains='B2')
        elif up in ('BATCH-B2', 'B2'):
            qs = qs.filter(
                Q(course__group__code__iexact='Batch-B2') |
                Q(course__group__code__iexact='IT-I-B') |
                Q(course__code__startswith='16261110-B') |
                Q(course__code__startswith='MENTOR-B') |
                (Q(course__code__icontains='-B') & Q(course__requires_lab=False))
            ).exclude(course__group__code__icontains='B1')
        else:
            qs = qs.filter(
                Q(course__group__code__iexact=group_param) |
                Q(course__group__code__icontains=group_param) |
                Q(course__group__name__icontains=group_param)
            )

    semester_param = request.GET.get('semester')
    if semester_param:
        qs = qs.filter(
            Q(course__group__code__icontains=f"-{semester_param}-") |
            Q(course__group__code__endswith=f"-{semester_param}") |
            Q(course__group__name__icontains=f"Sem-{semester_param}") |
            Q(course__group__name__icontains=f"Semester-{semester_param}") |
            Q(course__group__name__icontains=f"Sem {semester_param}") |
            Q(course__group__name__icontains=f"Semester {semester_param}")
        )

    teacher_param = request.GET.get('teacher') or request.GET.get('faculty')
    if teacher_param:
        if teacher_param.isdigit():
            qs = qs.filter(teacher_id=int(teacher_param))
        else:
            qs = qs.filter(teacher__name__icontains=teacher_param)

    room_param = request.GET.get('room')
    if room_param:
        if room_param.isdigit():
            qs = qs.filter(room_id=int(room_param))
        else:
            qs = qs.filter(room__room_number__icontains=room_param)

    day_param = request.GET.get('day')
    if day_param:
        qs = qs.filter(day=day_param.upper())

    type_param = request.GET.get('type') or request.GET.get('kind')
    if type_param:
        if type_param.upper() == 'LAB':
            qs = qs.filter(course__requires_lab=True)
        elif type_param.upper() in ('LECTURE', 'THEORY'):
            qs = qs.filter(course__requires_lab=False)

    search_param = request.GET.get('search') or request.GET.get('q')
    if search_param:
        search_param = search_param.strip()
        qs = qs.filter(
            Q(course__code__icontains=search_param) |
            Q(course__name__icontains=search_param) |
            Q(teacher__name__icontains=search_param) |
            Q(room__room_number__icontains=search_param) |
            Q(course__group__code__icontains=search_param)
        )

    return qs


def get_export_metadata(request):
    """
    Returns (title_description, filename_suffix) based on active query filters.
    """
    parts = []
    file_parts = []

    group_param = request.GET.get('group') or request.GET.get('batch')
    if group_param and group_param.upper() != 'ALL':
        if group_param.upper() in ('SEC-A', 'A', 'SECTION-A', 'SECTION A'):
            parts.append("Section A")
            file_parts.append("Section_A")
        elif group_param.upper() in ('SEC-B', 'B', 'SECTION-B', 'SECTION B'):
            parts.append("Section B")
            file_parts.append("Section_B")
        else:
            parts.append(f"Batch: {group_param}")
            clean_g = "".join(c for c in group_param if c.isalnum() or c in "-_")
            file_parts.append(f"Batch_{clean_g}")

    semester_param = request.GET.get('semester')
    if semester_param:
        parts.append(f"Semester {semester_param}")
        file_parts.append(f"Sem_{semester_param}")

    teacher_param = request.GET.get('teacher') or request.GET.get('faculty')
    if teacher_param:
        parts.append(f"Faculty: {teacher_param}")
        clean_t = "".join(c for c in teacher_param if c.isalnum() or c in "-_")
        file_parts.append(f"Faculty_{clean_t}")

    room_param = request.GET.get('room')
    if room_param:
        parts.append(f"Room: {room_param}")
        clean_r = "".join(c for c in room_param if c.isalnum() or c in "-_")
        file_parts.append(f"Room_{clean_r}")

    day_param = request.GET.get('day')
    if day_param:
        parts.append(f"Day: {day_param.upper()}")
        file_parts.append(f"Day_{day_param.upper()}")

    type_param = request.GET.get('type') or request.GET.get('kind')
    if type_param:
        parts.append(f"Type: {type_param.upper()}")
        file_parts.append(type_param.upper())

    if parts:
        filter_str = " · ".join(parts)
        title_suffix = f"Filtered by: {filter_str}"
        filename_base = f"MITS_Timetable_{'_'.join(file_parts)}"
    else:
        title_suffix = "Complete Master Timetable"
        filename_base = "MITS_Timetable_Master"

    return title_suffix, filename_base


def populate_excel_sheet(ws, schedules, title, subtitle):
    """Formats and writes a timetable sheet into an openpyxl worksheet."""
    ws.merge_cells('A1:I1')
    ws['A1'] = title
    ws['A1'].font = Font(name='Calibri', size=15, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 32

    ws.merge_cells('A2:I2')
    ws['A2'] = subtitle
    ws['A2'].font = Font(name='Calibri', size=10, italic=True, color='64748B')
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[2].height = 20

    headers = ['Course Code', 'Course Name', 'Student Group', 'Faculty', 'Room', 'Room Type', 'Day', 'Time Slot', 'Status']
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='334155', end_color='334155', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center')
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for col_num, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
    ws.row_dimensions[3].height = 24

    for row_idx, s in enumerate(schedules, 4):
        group_code = s.course.group.code if s.course and s.course.group else 'General'
        room_num = s.room.room_number if s.room else 'No Room'
        room_type = s.room.room_type if s.room else '-'
        teacher_name = s.teacher.name if s.teacher else 'Faculty TBD'
        row_values = [
            s.course.code if s.course else '-',
            s.course.name if s.course else '-',
            group_code,
            teacher_name,
            room_num,
            room_type,
            s.day,
            s.time_slot,
            s.status,
        ]
        row_fill = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid') if row_idx % 2 == 0 else PatternFill(fill_type=None)
        for col_num, val in enumerate(row_values, 1):
            cell = ws.cell(row=row_idx, column=col_num, value=val)
            cell.font = Font(name='Calibri', size=10)
            if row_fill.fill_type:
                cell.fill = row_fill
            cell.border = thin_border
            if col_num in (1, 3, 5, 6, 7, 8, 9):
                cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[row_idx].height = 19

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_csv(request):
    """Exports timetable as standard CSV with optional combination filtering."""
    schedules = filter_schedules_from_request(request)
    title_suffix, filename_base = get_export_metadata(request)

    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
    writer = csv.writer(resp)
    writer.writerow(['Course Code', 'Course Name', 'Student Group', 'Faculty', 'Room', 'Room Type', 'Day', 'Time Slot', 'Status'])
    for s in schedules:
        group_code = s.course.group.code if s.course and s.course.group else 'General'
        room_num = s.room.room_number if s.room else 'No Room'
        room_type = s.room.room_type if s.room else '-'
        teacher_name = s.teacher.name if s.teacher else 'Faculty TBD'
        writer.writerow([
            s.course.code if s.course else '-',
            s.course.name if s.course else '-',
            group_code,
            teacher_name,
            room_num,
            room_type,
            s.day,
            s.time_slot,
            s.status,
        ])
    return resp


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_excel(request):
    """
    Exports timetable as formatted Excel (.xlsx) file using openpyxl.
    Supports filtering by batch, teacher, room, semester, day, type.
    If split_batches=true or split_batches=1, includes dedicated tabs per student batch.
    """
    schedules = list(filter_schedules_from_request(request))
    title_suffix, filename_base = get_export_metadata(request)

    wb = openpyxl.Workbook()
    ws_main = wb.active
    ws_main.title = "Timetable"

    populate_excel_sheet(
        ws_main,
        schedules,
        title="MITS Gwalior - Classroom Timetable",
        subtitle=f"{title_suffix} · {len(schedules)} Scheduled Classes · User: {request.user.username}"
    )

    # Optional multi-batch split: create dedicated tabs per batch
    split_batches = request.GET.get('split_batches', '').lower() in ('1', 'true', 'yes')
    if split_batches:
        # Group by student group
        group_map = {}
        for s in schedules:
            if s.course and s.course.group:
                group_map.setdefault(s.course.group, []).append(s)

        for group, group_schedules in sorted(group_map.items(), key=lambda x: x[0].code):
            safe_sheet_name = "".join(c for c in group.code if c.isalnum() or c in "-_ ")[:30]
            ws_group = wb.create_sheet(title=safe_sheet_name)
            populate_excel_sheet(
                ws_group,
                group_schedules,
                title=f"MITS Gwalior - Batch: {group.name} ({group.code})",
                subtitle=f"{len(group_schedules)} Classes · Monday to Friday"
            )

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_pdf(request):
    """
    Exports timetable as an authentic MITS Gwalior weekly grid PDF matching the official format:
    - Landscape weekly grid with Days on rows and Time Slots across columns + LUNCH column.
    - Section A & Section B grids.
    - Official Department of IT Header & Room No. designation.
    - NRGF classroom and laboratory locations.
    - Pure 'Mentor Mentee Meeting' formatting for mentor sessions.
    - Complete official MITS faculty abbreviation legend and course code list.
    - Time Table Coordinator and Dean signature blocks.
    - Supports combination filtering for particular batch, faculty, room, semester, or day.
    """
    schedules = list(filter_schedules_from_request(request))
    title_suffix, filename_base = get_export_metadata(request)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=18,
        rightMargin=18,
        topMargin=10,
        bottomMargin=10,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=1)
    subtitle_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=1)
    sec_header_style = ParagraphStyle('SecH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10, alignment=1)
    hdr_cell_style = ParagraphStyle('HC', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=1)
    cell_style = ParagraphStyle('CC', parent=styles['Normal'], fontName='Helvetica', fontSize=5.5, leading=6.8, alignment=1)
    mentor_cell_style = ParagraphStyle('MC', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=6, leading=7.5, alignment=1, textColor=colors.HexColor('#78350f'))

    # Teacher abbrev map from PDF legend
    t_map = {}
    from .it_data import PDF_FACULTY_LEGEND
    for abbr, name in PDF_FACULTY_LEGEND:
        t_map[name] = abbr
        clean = name.replace('Dr. ', '').replace('Prof. ', '').replace('Mrs. ', '').strip()
        t_map[clean] = abbr
        t_map[abbr] = abbr

    elements = []

    # 1. Header (MITS School of IT)
    header_table = Table([
        [Paragraph('<b>School of Information Technology</b>', title_style), Paragraph('<i>Tentative</i>', ParagraphStyle('Ten', fontName='Helvetica-Oblique', fontSize=8, alignment=2))],
        [Paragraph(f'<b>Time-Table, B.Tech, IT {title_suffix if "Semester" in title_suffix else "Semester-I (Session: July-Dec 2026)"}</b>', subtitle_style), Paragraph('<b>Room No.: SH-5/J013</b>', ParagraphStyle('Rm', fontName='Helvetica-Bold', fontSize=8.5, alignment=2))]
    ], colWidths=[630, 126])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3))

    days = ['MON', 'TUE', 'WED', 'THU', 'FRI']
    time_slots = ['10:00-11:00', '11:00-12:00', '12:00-01:00', '01:00-02:00', '02:00-03:00', '03:00-04:00', '04:00-05:00', '05:00-06:00']
    col_widths = [40, 88, 88, 44, 88, 102, 102, 102, 102]

    def build_grid_table(label, sec_schedules):
        headers = ['DAY', '10:00 - 11:00', '11:00 - 12:00', '12:00 - 01:00', '01:00 - 02:00', '02:00 - 03:00', '03:00 - 04:00', '04:00 - 05:00', '05:00 - 06:00']
        rows = [
            [Paragraph(f'<b>SECTION - {label}</b>', sec_header_style)] + [''] * 8,
            [Paragraph(f'<b>{h}</b>', hdr_cell_style) for h in headers]
        ]
        for d in days:
            row = [Paragraph(f'<b>{d}</b>', hdr_cell_style)]
            for sl in time_slots:
                if sl == '12:00-01:00':
                    row.append(Paragraph('<b>LUNCH</b>', hdr_cell_style))
                    continue
                matching = [s for s in sec_schedules if s.day == d and s.time_slot == sl]
                if not matching:
                    row.append(Paragraph('', cell_style))
                    continue

                has_mentor = any('mentor' in (s.course.name if s.course else '').lower() or (s.course.code if s.course else '').startswith('MENTOR') for s in matching)
                if has_mentor:
                    row.append(Paragraph('<b>Mentor Mentee<br/>Meeting</b>', mentor_cell_style))
                    continue

                lines = []
                for s in matching:
                    raw_code = s.course.code if s.course else ''
                    c_code = raw_code.split('-')[0]
                    t_name = s.teacher.name if s.teacher else ''
                    t_abbr = t_map.get(t_name, t_name)
                    rm = s.room.room_number if s.room else ''
                    is_lab = s.course.requires_lab if s.course else False
                    grp = s.course.group.code if s.course and s.course.group else ''

                    b_str = ''
                    if 'A1' in raw_code or 'A1' in grp: b_str = 'Batch-A1'
                    elif 'A2' in raw_code or 'A2' in grp: b_str = 'Batch-A2'
                    elif 'B1' in raw_code or 'B1' in grp: b_str = 'Batch-B1'
                    elif 'B2' in raw_code or 'B2' in grp: b_str = 'Batch-B2'

                    if raw_code in ('16261110-A', '16261110-B'):
                        sec_b_tag = 'Batch-A1+A2' if '-A' in raw_code else 'Batch-B1+B2'
                        lines.append(f'{c_code} {sec_b_tag}<br/>[Language Lab] {t_abbr}<br/><b>NRGF</b>')
                    elif is_lab:
                        lines.append(f'{c_code} {b_str} {rm} {t_abbr}')
                    else:
                        if rm == 'NRGF':
                            lines.append(f'{c_code} {t_abbr}<br/><b>NRGF</b>')
                        else:
                            lines.append(f'{c_code} {t_abbr}')
                row.append(Paragraph('<br/>'.join(lines), cell_style))
            rows.append(row)

        t = Table(rows, colWidths=col_widths, rowHeights=[13, 13] + [22]*5)
        t.setStyle(TableStyle([
            ('SPAN', (0,0), (-1,0)),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f8fafc')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#334155')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
        ]))
        return t

    # Determine whether to render Section A, Section B, or both
    batch_param = (request.GET.get('batch') or request.GET.get('group') or '').upper()
    sec_a_schedules = [s for s in schedules if '-A' in (s.course.code if s.course else '') or 'A1' in (s.course.code if s.course else '') or 'A2' in (s.course.code if s.course else '') or '-A' in (s.course.group.code if s.course and s.course.group else '') or (s.course.group.code if s.course and s.course.group else '').endswith('A')]
    sec_b_schedules = [s for s in schedules if '-B' in (s.course.code if s.course else '') or 'B1' in (s.course.code if s.course else '') or 'B2' in (s.course.code if s.course else '') or '-B' in (s.course.group.code if s.course and s.course.group else '') or (s.course.group.code if s.course and s.course.group else '').endswith('B')]

    if batch_param in ('SEC-A', 'A', 'IT-I-A', 'SECTION-A', 'SECTION A', 'BATCH-A1', 'BATCH-A2'):
        elements.append(build_grid_table('A', sec_a_schedules if sec_a_schedules else schedules))
        elements.append(Spacer(1, 8))
    elif batch_param in ('SEC-B', 'B', 'IT-I-B', 'SECTION-B', 'SECTION B', 'BATCH-B1', 'BATCH-B2'):
        elements.append(build_grid_table('B', sec_b_schedules if sec_b_schedules else schedules))
        elements.append(Spacer(1, 8))
    else:
        # Both sections (or generic filter)
        if sec_a_schedules or sec_b_schedules:
            if sec_a_schedules:
                elements.append(build_grid_table('A', sec_a_schedules))
                elements.append(Spacer(1, 3))
            if sec_b_schedules:
                elements.append(build_grid_table('B', sec_b_schedules))
                elements.append(Spacer(1, 3))
        else:
            elements.append(build_grid_table('TIMETABLE', schedules))
            elements.append(Spacer(1, 4))

    # Faculty Legend
    fac_p = Paragraph(
        '<b>AT:</b> Dr. Akhilesh Tiwari &nbsp;&nbsp;|&nbsp;&nbsp; <b>SS:</b> Dr. Sanjiv Sharma &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<b>PJ:</b> Dr. Punit Kumar Johari &nbsp;&nbsp;|&nbsp;&nbsp; <b>AS:</b> Dr. Abhilash Sonker &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<b>VS:</b> Vikas Sejwar<br/>'
        '<b>RKS:</b> Dr. Rajeev K. Singh &nbsp;&nbsp;|&nbsp;&nbsp; <b>NB:</b> Neha Bhardwaj &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<b>VR:</b> Dr. Vikram Rajpoot &nbsp;&nbsp;|&nbsp;&nbsp; <b>GS:</b> Dr. Gulshan Soni &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<b>AS1:</b> Aradhana Saxena<br/>'
        '<b>SS1:</b> Shubham Sharma &nbsp;&nbsp;|&nbsp;&nbsp; <b>KD:</b> Kumud Dixit &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<b>SG:</b> Surbhi Gupta &nbsp;&nbsp;|&nbsp;&nbsp; <b>TS:</b> Mrs. Tanuja Sharma &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<b>SK:</b> Dr. Sanjiv Khanna &nbsp;&nbsp;|&nbsp;&nbsp; <b>JM:</b> Dr. J.K. Muthele &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<b>DP:</b> Divya Pundhir &nbsp;&nbsp;|&nbsp;&nbsp; <b>TJ:</b> Tarun Jadaun',
        ParagraphStyle('FT', fontName='Helvetica', fontSize=5.5, leading=7, alignment=0)
    )
    elements.append(fac_p)
    elements.append(Spacer(1, 3))

    # Course Legend Table
    courses_data = [
        [Paragraph('<b>Course Code</b>', hdr_cell_style), Paragraph('<b>Course Name</b>', hdr_cell_style),
         Paragraph('<b>Course Code</b>', hdr_cell_style), Paragraph('<b>Course Name</b>', hdr_cell_style),
         Paragraph('<b>Course Code</b>', hdr_cell_style), Paragraph('<b>Course Name</b>', hdr_cell_style)],
        [Paragraph('16261101', cell_style), Paragraph('Introduction to Information Technology', cell_style),
         Paragraph('16261105', cell_style), Paragraph('Statistical Techniques', cell_style),
         Paragraph('16261109', cell_style), Paragraph('Micro Project-I', cell_style)],
        [Paragraph('16261102', cell_style), Paragraph('Computer Programming', cell_style),
         Paragraph('16261106', cell_style), Paragraph('Computer Programming Lab', cell_style),
         Paragraph('16261110', cell_style), Paragraph('Language Lab', cell_style)],
        [Paragraph('16261103', cell_style), Paragraph('Digital Logic Design', cell_style),
         Paragraph('16261107', cell_style), Paragraph('IT Workshop', cell_style),
         Paragraph('16261111', cell_style), Paragraph('Mandatory Workshop', cell_style)],
        [Paragraph('16261104', cell_style), Paragraph('Discrete Structures', cell_style),
         Paragraph('16261108', cell_style), Paragraph('Semester Proficiency', cell_style),
         Paragraph('', cell_style), Paragraph('', cell_style)],
    ]
    c_table = Table(courses_data, colWidths=[55, 197, 55, 197, 55, 197], rowHeights=[8]*5)
    c_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#94a3b8')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.5),
        ('TOPPADDING', (0,0), (-1,-1), 0.5),
    ]))
    elements.append(c_table)
    elements.append(Spacer(1, 4))

    # Signatures
    sig_table = Table([
        [Paragraph('<b>(Vikas Sejwar)</b><br/>Time Table Coordinator', ParagraphStyle('ST1', fontName='Helvetica', fontSize=6.5, leading=8.5, alignment=0)),
         Paragraph('<b>(Dr. Punit K Johari)</b><br/>Dean, School of IT', ParagraphStyle('ST2', fontName='Helvetica', fontSize=6.5, leading=8.5, alignment=2))]
    ], colWidths=[378, 378])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
    return response


# =============================================================================
# CSV BULK IMPORT & TEMPLATES
# Validates the whole file before saving, in a transaction, so no partial writes occur.
# =============================================================================

CSV_TEMPLATES = {
    'rooms': {
        'filename': 'example_rooms.csv',
        'headers': ['room_number', 'capacity', 'room_type', 'is_available'],
        'sample': [
            ['101', '60', 'LECTURE', 'true'],
            ['102', '40', 'LECTURE', 'true'],
            ['LAB1', '30', 'LAB', 'true'],
        ],
    },
    'teachers': {
        'filename': 'example_faculty.csv',
        'headers': ['name', 'department'],
        'sample': [
            ['Prof. Sharma', 'CSE'],
            ['Dr. Gupta', 'IT'],
            ['Prof. Singh', 'ECE'],
        ],
    },
    'groups': {
        'filename': 'example_student_groups.csv',
        'headers': ['code', 'name'],
        'sample': [
            ['CSE-A', 'B.Tech CSE - Section A'],
            ['IT-A', 'B.Tech IT - Section A'],
        ],
    },
    'courses': {
        'filename': 'example_courses.csv',
        'headers': ['code', 'name', 'credit_hours', 'enrolled_students', 'difficulty', 'requires_lab', 'teacher', 'group'],
        'sample': [
            ['CSE101', 'Intro to Programming', '3', '50', 'MEDIUM', 'false', 'Prof. Sharma', 'CSE-A'],
            ['CSE102', 'Programming Lab', '2', '25', 'EASY', 'true', 'Prof. Sharma', 'CSE-A'],
            ['IT201', 'Database Systems', '3', '35', 'HARD', 'false', 'Dr. Gupta', 'IT-A'],
        ],
    },
    'availability': {
        'filename': 'example_availability.csv',
        'headers': ['teacher', 'day', 'time_slot'],
        'sample': [
            ['Prof. Sharma', 'MON', '09:00-10:00'],
            ['Prof. Sharma', 'MON', '10:00-11:00'],
            ['Dr. Gupta', 'TUE', '10:00-11:00'],
        ],
    },
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_csv_template(request, resource_type):
    """Provides downloadable CSV template with expected columns and example rows."""
    cfg = CSV_TEMPLATES.get(resource_type)
    if not cfg:
        return Response({"error": f"Invalid resource type '{resource_type}'."}, status=status.HTTP_404_NOT_FOUND)

    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="{cfg["filename"]}"'
    writer = csv.writer(resp)
    writer.writerow(cfg['headers'])
    for row in cfg['sample']:
        writer.writerow(row)
    return resp


@api_view(['POST'])
@permission_classes([IsAdmin])
@parser_classes([MultiPartParser, FormParser])
def import_csv(request, resource_type):
    """
    Validates the whole CSV file before committing anything.
    Uses database transaction so failed rows prevent any partial data writes.
    """
    if resource_type not in CSV_TEMPLATES:
        return Response({"error": f"Unsupported resource '{resource_type}'."}, status=status.HTTP_400_BAD_REQUEST)

    upload = request.FILES.get('file')
    if not upload:
        return Response({"error": "No CSV file provided. Please choose a file to upload."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        decoded = upload.read().decode('utf-8-sig')
        reader = list(csv.DictReader(io.StringIO(decoded)))
    except Exception as exc:
        return Response({"error": f"Could not read CSV file: {str(exc)}"}, status=status.HTTP_400_BAD_REQUEST)

    if not reader:
        return Response({"error": "The uploaded CSV file is empty."}, status=status.HTTP_400_BAD_REQUEST)

    errors = []
    records_to_create = []

    if resource_type == 'rooms':
        seen_numbers = set(Room.objects.values_list('room_number', flat=True))
        file_numbers = set()
        for idx, row in enumerate(reader, start=2):
            rn = (row.get('room_number') or '').strip()
            cap = (row.get('capacity') or '').strip()
            rtype = (row.get('room_type') or 'LECTURE').strip().upper()
            avail_str = (row.get('is_available') or 'true').strip().lower()

            if not rn:
                errors.append(f"Row {idx}: room_number is required.")
                continue
            if rn in file_numbers or rn in seen_numbers:
                errors.append(f"Row {idx}: Room '{rn}' already exists or is duplicated in file.")
                continue
            file_numbers.add(rn)

            try:
                cap_int = int(cap)
                if cap_int <= 0:
                    raise ValueError()
            except ValueError:
                errors.append(f"Row {idx}: capacity must be a positive integer (got '{cap}').")
                continue

            if rtype not in ('LECTURE', 'LAB'):
                errors.append(f"Row {idx}: room_type must be 'LECTURE' or 'LAB' (got '{rtype}').")
                continue

            is_avail = avail_str in ('true', '1', 'yes')
            records_to_create.append(Room(room_number=rn, capacity=cap_int, room_type=rtype, is_available=is_avail))

    elif resource_type == 'teachers':
        for idx, row in enumerate(reader, start=2):
            name = (row.get('name') or '').strip()
            dept = (row.get('department') or '').strip()
            if not name:
                errors.append(f"Row {idx}: Faculty name is required.")
                continue
            if not dept:
                errors.append(f"Row {idx}: Department is required.")
                continue
            records_to_create.append(Teacher(name=name, department=dept))

    elif resource_type == 'groups':
        seen_codes = set(StudentGroup.objects.values_list('code', flat=True))
        file_codes = set()
        for idx, row in enumerate(reader, start=2):
            code = (row.get('code') or '').strip()
            name = (row.get('name') or '').strip()
            if not code or not name:
                errors.append(f"Row {idx}: Group code and name are required.")
                continue
            if code in file_codes or code in seen_codes:
                errors.append(f"Row {idx}: Group code '{code}' already exists or is duplicated in file.")
                continue
            file_codes.add(code)
            records_to_create.append(StudentGroup(code=code, name=name))

    elif resource_type == 'courses':
        teachers_by_name = {t.name.lower(): t for t in Teacher.objects.all()}
        groups_by_code = {g.code.lower(): g for g in StudentGroup.objects.all()}
        seen_codes = set(Course.objects.values_list('code', flat=True))
        file_codes = set()

        for idx, row in enumerate(reader, start=2):
            code = (row.get('code') or '').strip()
            name = (row.get('name') or '').strip()
            credits_str = (row.get('credit_hours') or '3').strip()
            enrolled_str = (row.get('enrolled_students') or '').strip()
            diff = (row.get('difficulty') or 'MEDIUM').strip().upper()
            lab_str = (row.get('requires_lab') or 'false').strip().lower()
            teacher_name = (row.get('teacher') or '').strip()
            group_code = (row.get('group') or '').strip()

            if not code or not name:
                errors.append(f"Row {idx}: Course code and name are required.")
                continue
            if code in file_codes or code in seen_codes:
                errors.append(f"Row {idx}: Course code '{code}' already exists or is duplicated.")
                continue
            file_codes.add(code)

            try:
                credit_int = int(credits_str)
                if credit_int <= 0:
                    raise ValueError()
            except ValueError:
                errors.append(f"Row {idx}: credit_hours must be a positive integer.")
                continue

            try:
                enrolled_int = int(enrolled_str)
                if enrolled_int <= 0:
                    raise ValueError()
            except ValueError:
                errors.append(f"Row {idx}: enrolled_students must be a positive integer.")
                continue

            if diff not in ('EASY', 'MEDIUM', 'HARD'):
                errors.append(f"Row {idx}: difficulty must be EASY, MEDIUM, or HARD.")
                continue

            teacher_obj = None
            if teacher_name:
                teacher_obj = teachers_by_name.get(teacher_name.lower())
                if not teacher_obj:
                    errors.append(f"Row {idx}: Faculty member '{teacher_name}' not found. Please add faculty first.")
                    continue

            group_obj = None
            if group_code:
                group_obj = groups_by_code.get(group_code.lower())
                if not group_obj:
                    errors.append(f"Row {idx}: Student group '{group_code}' not found. Please add group first.")
                    continue

            records_to_create.append(Course(
                code=code,
                name=name,
                credit_hours=credit_int,
                enrolled_students=enrolled_int,
                difficulty=diff,
                requires_lab=(lab_str in ('true', '1', 'yes')),
                teacher=teacher_obj,
                group=group_obj,
            ))

    elif resource_type == 'availability':
        teachers_by_name = {t.name.lower(): t for t in Teacher.objects.all()}
        existing_keys = set(TeacherAvailability.objects.values_list('teacher_id', 'day', 'time_slot'))
        file_keys = set()

        for idx, row in enumerate(reader, start=2):
            t_name = (row.get('teacher') or '').strip()
            day = (row.get('day') or '').strip().upper()
            slot = (row.get('time_slot') or '').strip()

            t_obj = teachers_by_name.get(t_name.lower())
            if not t_obj:
                errors.append(f"Row {idx}: Faculty member '{t_name}' not found.")
                continue

            if day not in VALID_DAYS:
                errors.append(f"Row {idx}: Invalid day '{day}'. Allowed: {VALID_DAYS}.")
                continue

            if slot not in TIME_SLOTS:
                errors.append(f"Row {idx}: Invalid time slot '{slot}'. Allowed: {TIME_SLOTS}.")
                continue

            key = (t_obj.id, day, slot)
            if key in file_keys or key in existing_keys:
                errors.append(f"Row {idx}: Availability for {t_name} on {day} {slot} already exists or is duplicated.")
                continue
            file_keys.add(key)

            records_to_create.append(TeacherAvailability(teacher=t_obj, day=day, time_slot=slot))

    # If any error exists, reject entire file without saving anything
    if errors:
        return Response({
            "success": False,
            "created_count": 0,
            "errors": errors,
            "message": f"Validation failed with {len(errors)} error(s). No records were imported."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Perform atomic database save
    with transaction.atomic():
        if resource_type == 'rooms':
            Room.objects.bulk_create(records_to_create)
        elif resource_type == 'teachers':
            Teacher.objects.bulk_create(records_to_create)
        elif resource_type == 'groups':
            StudentGroup.objects.bulk_create(records_to_create)
        elif resource_type == 'courses':
            Course.objects.bulk_create(records_to_create)
        elif resource_type == 'availability':
            TeacherAvailability.objects.bulk_create(records_to_create)

    return Response({
        "success": True,
        "created_count": len(records_to_create),
        "message": f"Successfully imported {len(records_to_create)} {resource_type} records.",
    }, status=status.HTTP_201_CREATED)


# =============================================================================
# ACCURATE ANALYTICS & DASHBOARD METRICS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Returns API-backed statistics:
    - Required versus scheduled weekly sessions.
    - Fully, partially, and unscheduled courses (distinct course counting).
    - Room utilization.
    - Faculty workload.
    - Student-group long gaps.
    """
    rooms = list(Room.objects.all())
    teachers = list(Teacher.objects.all())
    courses = list(Course.objects.select_related('group').all())
    schedules = list(Schedule.objects.select_related('course', 'teacher', 'room', 'course__group').all())
    groups = list(StudentGroup.objects.all())

    total_slots = 5 * 7  # 35 weekly teaching slots

    # Session counts
    total_required_sessions = sum(c.credit_hours for c in courses)
    total_scheduled_sessions = len(schedules)
    remaining_sessions = max(0, total_required_sessions - total_scheduled_sessions)

    # Distinct course scheduling status
    course_session_counts = Counter(s.course_id for s in schedules)
    fully_scheduled = []
    partially_scheduled = []
    unscheduled = []

    for c in courses:
        scheduled_count = course_session_counts.get(c.id, 0)
        c_info = {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "group": c.group.code if c.group else "General",
            "required_credits": c.credit_hours,
            "scheduled_sessions": scheduled_count,
        }
        if scheduled_count >= c.credit_hours:
            fully_scheduled.append(c_info)
        elif scheduled_count > 0:
            partially_scheduled.append(c_info)
        else:
            unscheduled.append(c_info)

    # Room utilization
    room_use = Counter(s.room_id for s in schedules)
    utilization = []
    for r in rooms:
        used = room_use.get(r.id, 0)
        utilization.append({
            "room": r.room_number,
            "room_type": r.room_type,
            "capacity": r.capacity,
            "used_slots": used,
            "total_slots": total_slots,
            "utilization_pct": round(used / total_slots * 100, 1) if total_slots else 0,
        })

    # Faculty workload
    teacher_use = Counter(s.teacher_id for s in schedules)
    workload = []
    for t in teachers:
        workload.append({
            "teacher": t.name,
            "department": t.department,
            "assigned_slots": teacher_use.get(t.id, 0),
        })

    # Weekday distribution
    day_use = Counter(s.day for s in schedules)

    # Student-group long gaps
    schedule_dicts = [
        {"course_id": s.course_id, "day": s.day, "time_slot": s.time_slot}
        for s in schedules
    ]
    long_gaps = compute_long_gaps(schedule_dicts, courses)

    return Response({
        "counts": {
            "rooms": len(rooms),
            "teachers": len(teachers),
            "student_groups": len(groups),
            "courses": len(courses),
            "total_required_sessions": total_required_sessions,
            "total_scheduled_sessions": total_scheduled_sessions,
            "remaining_sessions": remaining_sessions,
            "fully_scheduled_courses": len(fully_scheduled),
            "partially_scheduled_courses": len(partially_scheduled),
            "unscheduled_courses": len(unscheduled),
            "student_group_long_gaps_count": len(long_gaps),
        },
        "breakdown": {
            "fully_scheduled": fully_scheduled,
            "partially_scheduled": partially_scheduled,
            "unscheduled": unscheduled,
        },
        "long_gaps": long_gaps,
        "utilization": sorted(utilization, key=lambda x: x["utilization_pct"], reverse=True),
        "workload": sorted(workload, key=lambda x: x["assigned_slots"], reverse=True),
        "by_day": {d: day_use.get(d, 0) for d in VALID_DAYS},
        "definitions": {
            "required_sessions": "Sum of all course credit hours (1 credit = 1 weekly 1-hour session).",
            "scheduled_sessions": "Total class sessions currently placed on the timetable.",
            "fully_scheduled": "Courses having all required weekly sessions scheduled.",
            "partially_scheduled": "Courses with at least one session scheduled, but fewer than required credit hours.",
            "unscheduled": "Courses with zero sessions scheduled on the timetable.",
            "room_utilization": "Percentage of 35 weekly teaching slots occupied in each room.",
            "student_group_long_gap": "At least 3 consecutive empty teaching slots between a group's classes on the same day.",
        },
    })
