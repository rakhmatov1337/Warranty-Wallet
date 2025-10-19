from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, PublicStoreListView, PublicStoreDetailView

router = DefaultRouter()
router.register(r'manage', StoreViewSet, basename='store')

urlpatterns = [
    # Public store APIs (no authentication required)
    path('list/', PublicStoreListView.as_view(), name='public-store-list'),
    path('detail/<int:pk>/', PublicStoreDetailView.as_view(), name='public-store-detail'),
    
    # Store management APIs (authentication required)
    path('', include(router.urls)),
]

