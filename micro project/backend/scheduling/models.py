from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

# Shared standard definitions across backend and frontend
DAYS_OF_WEEK = (
    ('MON', 'Monday'),
    ('TUE', 'Tuesday'),
    ('WED', 'Wednesday'),
    ('THU', 'Thursday'),
    ('FRI', 'Friday'),
)

TIME_SLOTS = [
    "10:00-11:00",
    "11:00-12:00",
    "01:00-02:00",
    "02:00-03:00",
    "03:00-04:00",
    "04:00-05:00",
    "05:00-06:00",
    "09:00-10:00",
    "12:00-13:00",
    "13:00-14:00",
    "14:00-15:00",
    "15:00-16:00",
    "16:00-17:00",
    "17:00-18:00",
]


class Room(models.Model):
    """
    Represents a learning space (Lecture Hall or Laboratory).
    Only available rooms are considered during automated scheduling.
    """
    ROOM_TYPES = (
        ('LECTURE', 'Lecture Hall'),
        ('LAB', 'Laboratory'),
    )
    room_number = models.CharField(max_length=50, unique=True)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='LECTURE')
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.room_number} ({self.capacity} seats, {self.room_type})"


class Teacher(models.Model):
    """
    Represents a faculty member with their department.
    """
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class TeacherAvailability(models.Model):
    """
    Specific (day, time_slot) windows when a teacher is free to teach.
    If a teacher has no records here, they are considered available anytime.
    """
    teacher = models.ForeignKey(Teacher, related_name='availabilities', on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    time_slot = models.CharField(max_length=50)

    class Meta:
        unique_together = ('teacher', 'day', 'time_slot')

    def __str__(self):
        return f"{self.teacher.name} available on {self.day} at {self.time_slot}"


class StudentGroup(models.Model):
    """
    Represents a student cohort/batch (e.g., CSE-A, IT-B).
    Used to prevent scheduling overlapping classes for the same students
    and to measure consecutive gap hours between classes.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)  # e.g., "CSE-A"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Course(models.Model):
    """
    Represents an academic course/subject.
    Each credit hour corresponds to one weekly 1-hour session.
    """
    DIFFICULTY_LEVELS = (
        ('EASY', 'Easy'),
        ('MEDIUM', 'Medium'),
        ('HARD', 'Hard'),
    )
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    credit_hours = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    enrolled_students = models.IntegerField(validators=[MinValueValidator(1)])
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='MEDIUM')
    requires_lab = models.BooleanField(default=False)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey(
        StudentGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
    )

    def __str__(self):
        group_str = f" [{self.group.code}]" if self.group else ""
        return f"{self.code} - {self.name}{group_str}"


class Schedule(models.Model):
    """
    A single scheduled weekly 1-hour class session linking Course, Teacher, Room, Day, and TimeSlot.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    day = models.CharField(max_length=3, choices=DAYS_OF_WEEK)
    time_slot = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='SCHEDULED')

    class Meta:
        unique_together = (
            ('teacher', 'day', 'time_slot'),
            ('room', 'day', 'time_slot'),
            ('course', 'day', 'time_slot'),
        )

    def __str__(self):
        return f"{self.course.code} | {self.teacher.name} | {self.room.room_number if self.room else 'No Room'} | {self.day} {self.time_slot}"


class UserProfile(models.Model):
    """
    Stores viewer/student profile metadata, specifically their enrolled student batch/section.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    batch = models.CharField(max_length=50, blank=True, default='')  # e.g., 'Batch-A1', 'Batch-A2', 'Batch-B1', 'Batch-B2', 'SEC-A', 'SEC-B'

    def __str__(self):
        return f"{self.user.username} ({self.batch or 'No Batch'})"
