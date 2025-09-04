from django.db import models #type: ignore
from django.conf import settings  #type: ignore

from Students.models import Student
from Staff.models import StaffWorkload, Staff
from Core.models import CourseDuration, Term

# -----------------------------
# 1. Exam Session (Overall Period)
# -----------------------------
class ExamSession(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)  # e.g., "March 2025 CAT"
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.title} ({self.term})"

# -----------------------------
# 2. Exam Timetable (Specific Exams)
# -----------------------------
class ExamTimetable(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),         # created by admin but not visible
        ("published", "Published"), # visible to staff/students
        ("approved", "Approved"),   # exams officer approved
        ("open", "Open"),           # exam is running
        ("closed", "Closed"),       # finished
    ]

    EXAM_TYPE_CHOICES = [
        ("cat", "CAT"),
        ("final", "Final Exam"),
        ("practical", "Practical"),
    ]

    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE)
    unit = models.ForeignKey(StaffWorkload, on_delete=models.CASCADE)  # from staff workload
    exam_type = models.CharField(max_length=50, choices=EXAM_TYPE_CHOICES)
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=255, blank=True, null=True)
    invigilators = models.ManyToManyField(Staff, related_name="invigilated_exams")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        Staff, null=True, blank=True, related_name="approved_exams", on_delete=models.SET_NULL
    )
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.unit} - {self.exam_type} ({self.session})"

# -----------------------------
# 3. Questions
# -----------------------------
class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("mcq", "Multiple Choice"),
        ("match", "Matching"),
        ("fill", "Fill in the Blank"),
        ("order", "Ordering"),
        ("hotspot", "Hotspot"),
        ("short", "Short Answer"),
        ("essay", "Essay"),
        ("calc", "Calculation"),
        ("code", "Coding"),
        ("case", "Case Study"),
        ("oral", "Oral"),
        ("video", "Video"),
    ]

    QUESTION_STATUS_CHOICES = [
        ("draft", "Draft"),         # Staff is still editing
        ("submitted", "Submitted"), # Staff finished, awaiting approval
        ("approved", "Approved"),   # Exams officer approved
    ]

    exam = models.ForeignKey(ExamTimetable, on_delete=models.CASCADE)
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    marks = models.FloatField()
    attachment = models.FileField(upload_to="exam/questions/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=QUESTION_STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(Staff, on_delete=models.CASCADE)

    def __str__(self):
        return f"Q{self.id} - {self.question_type}"

class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Option for {self.question.id}"

# -----------------------------
# 4. Student Exam Registration
# -----------------------------
class ExamRegistration(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(ExamTimetable, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "exam")

    def __str__(self):
        return f"{self.student} registered for {self.exam}"

# -----------------------------
# 5. Student Exam Submissions
# -----------------------------
class ExamSubmission(models.Model):
    registration = models.ForeignKey(ExamRegistration, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(blank=True, null=True)
    is_submitted = models.BooleanField(default=False)
    total_marks = models.FloatField(default=0)

    def __str__(self):
        return f"{self.registration.student} -> {self.registration.exam}"

class Answer(models.Model):
    submission = models.ForeignKey(ExamSubmission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    response_text = models.TextField(blank=True, null=True)
    selected_options = models.ManyToManyField(AnswerOption, blank=True)  # for MCQ/matching
    marks_awarded = models.FloatField(default=0)

    def __str__(self):
        return f"Answer by {self.submission.registration.student} Q{self.question.id}"

# -----------------------------
# 6. Grading
# -----------------------------
class GradingScheme(models.Model):
    """
    Defines grading ranges (A, B, C...).
    Configurable per institution or per course if needed.
    """
    course = models.ForeignKey(CourseDuration, on_delete=models.CASCADE, related_name="grades", null=True, blank=True,)   # e.g. "Default", "Engineering Scheme"
    min_mark = models.FloatField()
    max_mark = models.FloatField()
    grade = models.CharField(max_length=5)    # e.g. "A", "B+", "C"
    remark = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-max_mark"]

    def __str__(self):
        return f"{self.grade} ({self.min_mark}-{self.max_mark})"
    
# -----------------------------
# 7. Results
# -----------------------------
class ExamResult(models.Model):
    """
    Stores results per student per exam.
    """
    exam = models.ForeignKey(ExamTimetable, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="exam_results")
    total_marks = models.FloatField(default=0.0)
    grade = models.CharField(max_length=5, blank=True, null=True)
    remark = models.CharField(max_length=255, blank=True, null=True)
    graded_by = models.ForeignKey(
        Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name="graded_results"
    )
    graded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("exam", "student")

    def __str__(self):
        return f"{self.student.regno} - {self.exam} ({self.grade})"

    def auto_assign_grade(self):
        """
        Match total_marks against grading scheme and assign grade + remark.
        """
        scheme = GradingScheme.objects.filter(
            course__course=self.exam.unit.unit.course,
            course__module=self.exam.unit.unit.module,
            min_mark__lte=self.total_marks,
            max_mark__gte=self.total_marks
        ).first()

        if scheme:
            self.grade = scheme.grade
            self.remark = scheme.remark
        else:
            self.grade = "N/A"
            self.remark = "Out of range"
        self.save()

