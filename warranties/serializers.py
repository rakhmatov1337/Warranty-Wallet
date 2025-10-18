from rest_framework import serializers
from .models import Warranty
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
