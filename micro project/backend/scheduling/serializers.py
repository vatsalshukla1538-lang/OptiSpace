"""
serializers.py - Converts database models to and from JSON for the REST API,
with comprehensive validation for manual and automated scheduling actions.
"""

from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Room, Teacher, TeacherAvailability, StudentGroup, Course, Schedule, UserProfile, TIME_SLOTS, DAYS_OF_WEEK

VALID_DAYS = [d[0] for d in DAYS_OF_WEEK]


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Room capacity must be at least 1.")
        return value


class TeacherSerializer(serializers.ModelSerializer):
    availabilities = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Teacher
        fields = '__all__'


class TeacherAvailabilitySerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)

    class Meta:
        model = TeacherAvailability
        fields = '__all__'

    def validate(self, attrs):
        day = attrs.get('day')
        time_slot = attrs.get('time_slot')
        if day and day not in VALID_DAYS:
            raise serializers.ValidationError(f"Invalid day '{day}'. Must be one of {VALID_DAYS}.")
        if time_slot and time_slot not in TIME_SLOTS:
            raise serializers.ValidationError(f"Invalid time slot '{time_slot}'. Supported slots: {TIME_SLOTS}.")
        return attrs


class StudentGroupSerializer(serializers.ModelSerializer):
    course_count = serializers.IntegerField(source='courses.count', read_only=True)

    class Meta:
        model = StudentGroup
        fields = ('id', 'name', 'code', 'course_count')


class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True, default='')
    group_code = serializers.CharField(source='group.code', read_only=True, default='')
    group_name = serializers.CharField(source='group.name', read_only=True, default='')

    class Meta:
        model = Course
        fields = '__all__'

    def validate_credit_hours(self, value):
        if value <= 0:
            raise serializers.ValidationError("Credit hours must be at least 1.")
        return value

    def validate_enrolled_students(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enrolled students must be at least 1.")
        return value


class ScheduleSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_requires_lab = serializers.BooleanField(source='course.requires_lab', read_only=True, default=False)
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    group_code = serializers.CharField(source='course.group.code', read_only=True, default='')
    group_name = serializers.CharField(source='course.group.name', read_only=True, default='')

    class Meta:
        model = Schedule
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        c = instance.course
        t = instance.teacher
        r = instance.room
        data['course_id'] = instance.course_id
        data['teacher_id'] = instance.teacher_id
        data['room_id'] = instance.room_id
        if c:
            data['course'] = {
                'id': c.id,
                'code': c.code,
                'name': c.name,
                'requires_lab': c.requires_lab,
                'credit_hours': c.credit_hours,
                'group': {
                    'id': c.group.id,
                    'code': c.group.code,
                    'name': c.group.name,
                } if c.group else None,
            }
        if t:
            data['teacher'] = {
                'id': t.id,
                'name': t.name,
                'department': t.department,
            }
        if r:
            data['room'] = {
                'id': r.id,
                'room_number': r.room_number,
                'capacity': r.capacity,
                'room_type': r.room_type,
            }
        return data

    def validate(self, attrs):
        """
        Validates all constraints for manual API writes and drag-and-drop moves.
        """
        course = attrs.get('course', getattr(self.instance, 'course', None))
        teacher = attrs.get('teacher', getattr(self.instance, 'teacher', None))
        room = attrs.get('room', getattr(self.instance, 'room', None))
        day = attrs.get('day', getattr(self.instance, 'day', None))
        time_slot = attrs.get('time_slot', getattr(self.instance, 'time_slot', None))

        if not all([course, teacher, room, day, time_slot]):
            return attrs

        # 1. Day and Time slot validity
        if day not in VALID_DAYS:
            raise serializers.ValidationError(f"Invalid day '{day}'. Supported days: {VALID_DAYS}.")
        if time_slot not in TIME_SLOTS:
            raise serializers.ValidationError(f"Invalid time slot '{time_slot}'. Supported: {TIME_SLOTS}.")

        # 2. Room availability check
        if not room.is_available:
            raise serializers.ValidationError(f"Room {room.room_number} is marked as unavailable.")

        # 3. Room capacity check
        if room.capacity < course.enrolled_students:
            raise serializers.ValidationError(
                f"Room {room.room_number} capacity ({room.capacity}) is smaller than course enrollment ({course.enrolled_students})."
            )

        # 4. Room type match (LAB vs LECTURE)
        if course.requires_lab and room.room_type != 'LAB':
            raise serializers.ValidationError("Practical lab course must be placed in a Laboratory.")
        if not course.requires_lab and room.room_type != 'LECTURE':
            raise serializers.ValidationError("Theory lecture course must be placed in a Lecture hall.")

        # 5. Teacher availability windows
        avails = list(teacher.availabilities.all()) if teacher else []
        if avails and not any(a.day == day and a.time_slot == time_slot for a in avails):
            raise serializers.ValidationError(f"{teacher.name} is not available on {day} at {time_slot}.")

        # 6. Double booking checks (excluding self if updating existing schedule)
        qs = Schedule.objects.filter(day=day, time_slot=time_slot)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        # Room collision
        if qs.filter(room=room).exists():
            raise serializers.ValidationError(f"Room {room.room_number} is already booked at {day} {time_slot}.")

        # Teacher collision
        if qs.filter(teacher=teacher).exists():
            raise serializers.ValidationError(f"{teacher.name} is already teaching a class at {day} {time_slot}.")

        # Course collision (same course at same time)
        if qs.filter(course=course).exists():
            raise serializers.ValidationError(f"Course {course.code} is already scheduled at {day} {time_slot}.")

        # Student group collision (same group cannot attend two classes simultaneously)
        if course.group_id:
            group_clash = qs.filter(course__group_id=course.group_id).select_related('course').first()
            if group_clash:
                raise serializers.ValidationError(
                    f"Student group '{course.group.code}' is already attending course {group_clash.course.code} at {day} {time_slot}."
                )

        return attrs


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    batch = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff', 'role', 'batch')

    def get_role(self, obj):
        return 'ADMIN' if obj.is_staff else 'VIEWER'

    def get_batch(self, obj):
        try:
            return obj.profile.batch
        except Exception:
            return ""


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, min_length=3)
    password = serializers.CharField(write_only=True, min_length=4)
    batch = serializers.CharField(max_length=50, required=True)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already taken. Please choose another username.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            is_staff=False
        )
        UserProfile.objects.create(user=user, batch=validated_data.get('batch', ''))
        return user
