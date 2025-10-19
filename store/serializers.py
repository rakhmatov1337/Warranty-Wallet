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
        fields = [
            'id', 'name', 'image', 'phone_number', 'email', 'address', 
            'latitude', 'longitude', 'is_verified', 'admins', 'admin_ids', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_verified']
    
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


class StoreListSerializer(serializers.ModelSerializer):
    """
    Public serializer for store list with map URLs and success rate
    """
    image_url = serializers.SerializerMethodField()
    yandex_map_url = serializers.SerializerMethodField()
    google_map_url = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    total_claims = serializers.SerializerMethodField()
    approved_claims = serializers.SerializerMethodField()
    rejected_claims = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'image', 'image_url', 'phone_number', 'email', 
            'address', 'latitude', 'longitude', 'is_verified',
            'yandex_map_url', 'google_map_url',
            'success_rate', 'total_claims', 'approved_claims', 'rejected_claims',
            'created_at'
        ]
    
    def get_image_url(self, obj):
        """Get full URL for store image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_yandex_map_url(self, obj):
        """Generate Yandex Maps route URL"""
        if obj.latitude and obj.longitude:
            # Yandex Maps route URL format
            return f"https://yandex.com/maps/?rtext=~{obj.latitude},{obj.longitude}&rtt=auto"
        return None
    
    def get_google_map_url(self, obj):
        """Generate Google Maps route URL"""
        if obj.latitude and obj.longitude:
            # Google Maps route URL format
            return f"https://www.google.com/maps/dir/?api=1&destination={obj.latitude},{obj.longitude}"
        return None
    
    def get_total_claims(self, obj):
        """Get total number of claims for this store"""
        from claims.models import Claim
        return Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj
        ).exclude(status='In Review').count()
    
    def get_approved_claims(self, obj):
        """Get number of approved claims"""
        from claims.models import Claim
        return Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj,
            status='Approved'
        ).count()
    
    def get_rejected_claims(self, obj):
        """Get number of rejected claims"""
        from claims.models import Claim
        return Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj,
            status='Rejected'
        ).count()
    
    def get_success_rate(self, obj):
        """
        Calculate success rate (approval rate) for the store
        Success rate = (Approved claims / Total resolved claims) * 100
        """
        from claims.models import Claim
        
        # Get total resolved claims (Approved + Rejected)
        total_resolved = Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj
        ).exclude(status='In Review').count()
        
        if total_resolved == 0:
            return None  # No claims yet
        
        # Get approved claims
        approved = Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj,
            status='Approved'
        ).count()
        
        # Calculate success rate
        success_rate = (approved / total_resolved) * 100
        return round(success_rate, 1)


class StoreDetailSerializer(serializers.ModelSerializer):
    """
    Public serializer for store detail with map URLs, admin info, and success rate
    """
    image_url = serializers.SerializerMethodField()
    yandex_map_url = serializers.SerializerMethodField()
    google_map_url = serializers.SerializerMethodField()
    yandex_map_embed_url = serializers.SerializerMethodField()
    google_map_embed_url = serializers.SerializerMethodField()
    admin_count = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    total_claims = serializers.SerializerMethodField()
    approved_claims = serializers.SerializerMethodField()
    rejected_claims = serializers.SerializerMethodField()
    pending_claims = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'image', 'image_url', 'phone_number', 'email', 
            'address', 'latitude', 'longitude', 'is_verified',
            'yandex_map_url', 'google_map_url',
            'yandex_map_embed_url', 'google_map_embed_url',
            'admin_count', 'success_rate', 'total_claims', 
            'approved_claims', 'rejected_claims', 'pending_claims',
            'created_at', 'updated_at'
        ]
    
    def get_image_url(self, obj):
        """Get full URL for store image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def get_yandex_map_url(self, obj):
        """Generate Yandex Maps route URL"""
        if obj.latitude and obj.longitude:
            return f"https://yandex.com/maps/?rtext=~{obj.latitude},{obj.longitude}&rtt=auto"
        return None
    
    def get_google_map_url(self, obj):
        """Generate Google Maps route URL"""
        if obj.latitude and obj.longitude:
            return f"https://www.google.com/maps/dir/?api=1&destination={obj.latitude},{obj.longitude}"
        return None
    
    def get_yandex_map_embed_url(self, obj):
        """Generate Yandex Maps embed URL for iframe"""
        if obj.latitude and obj.longitude:
            return f"https://yandex.com/map-widget/v1/?ll={obj.longitude},{obj.latitude}&z=16&pt={obj.longitude},{obj.latitude},pm2rdm"
        return None
    
    def get_google_map_embed_url(self, obj):
        """Generate Google Maps embed URL for iframe"""
        if obj.latitude and obj.longitude:
            return f"https://www.google.com/maps/embed/v1/place?key=YOUR_API_KEY&q={obj.latitude},{obj.longitude}&zoom=16"
        return None
    
    def get_admin_count(self, obj):
        """Get number of store admins"""
        return obj.admins.count()
    
    def get_total_claims(self, obj):
        """Get total number of claims for this store"""
        from claims.models import Claim
        return Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj
        ).exclude(status='In Review').count()
    
    def get_approved_claims(self, obj):
        """Get number of approved claims"""
        from claims.models import Claim
        return Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj,
            status='Approved'
        ).count()
    
    def get_rejected_claims(self, obj):
        """Get number of rejected claims"""
        from claims.models import Claim
        return Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj,
            status='Rejected'
        ).count()
    
    def get_pending_claims(self, obj):
        """Get number of pending (In Review) claims"""
        from claims.models import Claim
        return Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj,
            status='In Review'
        ).count()
    
    def get_success_rate(self, obj):
        """
        Calculate success rate (approval rate) for the store
        Success rate = (Approved claims / Total resolved claims) * 100
        """
        from claims.models import Claim
        
        # Get total resolved claims (Approved + Rejected)
        total_resolved = Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj
        ).exclude(status='In Review').count()
        
        if total_resolved == 0:
            return None  # No claims yet
        
        # Get approved claims
        approved = Claim.objects.filter(
            warranty__receipt_item__receipt__store=obj,
            status='Approved'
        ).count()
        
        # Calculate success rate
        success_rate = (approved / total_resolved) * 100
        return round(success_rate, 1)

