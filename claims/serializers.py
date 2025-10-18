from rest_framework import serializers
from .models import Claim, ClaimNote, ClaimAttachment
from warranties.serializers import WarrantyListSerializer
from warranties.models import Warranty
from accounts.serializers import UserSerializer


class ClaimNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_email = serializers.CharField(source='author.email', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)
    
    class Meta:
        model = ClaimNote
        fields = ['id', 'content', 'author', 'author_name', 'author_email', 'author_role', 'created_at']
        read_only_fields = ['author', 'created_at']
    
    def get_author_name(self, obj):
        """Get retailer's full name, fallback to email or username"""
        if obj.author:
            full_name = obj.author.get_full_name()
            if full_name:
                return full_name
            return obj.author.email or obj.author.username
        return 'Unknown'


class ClaimAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    uploaded_by_email = serializers.CharField(source='uploaded_by.email', read_only=True)
    file_size_display = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ClaimAttachment
        fields = [
            'id', 'file', 'file_name', 'file_size', 'file_size_display',
            'file_url', 'uploaded_by', 'uploaded_by_name', 'uploaded_by_email', 'uploaded_at'
        ]
        read_only_fields = ['file_name', 'file_size', 'uploaded_by', 'uploaded_at']
    
    def get_uploaded_by_name(self, obj):
        """Get uploader's full name, fallback to email or username"""
        if obj.uploaded_by:
            full_name = obj.uploaded_by.get_full_name()
            if full_name:
                return full_name
            return obj.uploaded_by.email or obj.uploaded_by.username
        return 'Unknown'
    
    def get_file_url(self, obj):
        """Get the file URL"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class ClaimListSerializer(serializers.ModelSerializer):
    """Serializer for list view"""
    product_name = serializers.ReadOnlyField()
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    assigned_to_email = serializers.CharField(source='assigned_to.email', read_only=True)
    warranty_id = serializers.CharField(source='warranty.id', read_only=True)
    
    class Meta:
        model = Claim
        fields = [
            'id', 'claim_number', 'warranty', 'warranty_id', 'product_name',
            'issue_summary', 'category', 'priority', 'status',
            'assigned_to_email', 'customer_email',
            'estimated_cost', 'actual_cost', 'submitted_at', 'updated_at'
        ]


class ClaimDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with all related data"""
    warranty_details = WarrantyListSerializer(source='warranty', read_only=True)
    customer_details = UserSerializer(source='customer', read_only=True)
    retailer_details = UserSerializer(source='retailer', read_only=True)
    assigned_to_details = UserSerializer(source='assigned_to', read_only=True)
    created_by_details = UserSerializer(source='created_by', read_only=True)
    product_name = serializers.ReadOnlyField()
    notes = ClaimNoteSerializer(many=True, read_only=True)
    attachments = ClaimAttachmentSerializer(many=True, read_only=True)
    
    # Product information from warranty
    product_model = serializers.CharField(source='warranty.receipt_item.model', read_only=True)
    serial_number = serializers.CharField(source='warranty.receipt_item.serial_number', read_only=True)
    purchase_date = serializers.DateField(source='warranty.purchase_date', read_only=True)
    
    class Meta:
        model = Claim
        fields = [
            'id', 'claim_number', 'warranty', 'warranty_details',
            'issue_summary', 'detailed_description', 'category',
            'priority', 'status', 'assigned_to_details',
            'estimated_cost', 'actual_cost',
            'customer_details', 'retailer_details', 'created_by_details',
            'product_name', 'product_model', 'serial_number', 'purchase_date',
            'notes', 'attachments',
            'submitted_at', 'updated_at'
        ]


class ClaimCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating claims"""
    
    class Meta:
        model = Claim
        fields = [
            'warranty_id', 'issue_summary', 'detailed_description',
            'category', 'priority'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from warranties.models import Warranty
        
        # Create the warranty_id field dynamically
        if 'request' in self.context:
            user = self.context['request'].user
            if user.role == 'customer':
                # Customers can only create claims for their own warranties
                queryset = Warranty.objects.filter(receipt_item__receipt__customer=user)
            else:
                # Retailers and admins can create claims for any warranty
                queryset = Warranty.objects.all()
        else:
            queryset = Warranty.objects.all()
        
        self.fields['warranty_id'] = serializers.PrimaryKeyRelatedField(
            queryset=queryset,
            source='warranty',
            write_only=True
        )
    
    def create(self, validated_data):
        # Set created_by from request user
        validated_data['created_by'] = self.context['request'].user
        claim = Claim.objects.create(**validated_data)
        return claim


class ClaimUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating claims (retailer/admin only) - Status, priority, and costs can be changed"""
    
    class Meta:
        model = Claim
        fields = ['status', 'priority', 'estimated_cost', 'actual_cost']
    
    def update(self, instance, validated_data):
        # Update allowed fields
        instance.status = validated_data.get('status', instance.status)
        instance.priority = validated_data.get('priority', instance.priority)
        instance.estimated_cost = validated_data.get('estimated_cost', instance.estimated_cost)
        instance.actual_cost = validated_data.get('actual_cost', instance.actual_cost)
        instance.save()
        return instance


# ==================== CUSTOMER-FACING CLAIM SERIALIZERS ====================

class CustomerClaimIssueChoicesSerializer(serializers.Serializer):
    """Return available issue categories for customer"""
    issue_choices = serializers.SerializerMethodField()
    
    def get_issue_choices(self, obj):
        return [
            {'value': 'Product not working', 'label': 'Product not working'},
            {'value': 'Damaged on arrival', 'label': 'Damaged on arrival'},
            {'value': 'Manufacturing defect', 'label': 'Manufacturing defect'},
            {'value': 'Performance issue', 'label': 'Performance issue'},
            {'value': 'Missing parts', 'label': 'Missing parts'},
            {'value': 'Other', 'label': 'Other'}
        ]


class CustomerClaimCreateSerializer(serializers.ModelSerializer):
    """Customer mobile app claim creation"""
    warranty_id = serializers.IntegerField(write_only=True)
    issue_type = serializers.CharField(source='category', write_only=True)
    description = serializers.CharField(source='detailed_description', write_only=True)
    
    class Meta:
        model = Claim
        fields = ['warranty_id', 'issue_type', 'issue_summary', 'description', 'priority']
    
    def validate_warranty_id(self, value):
        """Validate warranty belongs to customer and is active"""
        from warranties.models import Warranty
        from django.utils import timezone
        
        user = self.context['request'].user
        
        try:
            warranty = Warranty.objects.select_related('receipt_item__receipt').get(
                id=value,
                receipt_item__receipt__customer=user
            )
            
            # Check if warranty is active
            if warranty.expiry_date < timezone.now().date():
                raise serializers.ValidationError('Warranty has expired')
            
            return value
            
        except Warranty.DoesNotExist:
            raise serializers.ValidationError('Warranty not found or does not belong to you')
    
    def create(self, validated_data):
        from warranties.models import Warranty
        
        warranty_id = validated_data.pop('warranty_id')
        warranty = Warranty.objects.get(id=warranty_id)
        
        # Set warranty
        validated_data['warranty'] = warranty
        validated_data['created_by'] = self.context['request'].user
        
        claim = Claim.objects.create(**validated_data)
        return claim


class CustomerClaimListSerializer(serializers.ModelSerializer):
    """Customer claims list"""
    product_name = serializers.ReadOnlyField()
    product_model = serializers.CharField(source='warranty.receipt_item.model', read_only=True)
    store_name = serializers.CharField(source='warranty.receipt_item.receipt.store.name', read_only=True)
    
    class Meta:
        model = Claim
        fields = [
            'id', 'claim_number', 'product_name', 'product_model',
            'store_name', 'status', 'priority', 'issue_summary',
            'submitted_at', 'updated_at'
        ]
