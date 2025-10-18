from django.contrib import admin
from .models import Warranty, CustomerWarranty
from receipts.models import ReceiptItem

@admin.register(Warranty)
class WarrantyAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_product_name', 'get_customer', 'get_retailer', 'get_serial_number', 'purchase_date', 'expiry_date', 'get_status', 'created_at']
    list_filter = ['purchase_date', 'expiry_date', 'created_at']
    search_fields = ['receipt_item__product_name', 'receipt_item__serial_number', 'receipt_item__receipt__customer__username', 'receipt_item__receipt__customer__email']
    ordering = ['-created_at']
    date_hierarchy = 'purchase_date'
    readonly_fields = ['created_at', 'updated_at', 'get_customer', 'get_retailer', 'get_product_name', 'get_serial_number', 'get_status', 'remaining_days', 'coverage_value', 'claims_count']
    autocomplete_fields = ['receipt_item']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Filter receipt_item to only show items without an existing warranty
        """
        if db_field.name == "receipt_item":
            # When adding a new warranty, only show receipt items without a warranty
            kwargs["queryset"] = ReceiptItem.objects.filter(warranty__isnull=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_fieldsets(self, request, obj=None):
        """
        Return different fieldsets for add vs change forms
        """
        if obj is None:  # Adding new warranty
            return (
                ('Receipt Item', {
                    'fields': ('receipt_item',),
                    'description': 'Select a receipt item. Purchase date will be automatically set from the receipt date.'
                }),
                ('Warranty Coverage', {
                    'fields': ('coverage_period_months', 'provider', 'coverage_terms'),
                    'description': 'Expiry date and status will be automatically calculated. Status: Active if not expired, Expired otherwise.'
                }),
            )
        else:  # Editing existing warranty
            return (
                ('Receipt Item', {
                    'fields': ('receipt_item', 'get_product_name', 'get_serial_number')
                }),
                ('Warranty Coverage', {
                    'fields': ('coverage_period_months', 'provider', 'coverage_terms', 'purchase_date', 'expiry_date', 'get_status')
                }),
                ('Calculated Fields', {
                    'fields': ('remaining_days', 'coverage_value', 'claims_count'),
                    'classes': ('collapse',)
                }),
                ('Related Info', {
                    'fields': ('get_customer', 'get_retailer'),
                    'classes': ('collapse',)
                }),
                ('Timestamps', {
                    'fields': ('created_at', 'updated_at'),
                    'classes': ('collapse',)
                }),
            )
    
    @admin.display(description='Product Name')
    def get_product_name(self, obj):
        try:
            return obj.receipt_item.product_name if obj.receipt_item else '-'
        except:
            return '-'
    
    @admin.display(description='Serial Number')
    def get_serial_number(self, obj):
        try:
            return obj.receipt_item.serial_number if obj.receipt_item else '-'
        except:
            return '-'
    
    @admin.display(description='Customer')
    def get_customer(self, obj):
        try:
            return obj.customer.email if obj.customer else '-'
        except:
            return '-'
    
    @admin.display(description='Retailer')
    def get_retailer(self, obj):
        try:
            return obj.retailer.email if obj.retailer else '-'
        except:
            return '-'
    
    @admin.display(description='Status')
    def get_status(self, obj):
        """Display auto-calculated status"""
        try:
            return obj.status
        except:
            return '-'


@admin.register(CustomerWarranty)
class CustomerWarrantyAdmin(admin.ModelAdmin):
    list_display = ['id', 'product_name', 'customer_email', 'expiry_date', 'get_status', 'created_at']
    list_filter = ['expiry_date', 'created_at']
    search_fields = ['product_name', 'customer__email', 'customer__username', 'notes']
    ordering = ['-created_at']
    date_hierarchy = 'expiry_date'
    readonly_fields = ['customer', 'is_active', 'days_remaining', 'get_status', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('customer', 'product_name', 'expiry_date')
        }),
        ('Warranty Document', {
            'fields': ('warranty_image',)
        }),
        ('Additional Details', {
            'fields': ('notes',)
        }),
        ('Status', {
            'fields': ('get_status', 'is_active', 'days_remaining'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description='Customer Email')
    def customer_email(self, obj):
        return obj.customer.email if obj.customer else '-'
    
    @admin.display(description='Status')
    def get_status(self, obj):
        return obj.status
