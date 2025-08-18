# yourapp/management/commands/seedUnit.py
from django.core.management.base import BaseCommand #type: ignore
import random

from Core.models import Course, Module, Unit
from .units import Units  # move your big dict into units_data.py

class Command(BaseCommand):
    help = "Seed Units table from a predefined Units dictionary"

    def handle(self, *args, **options):
        created, skipped = 0, 0
        skipped_unit = []

        Unit.objects.all().delete()
        for course_key, modules in Units.items():
            try:
                abbrev = course_key.split()[0]           # e.g. "CICT"
                code = course_key.split()[1]
            except Exception:
                self.stdout.write(self.style.ERROR(f"Invalid course key format: {course_key}"))
                continue

            course = Course.objects.filter(abbr=abbrev, code=code).first()
            if not course:
                self.stdout.write(self.style.WARNING(f"Course not found: {course_key}"))
                continue

            for module_name, unit_list in modules.items():
                module = Module.objects.filter(abbr=module_name).first()
                if not module:
                    self.stdout.write(self.style.WARNING(f"Module not found: {module_name} in {course_key}"))
                    continue

                for uncode, unit_name, unit_abbr in unit_list:
                    if Unit.objects.filter(uncode=uncode, course=course).exists():
                        skipped += 1
                        skipped_unit.append(uncode)
                        continue

                    Unit.objects.create(
                        uncode=uncode,
                        name=unit_name,
                        abbr=unit_abbr, 
                        course=course,
                        module=module,
                        weekly_hours=random.choice([4, 6, 8, 10, 12])
                    )
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} units"))
        self.stdout.write(self.style.WARNING(f"Skipped {skipped} units (already existed)"))
        self.stdout.write(self.style.WARNING(f"{skipped_unit}"))
