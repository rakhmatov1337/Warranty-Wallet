from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarrantyViewSet
from .views_customer import CustomerWarrantyViewSet

router = DefaultRouter()
router.register(r'', WarrantyViewSet, basename='warranty')
router.register(r'customer', CustomerWarrantyViewSet, basename='customer-warranty')

urlpatterns = [
    path('', include(router.urls)),
]
