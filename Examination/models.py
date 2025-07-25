from django.db import models #type: ignore
from django import utils #type: ignore

from Core.models import (
    Unit, AcademicYear, Intake, Class
)
from Students.models import Student

# ==========================================================================================#
# ========================             EXAMINATION MODULE          =========================#
OFFER_STATES=[
    ("OPENED","Opened"),
    ("CLOSED", "Closed")
]

class ExaminationCategory(models.Model):
    #Either CAT, EndTerm or End Year
    name = models.CharField(max_length=30)
    dor = models.DateTimeField(default=utils.timezone.now, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Exam Category'
        verbose_name_plural = 'Exams Categories'

class Grading(models.Model):
    leastmark = models.IntegerField(verbose_name='Lowest Marks')
    highmark = models.IntegerField(verbose_name='Highest Marks')
    remark = models.CharField(verbose_name='Remark', max_length=30)
    grade = models.IntegerField(unique=True)

    def __str__(self):
        return str(self.remark) +' '+ str(self.grade)
    
    class Meta:
        verbose_name = 'Grading'
        verbose_name_plural = 'Gradings'

class ExamResults(models.Model):
    studentno = models.ForeignKey(Student, on_delete=models.CASCADE)
    examcategory = models.ForeignKey(ExaminationCategory, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    marks = models.IntegerField()
    grade = models.ForeignKey(Grading, on_delete=models.CASCADE)
    year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Intake, on_delete=models.CASCADE)
    Class = models.ForeignKey(Class, on_delete=models.CASCADE)
    dor = models.DateTimeField(verbose_name='Date Registered', default=utils.timezone.now, blank = True, null=True)
    dom = models.DateTimeField(verbose_name='Date Modified', default=utils.timezone.now, blank = True, null=True)

    def __str__(self):
        return "Marks Entered"

    class Meta:
        verbose_name = 'Exam Result'
        verbose_name_plural = 'Exams Results'

class Deadlines(models.Model):
    examcategory = models.ForeignKey(ExaminationCategory, on_delete=models.CASCADE)
    openingTime = models.DateTimeField(verbose_name='Openning Offer', default=utils.timezone.now, blank = True, null=True)
    closingTime = models.DateTimeField(verbose_name='Closing Offer', default=utils.timezone.now, blank = True, null=True)
    state = models.CharField(choices=OFFER_STATES, max_length=30, blank=True, null = True, default="OPENED")

    def __str__(self):
        return self.state

    class Meta:
        verbose_name = 'Exam Deadline'
        verbose_name_plural = 'Exams Deadlines'

class ReportCard(models.Model):
    studentno = models.ForeignKey(Student, on_delete=models.CASCADE)
    year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    Class = models.ForeignKey(Class, on_delete=models.CASCADE)
    term = models.ForeignKey(Intake, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    cat = models.CharField(max_length=30, blank=True, null=True)
    endterm = models.CharField(max_length=30, blank=True, null=True)
    total = models.CharField(max_length=30)
    Grade = models.CharField(max_length=30)
    dor = models.DateTimeField(verbose_name='Date Registered', default=utils.timezone.now, blank = True, null=True)

    def __str__(self):
        return str(self.studentno) +" Reports"

    class Meta:
        verbose_name = 'Exam Report'
        verbose_name_plural = 'Exams Reports'
