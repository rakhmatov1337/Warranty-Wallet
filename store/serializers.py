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
        fields = ['id', 'name', 'image', 'phone_number', 'email', 'address', 'admins', 'admin_ids', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

