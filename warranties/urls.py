from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarrantyViewSet

router = DefaultRouter()
router.register(r'', WarrantyViewSet, basename='warranty')

urlpatterns = [
    path('', include(router.urls)),
]
