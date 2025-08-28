from django.db import models #type: ignore
from django.conf import settings #type: ignore
from Core.models import Term, Branch, Department, Course, Class  # adjust import paths to your app structure
from Staff.models import Staff
from Students.models import Student

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_all_day = models.BooleanField(default=False, blank=True, null = True)

    location = models.CharField(max_length=255, blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_events"
    )

    # Academic tie-ins
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="events", blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    Class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")

    # Event classification
    event_type = models.CharField(
        max_length=50,
        choices=[
            ("Personal", "Personal Event"),
            ("Class", "Class Event"),
            ("Exam", "Exam"),
            ("Assignment", "Assignment"),
            ("Meeting", "Meeting"),
            ("Holiday", "Holiday"),
            ("Sports", "Sports"),
            ("Other", "Other"),
        ],
        default="Personal",
        blank=True, null = True
    )

    visibility = models.CharField(
        max_length=20,
        choices=[
            ("public", "Public"),
            ("branch", "Branch Only"),
            ("department", "Department Only"),
            ("course", "Course Only"),
            ("class", "Class Only"),
            ("students", "Students Only"),
            ("classreps", "Class Representatives Only"),
            ("staff", "Staff Only"),
            ("classtutors", "Class Tutors Only"),
            ("admins", "Administrators Only"),
            ("private", "Private"),
        ],
        default="private",
        blank=True, null = True
    )

    # Event Color Code
    level = models.CharField(max_length=20, choices=[
            ("danger", "danger"),
            ("success", "success"),
            ("primary", "primary"),
            ("warning", "warning"),
            ("info", "info"),
        ],
        blank=True, null=True, default="primary"
    )

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.term})"

class EventParticipant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        choices=[
            ("invited", "Invited"),
            ("going", "Going"),
            ("not_going", "Not Going"),
            ("maybe", "Maybe"),
        ],
        default="invited"
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user")

    def __str__(self):
        return f"{self.user} → {self.event} ({self.status})"

class EventReminder(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="reminders")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    reminder_time = models.DateTimeField()
    method = models.CharField(
        max_length=20,
        choices=[("email", "Email"), ("sms", "SMS"), ("app", "App Notification")],
        default="app"
    )
    sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Reminder for {self.user} @ {self.reminder_time}"

