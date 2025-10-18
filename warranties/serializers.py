from rest_framework import serializers
from .models import Warranty, CustomerWarranty
from receipts.serializers import ReceiptSerializer, ReceiptItemSerializer
from receipts.models import ReceiptItem
from accounts.serializers import UserSerializer
from store.serializers import StoreSerializer

class WarrantyDetailSerializer(serializers.ModelSerializer):
    # Receipt information with all items (including product details)
    receipt_info = serializers.SerializerMethodField()
    
    # Customer information
    customer_info = UserSerializer(source='customer', read_only=True)
    
    # Store/Purchase information
    store_info = StoreSerializer(source='store', read_only=True)
    
    # Calculated fields
    remaining_days = serializers.ReadOnlyField()
    coverage_value = serializers.ReadOnlyField()
    claims_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Warranty
        fields = [
            'id', 'status', 'remaining_days', 'coverage_value', 'claims_count',
            # Warranty coverage
            'coverage_period_months', 'provider', 'coverage_terms', 'purchase_date', 'expiry_date',
            # Related info
            'receipt_info', 'customer_info', 'store_info',
            'created_at', 'updated_at'
        ]
    
    def get_receipt_info(self, obj):
        """Get receipt with all items (items include product details like color, imei, storage)"""
        receipt = obj.receipt
        return {
            'id': receipt.id,
            'receipt_number': receipt.receipt_number,
            'date': receipt.date,
            'time': receipt.time,
            'total': receipt.total,
            'payment_method': receipt.payment_method,
            'notes': receipt.notes,
            'items': ReceiptItemSerializer(receipt.items.all(), many=True).data
        }


class WarrantyListSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='receipt_item.product_name', read_only=True)
    remaining_days = serializers.ReadOnlyField()
    coverage_value = serializers.ReadOnlyField()
    claims_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Warranty
        fields = [
            'id', 'product_name', 'status', 'remaining_days', 
            'coverage_value', 'claims_count', 'expiry_date', 'created_at'
        ]


class WarrantyCreateSerializer(serializers.ModelSerializer):
    receipt_item_id = serializers.PrimaryKeyRelatedField(
        queryset=ReceiptItem.objects.all(),
        source='receipt_item',
        write_only=True
    )
    purchase_date = serializers.DateField(read_only=True)
    expiry_date = serializers.DateField(read_only=True)
    status = serializers.ReadOnlyField()
    
    class Meta:
        model = Warranty
        fields = [
            'receipt_item_id',
            'coverage_period_months', 'provider', 'coverage_terms',
            'purchase_date', 'expiry_date', 'status'
        ]
    
    def create(self, validated_data):
        """
        Automatically set purchase_date from receipt date
        and calculate expiry_date based on coverage_period_months
        """
        from dateutil.relativedelta import relativedelta
        
        receipt_item = validated_data['receipt_item']
        
        # Set purchase_date from receipt date
        validated_data['purchase_date'] = receipt_item.receipt.date
        
        # Calculate expiry_date based on coverage period
        coverage_months = validated_data['coverage_period_months']
        validated_data['expiry_date'] = receipt_item.receipt.date + relativedelta(months=coverage_months)
        
        return super().create(validated_data)


# ==================== CUSTOMER WARRANTY SERIALIZERS ====================

class CustomerWarrantySerializer(serializers.ModelSerializer):
    """Serializer for customer-uploaded warranties"""
    warranty_image_url = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()
    
    class Meta:
        model = CustomerWarranty
        fields = [
            'id', 'product_name', 'expiry_date', 'warranty_image', 
            'warranty_image_url', 'notes', 'is_active', 'days_remaining', 
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_warranty_image_url(self, obj):
        """Get full URL for warranty image"""
        if obj.warranty_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.warranty_image.url)
            return obj.warranty_image.url
        return None


class CustomerWarrantyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating customer warranties"""
    
    class Meta:
        model = CustomerWarranty
        fields = ['product_name', 'expiry_date', 'warranty_image', 'notes']
    
    def create(self, validated_data):
        """Set customer from request user"""
        validated_data['customer'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate_expiry_date(self, value):
        """Validate expiry date is in the future"""
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Expiry date must be in the future")
        return value
    
    def validate_warranty_image(self, value):
        """Validate warranty image file size and type"""
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum limit of 10MB. Your file is {value.size / (1024*1024):.2f}MB"
            )
        
        # Check file type (images only)
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: JPEG, PNG, GIF, WebP. Got: {value.content_type}"
            )
        
        return value


class CustomerWarrantyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating customer warranties"""
    
    class Meta:
        model = CustomerWarranty
        fields = ['product_name', 'expiry_date', 'warranty_image', 'notes']
    
    def validate_expiry_date(self, value):
        """Validate expiry date is in the future"""
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Expiry date must be in the future")
        return value
    
    def validate_warranty_image(self, value):
        """Validate warranty image file size and type"""
        if not value:  # Allow null when not updating image
            return value
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds maximum limit of 10MB. Your file is {value.size / (1024*1024):.2f}MB"
            )
        
        # Check file type (images only)
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: JPEG, PNG, GIF, WebP. Got: {value.content_type}"
            )
        
        return value
