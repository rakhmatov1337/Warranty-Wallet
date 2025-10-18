from django.urls import path
from .views import (
    NotificationListView, NotificationMarkAsReadView,
    NotificationMarkAllAsReadView, NotificationStatsView
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('stats/', NotificationStatsView.as_view(), name='notification-stats'),
    path('<int:pk>/mark-as-read/', NotificationMarkAsReadView.as_view(), name='notification-mark-as-read'),
    path('mark-all-as-read/', NotificationMarkAllAsReadView.as_view(), name='notification-mark-all-as-read'),
]

