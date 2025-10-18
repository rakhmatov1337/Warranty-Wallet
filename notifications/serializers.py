from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    actor_email = serializers.CharField(source='actor.email', read_only=True)
    link = serializers.ReadOnlyField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'related_object_type', 'related_object_id', 'link',
            'actor', 'actor_name', 'actor_email',
            'is_read', 'created_at', 'read_at', 'time_ago'
        ]
        read_only_fields = ['actor', 'created_at', 'read_at']
    
    def get_actor_name(self, obj):
        """Get actor's full name"""
        if obj.actor:
            return obj.actor.full_name
        return 'System'
    
    def get_time_ago(self, obj):
        """Calculate human-readable time ago"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        time_diff = now - obj.created_at
        
        if time_diff < timedelta(minutes=1):
            return 'Just now'
        elif time_diff < timedelta(hours=1):
            minutes = int(time_diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif time_diff < timedelta(days=1):
            hours = int(time_diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif time_diff < timedelta(days=7):
            days = time_diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return obj.created_at.strftime('%b %d, %Y')

