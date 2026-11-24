from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoomViewSet,
    TeacherViewSet,
    TeacherAvailabilityViewSet,
    StudentGroupViewSet,
    CourseViewSet,
    ScheduleViewSet,
    generate_schedule,
    clear_schedule,
    dashboard_stats,
    me,
    register,
    export_csv,
    export_excel,
    export_pdf,
    validate_manual,
    import_csv,
    download_csv_template,
)

router = DefaultRouter()
router.register(r'rooms', RoomViewSet)
router.register(r'teachers', TeacherViewSet)
router.register(r'availabilities', TeacherAvailabilityViewSet)
router.register(r'groups', StudentGroupViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'schedules', ScheduleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('schedule/generate/', generate_schedule, name='generate_schedule'),
    path('schedule/clear/', clear_schedule, name='clear_schedule'),
    path('schedule/validate/', validate_manual, name='validate_manual'),
    path('schedule/export.csv', export_csv, name='export_csv'),
    path('schedule/export.xlsx', export_excel, name='export_excel'),
    path('schedule/export.pdf', export_pdf, name='export_pdf'),
    path('import/<str:resource_type>/', import_csv, name='import_csv'),
    path('import/template/<str:resource_type>/', download_csv_template, name='download_csv_template'),
    path('dashboard/stats/', dashboard_stats, name='dashboard_stats'),
    path('me/', me, name='me'),
    path('auth/register/', register, name='register'),
    path('register/', register, name='register_alias'),
]
