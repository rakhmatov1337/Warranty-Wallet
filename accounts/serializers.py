from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'password', 'role', 'access', 'refresh')
        extra_kwargs = {
            'role': {'default': 'customer'}
        }

    def create(self, validated_data):
        # Set role to customer if not provided
        if 'role' not in validated_data:
            validated_data['role'] = 'customer'
        
        user = User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            phone_number=validated_data.get('phone_number', ''),
            password=validated_data['password'],
            role=validated_data['role']
        )
        
        # Send welcome notification for customers
        if user.role == 'customer':
            from notifications.utils import notify_welcome
            notify_welcome(user)
        
        return user
    
    def to_representation(self, instance):
        """Add JWT tokens to the response"""
        data = super().to_representation(instance)
        
        # Generate tokens for the newly created user
        refresh = RefreshToken.for_user(instance)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'role')
