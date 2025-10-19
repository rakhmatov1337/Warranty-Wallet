from django.contrib import admin
from .models import Store

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone_number', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['name', 'email', 'phone_number', 'address']
    filter_horizontal = ['admins']
    ordering = ['-created_at']
    list_editable = ['is_verified']  # Allow quick verification from list view
    
    fieldsets = (
        ('Store Information', {
            'fields': ('name', 'image', 'email', 'phone_number', 'address')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'description': 'Store coordinates for map integration (Yandex Maps, Google Maps)'
        }),
        ('Verification Status', {
            'fields': ('is_verified',),
            'description': 'Only admins can verify stores. Verified stores get a badge.'
        }),
        ('Store Admins', {
            'fields': ('admins',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
