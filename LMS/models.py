from django.db import models #type: ignore
from django import utils #type: ignore

from Students.models import Student
from Core.models import Unit
 
# ==========================================================================================#
# ========================              E-LEARNING MODULE          =========================#
class Book(models.Model):
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
    is_published = models.BooleanField(default=False, blank = True, null = True)
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
        verbose_name = 'Course Content'
        verbose_name_plural = 'Course Contents'

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
