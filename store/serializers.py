from rest_framework import serializers
from .models import Store
from accounts.serializers import UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class StoreSerializer(serializers.ModelSerializer):
    admins = UserSerializer(many=True, read_only=True)
    admin_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        write_only=True, 
        queryset=User.objects.filter(role='retailer'),
        source='admins'
    )
    
    class Meta:
        model = Store
        fields = ['id', 'name', 'image', 'phone_number', 'email', 'address', 'admins', 'admin_ids', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_image(self, value):
        """Validate store logo/image file size and type"""
        if not value:  # Allow null/empty
            return value
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum limit of 10MB. Your file is {value.size / (1024*1024):.2f}MB"
            )
        
        # Check file type (images only)
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: JPEG, PNG, GIF, WebP, SVG. Got: {value.content_type}"
            )
        
        return value

