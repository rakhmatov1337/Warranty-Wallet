from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarrantyViewSet
from .views_customer import CustomerWarrantyViewSet

# Separate routers to avoid conflicts
warranty_router = DefaultRouter()
warranty_router.register(r'', WarrantyViewSet, basename='warranty')

customer_warranty_router = DefaultRouter()
customer_warranty_router.register(r'', CustomerWarrantyViewSet, basename='customer-warranty')

urlpatterns = [
    path('customer/', include(customer_warranty_router.urls)),
    path('', include(warranty_router.urls)),
]
