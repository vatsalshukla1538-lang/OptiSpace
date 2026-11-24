from django.core.management.base import BaseCommand
from seed import seed_users
from scheduling.it_data import seed_it_pdf_data


class Command(BaseCommand):
    help = "Seeds default users (admin, viewer) and authentic MITS IT Department timetable data."

    def handle(self, *args, **options):
        self.stdout.write("1. Ensuring baseline Admin and Viewer users exist...")
        seed_users()
        self.stdout.write("2. Loading authentic IT Semester-I data directly from MITS Master TimeTable PDF...")
        data = seed_it_pdf_data()
        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded! Loaded {data['total_courses']} courses, "
            f"{len(data['rooms'])} rooms, {len(data['teachers'])} teachers, "
            f"{data['sessions_scheduled']} scheduled sessions."
        ))
