from django.contrib import admin #type:ignore
from .models import *
from django.urls import reverse #type:ignore
from django.utils.http import urlencode #type:ignore
from django.utils.html import format_html #type:ignore

@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ("account_number", "token", )

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", )

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("name", "payment_method", "cardNumber", "expiry", "blocked" )

@admin.register(PriorityLevel)
class PriorityLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "rank", )
    
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("votehead", "abbr", "priority", )
    
@admin.register(FeeParticular)
class FeeParticularAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "module", "term", "account", "amount", )
    
@admin.register(FeeStatus)
class FeeStatusAdmin(admin.ModelAdmin):
    list_display = ("student", "term", "module", "status", "arrears", )

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("trans_id", "student", "wallet", "term", "amount", )
    
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("receipt", "account", "amount", "running_balance", )
        
@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("wallet", "checkout_request_id", "amount", "status" )

@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = ("sponsor", "plan", "datelastreminded", )

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    readonly_fields = ('amount',)  # Make 'amount' read-only
    list_display = ('inv_no', 'student', 'term', 'amount')  # Optional: show it in list view
    filter_horizontal = ('narration',)  # Optional: better UI for ManyToMany fields
