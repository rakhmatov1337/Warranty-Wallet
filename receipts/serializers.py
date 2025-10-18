from rest_framework import serializers
from .models import Receipt, ReceiptItem
from store.serializers import StoreSerializer
from accounts.serializers import UserSerializer
from store.models import Store
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class ReceiptItemSerializer(serializers.ModelSerializer):
    item_total = serializers.ReadOnlyField()
    
    class Meta:
        model = ReceiptItem
        fields = [
            'id', 'product_name', 'model', 'serial_number', 'price', 'quantity', 'item_total',
            'color', 'imei', 'storage', 'warranty_coverage', 'warranty_expiry'
        ]


class ReceiptItemWithReceiptSerializer(serializers.ModelSerializer):
    """Serializer for receipt items that includes receipt details"""
    item_total = serializers.ReadOnlyField()
    receipt_number = serializers.CharField(source='receipt.receipt_number', read_only=True)
    receipt_date = serializers.DateField(source='receipt.date', read_only=True)
    store_name = serializers.CharField(source='receipt.store.name', read_only=True)
    customer_email = serializers.CharField(source='receipt.customer.email', read_only=True)
    has_warranty = serializers.SerializerMethodField()
    
    class Meta:
        model = ReceiptItem
        fields = [
            'id', 'receipt', 'receipt_number', 'receipt_date', 'store_name', 'customer_email',
            'product_name', 'model', 'serial_number', 'price', 'quantity', 'item_total',
            'color', 'imei', 'storage', 'warranty_coverage', 'warranty_expiry', 'has_warranty'
        ]
    
    def get_has_warranty(self, obj):
        """Check if this item has a warranty"""
        return hasattr(obj, 'warranty')


class ReceiptSerializer(serializers.ModelSerializer):
    items = ReceiptItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    store_details = StoreSerializer(source='store', read_only=True)
    retailer_details = UserSerializer(source='retailer', read_only=True)
    customer_details = UserSerializer(source='customer', read_only=True)
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_number', 'store', 'store_details', 'retailer', 'retailer_details', 
            'customer', 'customer_details', 'total', 'date', 'time', 
            'payment_method', 'notes', 'items', 'items_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['receipt_number', 'created_at', 'updated_at']
    
    def get_items_count(self, obj):
        return obj.items.count()


