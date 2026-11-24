from django.contrib import admin
from .models import Room, Teacher, TeacherAvailability, Course, Schedule


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'capacity', 'room_type', 'is_available')
    list_filter = ('room_type', 'is_available')
    search_fields = ('room_number',)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'department')
    list_filter = ('department',)
    search_fields = ('name',)


@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'day', 'time_slot')
    list_filter = ('day',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'enrolled_students', 'difficulty', 'requires_lab', 'teacher')
    list_filter = ('difficulty', 'requires_lab')
    search_fields = ('code', 'name')


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('course', 'teacher', 'room', 'day', 'time_slot', 'status')
    list_filter = ('day', 'status')
