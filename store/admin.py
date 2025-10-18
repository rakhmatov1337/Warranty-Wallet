from django.contrib import admin
from .models import Store

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone_number', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email', 'phone_number', 'address']
    filter_horizontal = ['admins']
    ordering = ['-created_at']
