# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid
from django.db import models  # type: ignore
from django.utils import timezone  # type: ignore

from Core.models import Course, Sponsor, Module, Term
from Students.models import Student

FEE_STATUS = [
    ("Overpaid", "Overpaid"),
    ("Cleared", "Cleared"),
    ("Not-Cleared", "Not-Cleared"),
]

PAYMENT_PLAN_CHOICES = [
    ('Daily', 'Daily'),
    ('Weekly', 'Weekly'),
    ('Monthly', 'Monthly'),
    ('Termly', 'Termly'),
    ('Semi-Annually', 'Semi-Annually'),
    ('Annually', 'Annually'),
]

# ==========================================================================================#
# ========================                FINANCE MODULE           =========================#

class AccessToken(models.Model):
    token = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.token

    class Meta:
        get_latest_by = 'created_at'

class BaseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

class PaymentMethod(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name

class Wallet(BaseModel):
    name = models.CharField(max_length=255)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    logo = models.ImageField(upload_to="brand/")
    paybill = models.CharField(max_length=30)
    cardNumber = models.CharField(max_length=30)
    cardHolder = models.CharField(max_length=30)
    account_number = models.CharField(max_length=30, blank=True, null= True)
    ccv = models.CharField(max_length=20, blank=True, null= True)
    expiry = models.DateField(blank=True, null=True)
    blocked = models.BooleanField(default=False, blank=True)
    bgClass = models.CharField(max_length=255, blank = True, null = True)
    
    def __str__(self):
        return self.name or self.account_number
      
class PriorityLevel(BaseModel):
    name = models.CharField(max_length=50)
    rank = models.PositiveSmallIntegerField()
 
    def __str__(self):
        return f"{self.name} ({self.rank}%)"

    class Meta:
        verbose_name = "Priority Level"
        verbose_name_plural = "Priority Levels"
        ordering = ['rank']

class Account(BaseModel):
    votehead = models.CharField(verbose_name='Vote Head', max_length=255)
    abbr = models.CharField(verbose_name='Abbreviation', max_length=25)
    priority = models.ForeignKey(PriorityLevel, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.votehead} ({self.priority})"

    class Meta:
        verbose_name = 'Fee Account'
        verbose_name_plural = 'Fee Accounts'

class FeeParticular(BaseModel):
    name = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    target = models.CharField(max_length=30, choices=[("Student", "Student"), ("Class","Class"), ("Course", "Course")], default="Course", blank=True, null=True)

    def __str__(self):
        return f"{self.account} #{self.amount}"

    class Meta:
        verbose_name = "Fee Particular"
        verbose_name_plural = "Fee Particulars"
        unique_together = ("name", "course", "module", "term")

class Invoice(BaseModel):
    inv_no = models.CharField(max_length=30)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='Student')
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    narration = models.ManyToManyField(FeeParticular, related_name='invoices')
    state = models.CharField(max_length=30, choices=[("Pending", "Pending"), ("Cleared", "Cleared")], default="Pending", blank=True, null=True)
    is_cleared = models.BooleanField(default=False)
    paid_amount = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"Invoice #{self.inv_no}"

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"

    def get_balance_due(self):
        return self.amount - self.paid_amount
  
class FeeStatus(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, verbose_name='Academic Year', on_delete=models.CASCADE)
    module = models.ForeignKey(Module, verbose_name='Module', on_delete=models.CASCADE)
    status = models.CharField(choices=FEE_STATUS, max_length=25)
    arrears = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.CharField(max_length = 40, blank = True, null = True)

    def __str__(self):
        return f"{self.student} {self.term} {self.module} {self.status} {self.arrears}"

    class Meta:
        verbose_name = "Fee Status"
        verbose_name_plural = "Fee Statuses"
  
class Receipt(BaseModel):
    trans_id = models.CharField(max_length=50)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='Student')
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    cashier = models.CharField(max_length=50)
    dop = models.DateTimeField(verbose_name='Date of Payment', default=timezone.now)
    narration = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Receipt #{self.pk}"

    class Meta:
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"

class ReceiptAllocation(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

class Transaction(BaseModel):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    account = models.ForeignKey(FeeParticular, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    running_balance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.account} #{self.amount}"

    class Meta:
        verbose_name = "Fee Transaction"
        verbose_name_plural = "Fee Transactions"
  
class PaymentAttempt(BaseModel):
    wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, null=True)
    ref_id = models.CharField(max_length=100, null=True, blank=True)
    merchant_request_id = models.CharField(max_length=50, unique=True)
    checkout_request_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payer_name = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=20, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'), ('Success', 'Success'), ('Failed', 'Failed')
    ], default='Pending')
    response_payload = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.checkout_request_id} - {self.status}"

    class Meta:
        verbose_name = "Payment Attempt"
        verbose_name_plural = "Payment Attempts"
  
class PaymentPlan(BaseModel):
    sponsor = models.OneToOneField(Sponsor, on_delete=models.CASCADE)
    plan = models.CharField(choices=PAYMENT_PLAN_CHOICES, max_length=20)
    datelastreminded = models.DateTimeField(auto_now=True, blank=True, null=True)
    datenextreminder = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.sponsor} Pays {self.plan}"

    class Meta:
        verbose_name = "Fee Payment Plan"
        verbose_name_plural = "Fee Payment Plans"
  