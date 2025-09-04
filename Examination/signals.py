from django.db.models.signals import post_save, pre_save #type: ignore
from django.dispatch import receiver #type: ignore
from django.utils import timezone #type: ignore

from .models import Question, ExamTimetable, ExamResult

# When all questions for an exam are approved, auto-move ExamTimetable to "PUBLISHED"
@receiver(post_save, sender=Question)
def auto_publish_exam(sender, instance, **kwargs):
    exam = instance.exam
    if exam.questions.exists() and all(q.status == "approved" for q in exam.questions.all()):
        exam.status = "published"
        exam.save()

# Before saving ExamTimetable, check exam time and update status
@receiver(pre_save, sender=ExamTimetable)
def auto_update_exam_status(sender, instance, **kwargs):
    now = timezone.now()
    exam_start = timezone.make_aware(
        timezone.datetime.combine(instance.exam_date, instance.start_time)
    )
    exam_end = timezone.make_aware(
        timezone.datetime.combine(instance.exam_date, instance.end_time)
    )

    if instance.status == "approved":
        if exam_start <= now <= exam_end:
            instance.status = "open"
        elif now > exam_end:
            instance.status = "closed"

@receiver(post_save, sender=ExamResult)
def assign_grade_on_save(sender, instance, created, **kwargs):
    instance.auto_assign_grade()