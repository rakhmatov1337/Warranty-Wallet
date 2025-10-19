from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarrantyViewSet, CustomerWarrantyMeView
from .views_customer import CustomerWarrantyViewSet

# Separate routers to avoid conflicts
warranty_router = DefaultRouter()
warranty_router.register(r'', WarrantyViewSet, basename='warranty')

customer_warranty_router = DefaultRouter()
customer_warranty_router.register(r'', CustomerWarrantyViewSet, basename='customer-warranty')

urlpatterns = [
    # Customer's own warranties (from receipts) with receipt item details
    path('me/', CustomerWarrantyMeView.as_view(), name='warranty-me-list'),
    path('me/<int:pk>/', CustomerWarrantyMeView.as_view(), name='warranty-me-detail'),
    # Customer manually uploaded warranties
    path('customer/', include(customer_warranty_router.urls)),
    # Main warranty CRUD
    path('', include(warranty_router.urls)),
]
