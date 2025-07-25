from rest_framework import serializers #type: ignore
from .models import *
from django.db.models import Sum #type: ignore
from decimal import Decimal

class AccessTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessToken
        fields = '__all__'

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'

class WalletSerializer(serializers.ModelSerializer):
    latest_transaction = serializers.SerializerMethodField()
    total_transactions = serializers.SerializerMethodField()
    wallet_type = serializers.CharField(source='payment_method.name', read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = '__all__'

    def get_latest_transaction(self, obj):
        latest = Receipt.objects.filter(wallet=obj).order_by('-created_at').first()
        if latest:
            return {
                "amount": str(latest.amount),
                "sender": latest.student.get_full_name() if latest.student else "Unknown",
                "date": latest.created_at.strftime("%d %b %Y, %I:%M %p"),
            }
        return None

    def get_total_transactions(self, obj):
        return Receipt.objects.filter(wallet=obj).count()
    
    def get_balance(self, obj):
        total = Receipt.objects.filter(wallet=obj).aggregate(sum=Sum("amount"))["sum"] or Decimal("0.00")
        return str(total)

class PriorityLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorityLevel
        fields = '__all__'

class AccountSerializer(serializers.ModelSerializer):
        
    priority_name = serializers.CharField(source='priority.name', read_only=True)
    priority_level = serializers.CharField(source='priority.rank', read_only=True)

    class Meta:
        model = Account
        fields = '__all__'

class FeeParticularSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.abbr', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)
    account_name = serializers.CharField(source='account.votehead', read_only=True)
    year_name = serializers.CharField(source='term.year.name', read_only=True)
    intake_name = serializers.CharField(source='term.name.name', read_only=True)

    class Meta:
        model = FeeParticular
        fields = '__all__'

class FeeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeStatus
        fields = '__all__'

class ReceiptSerializer(serializers.ModelSerializer):
    fname = serializers.CharField(source='student.fname', read_only=True)
    mname = serializers.CharField(source='student.mname', read_only=True)
    sname = serializers.CharField(source='student.sname', read_only=True)
    regno = serializers.CharField(source='student.regno', read_only=True)
    year_name = serializers.CharField(source='term.year.name', read_only=True)
    intake_name = serializers.CharField(source='term.name.name', read_only=True)
    wallet_name = serializers.CharField(source='wallet.name', read_only=True)
    wallet_type = serializers.CharField(source='wallet.paymethod.name', read_only=True)
    passport = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = '__all__'

    def get_passport(self, obj):
        request = self.context.get('request')
        if obj.student and obj.student.passport:
            passport_url = obj.student.passport.url
            return request.build_absolute_uri(passport_url) if request else passport_url
        return None

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = '__all__'

class PaymentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = '__all__'
