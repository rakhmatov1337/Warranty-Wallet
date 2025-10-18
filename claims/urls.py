from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClaimViewSet, CustomerClaimCreateView, CustomerClaimListView, 
    CustomerClaimDetailView, CustomerClaimAddAttachmentView
)

router = DefaultRouter()
router.register(r'', ClaimViewSet, basename='claim')

urlpatterns = [
    # Customer-facing endpoints
    path('my/', CustomerClaimListView.as_view(), name='customer-claims'),
    path('my/create/', CustomerClaimCreateView.as_view(), name='customer-claim-create'),
    path('my/<int:pk>/', CustomerClaimDetailView.as_view(), name='customer-claim-detail'),
    path('my/<int:pk>/add-attachment/', CustomerClaimAddAttachmentView.as_view(), name='customer-claim-add-attachment'),
    path('', include(router.urls)),
]
