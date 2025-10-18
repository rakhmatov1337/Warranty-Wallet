from django.urls import path
from .views import AnalyticsOverview, RetailerAIInsights

urlpatterns = [
    path('', AnalyticsOverview.as_view(), name='analytics-overview'),
    path('ai-insights/', RetailerAIInsights.as_view(), name='ai-insights'),
]
