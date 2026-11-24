"""
seed.py - Seeds default users and the authentic IT Department dataset from MITS Gwalior PDF.
Usage:
    python seed.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from scheduling.models import UserProfile
from scheduling.it_data import seed_it_pdf_data


def seed_users():
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@mits.local', 'is_staff': True, 'is_superuser': True},
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print("Created default admin user: admin / admin123")
    UserProfile.objects.update_or_create(user=admin, defaults={'batch': 'ALL'})

    viewer, created = User.objects.get_or_create(
        username='viewer',
        defaults={'email': 'viewer@mits.local', 'is_staff': False, 'is_superuser': False},
    )
    if created:
        viewer.set_password('viewer123')
        viewer.save()
        print("Created default viewer user: viewer / viewer123")
    UserProfile.objects.update_or_create(user=viewer, defaults={'batch': 'Batch-A1'})


def run():
    print("1. Ensuring baseline Admin and Viewer users exist...")
    seed_users()

    print("2. Loading authentic IT Semester-I data directly from MITS Master TimeTable PDF...")
    data = seed_it_pdf_data()
    print(f"Loaded {data['total_courses']} courses/modules for Section A and Section B.")
    print(f"Rooms: {len(data['rooms'])} (SH-5, J013, DS Lab, CL Lab, PL Lab).")
    print(f"Faculty: {len(data['teachers'])} Instructors from official MITS timetable PDF legend.")
    print(f"Groups: {len(data['groups'])} (Sections A & B, Batches A1, A2, B1, B2).")
    print(f"Scheduled: {data['sessions_scheduled']} exact sessions loaded with ZERO conflicts!")


if __name__ == "__main__":
    run()
