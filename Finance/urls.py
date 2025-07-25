from django.urls import path, include  #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from .views import *

router = DefaultRouter()
router.register(r'accesstokens', AccessTokenViewSet, basename='accesstoken')
router.register(r'paymentmethods', PaymentMethodViewSet, basename='paymentmethod')
router.register(r'wallets', WalletViewSet, basename='wallets')
router.register(r'prioritylevel', PriorityLevelViewSet, basename='prioritylevel')
router.register(r'accounts', AccountViewSet, basename='accounts')
router.register(r'feeparticular', FeeParticularViewSet, basename='feeparticular')
router.register(r'feestatus', FeeStatusViewSet, basename='feestatus')
router.register(r'receipts', ReceiptViewSet, basename='receipts')
router.register(r'transaction', TransactionViewSet, basename='transaction')
router.register(r'paymentattempt', PaymentAttemptViewSet, basename='paymentattempt')
router.register(r'paymentplan', PaymentPlanViewSet, basename='paymentplan')

urlpatterns = [
    path('api/', include(router.urls)),
    path('bank/payment/webhook/', bank_payment_webhook, name='bank_payment_webhook'),
    path("api/payments/mpesa-stk/", request_payment, name="mpesa-stk"),
    path("api/payments/stk-status/", check_stk_status, name="mpesa-stk"),
    path("api/payments/stk-callback/", mpesa_c2b_confirmation, name = "stk-callback"),
    path('api/dashboard/kpi/', kpi_dashboard, name = "kpi"),
    path('api/statement/', generate_statement, name = "statements"),
    path('api/logs/', generate_logs, name = "logs"),
    path('api/student-receipts/', student_receipts, name = "receipts"),
    path('api/fee-structure/', fee_structure, name = "fee-structure"),
    path('api/fetch-reciept-summary/', reciept_summary, name= "fetch-reciept-summary"),
    path('api/fetch-reciepts/', view_receipts, name= "fetch-reciepts"),
    path('api/fetch-course-invoices/', view_course_invoices, name= "fetch-invoices"),
    path('api/class-income-statement/', class_income_statement, name = "class-income-statement"),
    path('api/class-student-breakdown/', class_student_breakdown, name = "class-student-breakdown"),
    path('api/institution-fee-summary/', institution_fee_summary, name = "institution-fee-summary"),
    path("api/institution-fee-trend/", InstitutionFeeTrendAPIView.as_view(), name="institution-fee-trend"),
    path("api/institution-monthly-fee-summary/", InstitutionMonthlyFeeSummary.as_view(), name="institution-monthly-fee-trend"),
    path("api/predict-fee-payments/", predict_fee_payments, name = "predict-fee"),


    # Equity
    path('api/equity/payment-callback/', equity_payment_callback),

]
