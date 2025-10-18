from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReceiptViewSet, ReceiptItemsWithoutWarrantyView, StoreCustomersView,
    CustomerReceiptsView, CustomerReceiptDetailView, CustomerHomeView
)

router = DefaultRouter()
router.register(r'', ReceiptViewSet, basename='receipt')

urlpatterns = [
    path('items/without-warranty/', ReceiptItemsWithoutWarrantyView.as_view(), name='receipt-items-without-warranty'),
    path('customers/', StoreCustomersView.as_view(), name='store-customers'),
    # Customer-facing endpoints
    path('my/', CustomerReceiptsView.as_view(), name='customer-receipts'),
    path('my/<int:pk>/', CustomerReceiptDetailView.as_view(), name='customer-receipt-detail'),
    path('', include(router.urls)),
]
