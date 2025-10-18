from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer
from django.db.models import Q


class NotificationListView(generics.ListAPIView):
    """
    List all notifications for the authenticated user
    Supports filtering by is_read
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Notification.objects.filter(user=user)
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read', None)
        if is_read is not None:
            if is_read.lower() == 'false':
                queryset = queryset.filter(is_read=False)
            elif is_read.lower() == 'true':
                queryset = queryset.filter(is_read=True)
        
        # Filter by notification type
        notification_type = self.request.query_params.get('type', None)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return queryset.select_related('actor')
    
    def list(self, request, *args, **kwargs):
        """Include unread count in response"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get unread count
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['unread_count'] = unread_count
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'unread_count': unread_count,
            'results': serializer.data
        })


class NotificationMarkAsReadView(APIView):
    """
    Mark a specific notification as read
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.mark_as_read()
            serializer = NotificationSerializer(notification)
            return Response(serializer.data)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllAsReadView(APIView):
    """
    Mark all notifications as read for the authenticated user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        from django.utils import timezone
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({
            'message': f'{count} notifications marked as read',
            'count': count
        })


class NotificationStatsView(APIView):
    """
    Get notification statistics for the authenticated user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get counts
        total = Notification.objects.filter(user=user).count()
        unread = Notification.objects.filter(user=user, is_read=False).count()
        
        # Get counts by type (unread only)
        receipts_count = Notification.objects.filter(
            user=user,
            is_read=False,
            notification_type='NEW_RECEIPT'
        ).count()
        
        claims_count = Notification.objects.filter(
            user=user,
            is_read=False,
            notification_type__in=['NEW_CLAIM', 'CLAIM_STATUS_UPDATE', 'CLAIM_NOTE_ADDED', 'CLAIM_ATTACHMENT_ADDED']
        ).count()
        
        warranty_count = Notification.objects.filter(
            user=user,
            is_read=False,
            notification_type__in=['WARRANTY_EXPIRING', 'WARRANTY_EXPIRED']
        ).count()
        
        return Response({
            'total': total,
            'unread': unread,
            'by_category': {
                'receipts': receipts_count,
                'claims': claims_count,
                'warranties': warranty_count
            }
        })
