from django.db import models #type: ignore
from django import utils #type: ignore

from Students.models import Student
from Core.models import Unit, Class
 
# ==========================================================================================#
# ========================              E-LEARNING MODULE          =========================#
class Books(models.Model):
    name = models.CharField(max_length=30)
    dor = models.DateTimeField(default=utils.timezone.now, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Book'
        verbose_name_plural = 'Books'

class Chapter(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="Chapter")
    number = models.PositiveIntegerField(default = 1)
    title = models.CharField(max_length=255)
    objectives = models.TextField(blank=True, null=True)
    duration = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Chapter {self.number}: {self.title} - {str(self.unit)}"

    class Meta:
        verbose_name = 'Chapter'
        verbose_name_plural = 'Chapters'
        ordering = ["number", "id"]

class Lesson(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="lessons")
    number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title}: {self.chapter}"
    
    class Meta:
        verbose_name = 'Lesson'
        verbose_name_plural = 'Lessons'
        ordering = ["number", "id"]

    def get_short_description(self):
        return f"{str(self.description[0:50])}....."

class CourseContent(models.Model):
    """Represents content (PDF, video, quiz, or assignment) in a course"""
    PDF = "pdf"; TEXT = "text"; AUDIO = "audio"; VIDEO = "video"; IMAGE = "image"
    CONTENT_TYPES = [(PDF, "PDF Document"), (TEXT,"Text"), (AUDIO,"Audio"), (VIDEO,"Video"), (IMAGE,"Image")]

    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES)
    title = models.CharField(max_length=255)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="contents")

    # For storing different content types
    text = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='course_pdfs/', null=True, blank=True)
    external_url = models.URLField(null=True, blank=True)
    caption = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ["order", "id"]

    def clean(self):
        # Optional: validate required fields by kind
        from django.core.exceptions import ValidationError #type: ignore
        if self.content_type == self.TEXT and not self.text:
            raise ValidationError("Text content requires text.")
        if self.content_type in {self.AUDIO, self.VIDEO, self.IMAGE} and not (self.pdf_file or self.external_url):
            raise ValidationError("Media content requires file or external_url.")
        if self.content_type == self.PDF and not self.pdf_file:
            raise ValidationError("Document content requires document uploaded.")
        return super().clean()

class LessonProgress(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0..100

    class Meta:
        unique_together = ("student", "lesson")

# class Quiz(models.Model):
#     """Represents a quiz for a specific lesson/topic"""
#     classs = models.ForeignKey(Class, on_delete=models.CASCADE)
#     question = models.TextField()  # The question being asked in the quiz
#     coursecontent = models.ForeignKey(CourseContent, on_delete=models.CASCADE, related_name="coursequizez")
#     deadline = models.DateTimeField()  # The deadline for submitting the quiz
#     marks = models.IntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the quiz was created

#     def is_past_due(self):
#         """Check if the quiz deadline has passed."""
#         return utils.timezone.now() > self.deadline

#     def __str__(self):
#         return f"Quiz: {self.question[:15]}..."  # Show first 50 chars of the question

# class Choice(models.Model):
#     """Represents an answer choice for a quiz question."""
#     quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='choices')
#     choice_text = models.CharField(max_length=255)  # Text of the answer choice
#     is_correct = models.BooleanField(default=False)  # True if this is the correct answer, False otherwise

#     def __str__(self):
#         return self.choice_text

# class QuizSubmission(models.Model):
#     """Represents a quiz submission from a user."""
#     student = models.ForeignKey(Student, on_delete=models.CASCADE) # Assuming we have students
#     quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
#     selected_choices = models.ManyToManyField(Choice)  # The choices selected by the student
#     point = models.IntegerField()
#     submitted_at = models.DateTimeField(auto_now_add=True)

#     def is_correct(self):
#         """Check if the student's answers are correct by comparing to the correct choices."""
#         correct_choices = self.quiz.choices.filter(is_correct=True)
#         selected_choices = self.selected_choices.all()

#         result = set(correct_choices) == set(selected_choices)

#         if result == True:
#             self.point = int(self.quiz.marks)
#         else:
#             self.point = 0
#         self.save()

#         return result

#     def __str__(self):
#         return f"Submission by {self.student} for quiz '{self.quiz.question[:15]}...'"
