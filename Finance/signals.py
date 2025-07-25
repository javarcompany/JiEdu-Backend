from django.db.models.signals import m2m_changed, post_save #type: ignore
from django.dispatch import receiver #type: ignore
from decimal import Decimal

from .models import Invoice
from .fee_manager import FeeManager

@receiver(m2m_changed, sender=Invoice.narration.through)
def update_invoice_amount(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        total = sum(item.amount for item in instance.narration.all())
        instance.amount = total
        instance.save(update_fields=["amount"])

        if action == "post_add":
            
            student = instance.student
            term = instance.term

            manager = FeeManager(student.regno, term.id)
            manager.update_status(receipt = instance.inv_no, amount_paid = Decimal(-instance.amount))
