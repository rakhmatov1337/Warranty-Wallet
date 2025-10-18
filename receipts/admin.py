from django.contrib import admin
from .models import Receipt, ReceiptItem

class ReceiptItemInline(admin.TabularInline):
    model = ReceiptItem
    extra = 1
    fields = ['product_name', 'model', 'serial_number', 'color', 'imei', 'storage', 'price', 'quantity', 'warranty_coverage', 'warranty_expiry', 'has_warranty_registered']
    readonly_fields = ['has_warranty_registered']
    
    @admin.display(description='Warranty Registered', boolean=True)
    def has_warranty_registered(self, obj):
        """Show if this receipt item has a warranty registered"""
        if obj.id:  # Only check if the object has been saved
            return hasattr(obj, 'warranty')
        return False

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'store', 'retailer', 'customer', 'total', 'date', 'created_at']
    list_filter = ['date', 'created_at', 'store']
    search_fields = ['receipt_number', 'store__name', 'retailer__username', 'retailer__email', 'customer__username', 'customer__email', 'notes']
    ordering = ['-created_at']
    date_hierarchy = 'date'
    autocomplete_fields = ['store', 'retailer', 'customer']
    readonly_fields = ['receipt_number', 'created_at', 'updated_at']
    inlines = [ReceiptItemInline]
    
    fieldsets = (
        ('Receipt Information', {
            'fields': ('receipt_number', 'store', 'retailer', 'customer')
        }),
        ('Financial Details', {
            'fields': ('total',)
        }),
        ('Transaction Details', {
            'fields': ('date', 'time', 'payment_method')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class HasWarrantyFilter(admin.SimpleListFilter):
    title = 'warranty status'
    parameter_name = 'has_warranty'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Has Warranty'),
            ('no', 'No Warranty'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(warranty__isnull=False)
        if self.value() == 'no':
            return queryset.filter(warranty__isnull=True)

@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'receipt', 'model', 'serial_number', 'color', 'imei', 'storage', 'price', 'quantity', 'warranty_expiry', 'has_warranty']
    list_filter = [HasWarrantyFilter, 'warranty_expiry', 'receipt__date']
    search_fields = ['product_name', 'model', 'serial_number', 'imei', 'receipt__receipt_number']
    autocomplete_fields = ['receipt']
    
    @admin.display(description='Has Warranty', boolean=True)
    def has_warranty(self, obj):
        """Show if this receipt item has a warranty registered"""
        return hasattr(obj, 'warranty')
