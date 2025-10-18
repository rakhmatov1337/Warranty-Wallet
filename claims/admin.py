from django.contrib import admin
from .models import Claim, ClaimNote, ClaimAttachment


class ClaimNoteInline(admin.TabularInline):
    model = ClaimNote
    extra = 0
    readonly_fields = ['author', 'created_at']
    fields = ['content', 'author', 'created_at']


class ClaimAttachmentInline(admin.TabularInline):
    model = ClaimAttachment
    extra = 0
    readonly_fields = ['file_name', 'file_size', 'uploaded_by', 'uploaded_at', 'file_size_display']
    fields = ['file', 'file_name', 'file_size_display', 'uploaded_by', 'uploaded_at']


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_number', 'get_product', 'get_customer', 'get_assigned_to', 'status', 'priority', 'category', 'estimated_cost', 'submitted_at']
    list_filter = ['status', 'priority', 'category', 'submitted_at']
    search_fields = ['claim_number', 'issue_summary', 'warranty__receipt_item__product_name', 'warranty__receipt_item__receipt__customer__email']
    ordering = ['-submitted_at']
    date_hierarchy = 'submitted_at'
    readonly_fields = ['claim_number', 'submitted_at', 'updated_at', 'get_customer', 'get_retailer', 'get_product', 'get_assigned_to']
    autocomplete_fields = ['warranty', 'created_by']
    inlines = [ClaimNoteInline, ClaimAttachmentInline]
    
    fieldsets = (
        ('Claim Information', {
            'fields': ('claim_number', 'warranty', 'get_product')
        }),
        ('Issue Details', {
            'fields': ('issue_summary', 'detailed_description', 'category')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'priority', 'get_assigned_to')
        }),
        ('Cost Information', {
            'fields': ('estimated_cost', 'actual_cost')
        }),
        ('Related Information', {
            'fields': ('get_customer', 'get_retailer', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    @admin.display(description='Product')
    def get_product(self, obj):
        try:
            return obj.product_name
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
    
    @admin.display(description='Assigned To')
    def get_assigned_to(self, obj):
        """Display automatically assigned customer"""
        try:
            return obj.assigned_to.email if obj.assigned_to else '-'
        except:
            return '-'


@admin.register(ClaimNote)
class ClaimNoteAdmin(admin.ModelAdmin):
    list_display = ['claim', 'author', 'created_at']
    list_filter = ['created_at']
    search_fields = ['claim__claim_number', 'content']
    readonly_fields = ['created_at']
    autocomplete_fields = ['claim', 'author']


@admin.register(ClaimAttachment)
class ClaimAttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'claim', 'file_size_display', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['claim__claim_number', 'file_name', 'uploaded_by__email']
    readonly_fields = ['file_name', 'file_size', 'file_size_display', 'uploaded_at']
    autocomplete_fields = ['claim', 'uploaded_by']