class ReceiptCreateSerializer(serializers.ModelSerializer):
    items = ReceiptItemSerializer(many=True)
    store_id = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        source='store',
        write_only=True
    )
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='customer'),
        source='customer',
        write_only=True
    )
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Receipt
        fields = [
            'store_id', 'customer_id', 'total', 
            'date', 'time', 'payment_method', 'notes', 'items'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If user is retailer, limit to stores they manage
        if hasattr(self, 'context') and 'request' in self.context:
            user = self.context['request'].user
            if user.role == 'retailer':
                self.fields['store_id'].queryset = user.managed_stores.all()
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        # Calculate total from items
        from decimal import Decimal
        total = Decimal('0.00')
        for item_data in items_data:
            item_total = item_data['price'] * item_data.get('quantity', 1)
            total += item_total
        
        # Set calculated total
        validated_data['total'] = total
        
        # Set retailer from request user
        validated_data['retailer'] = self.context['request'].user
        receipt = Receipt.objects.create(**validated_data)
        
        for item_data in items_data:
            ReceiptItem.objects.create(receipt=receipt, **item_data)
        
        return receipt


# ==================== CUSTOMER-FACING SERIALIZERS ====================

class CustomerReceiptItemSerializer(serializers.ModelSerializer):
    """Simplified receipt item for customer mobile view"""
    item_total = serializers.ReadOnlyField()
    has_warranty = serializers.SerializerMethodField()
    warranty_days_left = serializers.SerializerMethodField()
    
    class Meta:
        model = ReceiptItem
        fields = [
            'id', 'product_name', 'model', 'price', 'quantity', 'item_total',
            'warranty_expiry', 'has_warranty', 'warranty_days_left'
        ]
    
    def get_has_warranty(self, obj):
        return hasattr(obj, 'warranty')
    
    def get_warranty_days_left(self, obj):
        if obj.warranty_expiry:
            from django.utils import timezone
            today = timezone.now().date()
            if obj.warranty_expiry >= today:
                return (obj.warranty_expiry - today).days
        return None


class CustomerReceiptListSerializer(serializers.ModelSerializer):
    """Receipt list for customer mobile app"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    main_product = serializers.SerializerMethodField()
    warranty_status = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_number', 'store_name', 'main_product',
            'total', 'date', 'warranty_status', 'days_left'
        ]
    
    def get_main_product(self, obj):
        """Get the first/main product from receipt"""
        first_item = obj.items.first()
        return first_item.product_name if first_item else 'N/A'
    
    def get_warranty_status(self, obj):
        """Determine overall warranty status"""
        from django.utils import timezone
        today = timezone.now().date()
        
        # Check all items with warranty expiry
        items_with_warranty = obj.items.filter(warranty_expiry__isnull=False)
        if not items_with_warranty.exists():
            return 'No Warranty'
        
        # Check for expired
        expired = items_with_warranty.filter(warranty_expiry__lt=today)
        if expired.exists() and expired.count() == items_with_warranty.count():
            return 'Expired'
        
        # Check for expiring soon (within 30 days)
        expiring_soon_date = today + timedelta(days=30)
        expiring_soon = items_with_warranty.filter(
            warranty_expiry__gte=today,
            warranty_expiry__lte=expiring_soon_date
        )
        if expiring_soon.exists():
            return 'Expiring Soon'
        
        # Otherwise active
        return 'Active'
    
    def get_days_left(self, obj):
        """Get minimum days left from all items"""
        from django.utils import timezone
        today = timezone.now().date()
        
        items_with_warranty = obj.items.filter(warranty_expiry__isnull=False, warranty_expiry__gte=today)
        if items_with_warranty.exists():
            # Get the item with nearest expiry
            nearest = items_with_warranty.order_by('warranty_expiry').first()
            return (nearest.warranty_expiry - today).days
        return 0


class CustomerReceiptWarrantySerializer(serializers.Serializer):
    """Warranty information for customer receipt detail"""
    id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source='receipt_item.product_name', read_only=True)
    product_model = serializers.CharField(source='receipt_item.model', read_only=True)
    warranty_status = serializers.SerializerMethodField()
    coverage_period = serializers.SerializerMethodField()
    purchase_date = serializers.DateField(read_only=True)
    expiry_date = serializers.DateField(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    can_claim = serializers.SerializerMethodField()
    
    def get_warranty_status(self, obj):
        """Get warranty status (Active/Expired)"""
        return obj.status
    
    def get_coverage_period(self, obj):
        """Get coverage period in readable format"""
        if obj.coverage_period_months >= 12:
            years = obj.coverage_period_months // 12
            return f"{years} Year{'s' if years > 1 else ''}"
        return f"{obj.coverage_period_months} Month{'s' if obj.coverage_period_months > 1 else ''}"
    
    def get_days_remaining(self, obj):
        """Get days remaining"""
        return obj.remaining_days
    
    def get_can_claim(self, obj):
        """Check if customer can file a claim"""
        return obj.status == 'Active'


class CustomerReceiptDetailSerializer(serializers.ModelSerializer):
    """Detailed receipt view for customer"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_address = serializers.CharField(source='store.address', read_only=True)
    items = CustomerReceiptItemSerializer(many=True, read_only=True)
    warranties = serializers.SerializerMethodField()
    warranty_status = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    can_claim = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'receipt_number', 'store_name', 'store_address',
            'total', 'date', 'time', 'payment_method',
            'items', 'warranties', 'warranty_status', 'days_remaining', 'can_claim'
        ]
    
    def get_warranties(self, obj):
        """Get all warranties for items in this receipt"""
        from warranties.models import Warranty
        
        # Get all warranties for items in this receipt
        warranties = Warranty.objects.filter(
            receipt_item__receipt=obj
        ).select_related('receipt_item')
        
        return CustomerReceiptWarrantySerializer(warranties, many=True).data
    
    def get_warranty_status(self, obj):
        """Get overall warranty status"""
        serializer = CustomerReceiptListSerializer()
        return serializer.get_warranty_status(obj)
    
    def get_days_remaining(self, obj):
        """Get days remaining"""
        serializer = CustomerReceiptListSerializer()
        return serializer.get_days_left(obj)
    
    def get_can_claim(self, obj):
        """Check if customer can start a claim"""
        from warranties.models import Warranty
        
        # Can claim if there's at least one active warranty
        active_warranties = Warranty.objects.filter(
            receipt_item__receipt=obj,
            expiry_date__gte=timezone.now().date()
        ).exists()
        
        return active_warranties
    