from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Notification(models.Model):
    """
    Notification model for system-wide notifications to users
    """
    
    NOTIFICATION_TYPES = [
        ('WELCOME', 'Welcome Message'),
        ('NEW_RECEIPT', 'New Receipt'),
        ('NEW_CLAIM', 'New Claim'),
        ('CLAIM_STATUS_UPDATE', 'Claim Status Updated'),
        ('CLAIM_NOTE_ADDED', 'Claim Note Added'),
        ('CLAIM_ATTACHMENT_ADDED', 'Claim Attachment Added'),
        ('WARRANTY_EXPIRING', 'Warranty Expiring Soon'),
        ('WARRANTY_EXPIRED', 'Warranty Expired'),
    ]
    
    RELATED_OBJECT_TYPES = [
        ('Receipt', 'Receipt'),
        ('Claim', 'Claim'),
        ('Warranty', 'Warranty'),
        ('ReceiptItem', 'Receipt Item'),
    ]
    
    # Recipient of the notification
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    # User who performed the action (nullable for system notifications)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='actions')
    
    # Notification details
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Related object (for linking back to the object)
    related_object_type = models.CharField(max_length=50, choices=RELATED_OBJECT_TYPES, null=True, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    @property
    def link(self):
        """Generate deep link for mobile app or web URL"""
        if self.related_object_type and self.related_object_id:
            if self.related_object_type == 'Receipt':
                return f'/receipts/{self.related_object_id}'
            elif self.related_object_type == 'Claim':
                return f'/claims/{self.related_object_id}'
            elif self.related_object_type == 'Warranty':
                return f'/warranties/{self.related_object_id}'
        return None
