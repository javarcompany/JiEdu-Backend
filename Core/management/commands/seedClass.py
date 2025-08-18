# yourapp/management/commands/seedClass.py
from django.core.management.base import BaseCommand #type: ignore
import random

from Core.models import Branch, CourseDuration, Class, Term

class Command(BaseCommand):
    help = "Seed Class table from a real-time generation."

    def handle(self, *args, **options):
        created, skipped = 0, 0
        skipped_class = []
        
        branches = list(Branch.objects.all())
        course_durations = list(CourseDuration.objects.all())
        current_intake = Term.objects.first()

        Class.objects.all().delete()
        for branch in branches:
            for course_duration in course_durations:
                no_classes = random.randint(1, 3)
                try:
                    course = course_duration.course.abbr # e.g. "CICT"
                    module = course_duration.module.abbr[1] # e.g "M1"
                    class_name = str(course)+str(module)
                except Exception:
                    self.stdout.write(self.style.ERROR(f"Invalid format: either {course} or {module}"))
                    continue

                for i in range(no_classes):
                    if no_classes > 1:
                        if i<1:
                            up_class_name = class_name+"A"
                        elif i<2:
                            up_class_name = class_name+"B"
                        else:
                            up_class_name = class_name+"C"
                    else:
                        up_class_name = class_name

                    if Class.objects.filter(name=up_class_name, course = course_duration.course, module = course_duration.module, branch = branch, intake = current_intake ).exists():
                        skipped += 1
                        skipped_class.append(up_class_name)
                        continue

                    Class.objects.create(
                        name=up_class_name, 
                        course = course_duration.course, 
                        module = course_duration.module, 
                        branch = branch, 
                        intake = current_intake
                    )
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} classes"))
        self.stdout.write(self.style.WARNING(f"Skipped {skipped} classes (already existed)"))
        self.stdout.write(self.style.WARNING(f"{skipped_class}"))
