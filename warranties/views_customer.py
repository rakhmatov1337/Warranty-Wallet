"""
Views for customer-uploaded warranties
CRUD operations for CustomerWarranty model
"""
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import CustomerWarranty
from .serializers import (
    CustomerWarrantySerializer,
    CustomerWarrantyCreateSerializer,
    CustomerWarrantyUpdateSerializer
)


class IsCustomerOwner(permissions.BasePermission):
    """
    Custom permission to only allow customers to access their own warranties
    """
    def has_permission(self, request, view):
        # Only customers can use this endpoint
        return request.user.is_authenticated and request.user.role == 'customer'
    
    def has_object_permission(self, request, view, obj):
        # Only the owner can access their warranty
        return obj.customer == request.user


class CustomerWarrantyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for customer-uploaded warranties
    Allows customers to CREATE, READ, UPDATE, DELETE their own warranties
    """
    permission_classes = [IsCustomerOwner]
    parser_classes = [MultiPartParser, FormParser]  # For file upload
    
    def get_queryset(self):
        """Return only warranties belonging to the current user"""
        return CustomerWarranty.objects.filter(customer=self.request.user)
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return CustomerWarrantyCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CustomerWarrantyUpdateSerializer
        return CustomerWarrantySerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new customer warranty"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return detailed response with all fields
        warranty = serializer.instance
        response_serializer = CustomerWarrantySerializer(warranty, context={'request': request})
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Update a customer warranty"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return detailed response
        response_serializer = CustomerWarrantySerializer(instance, context={'request': request})
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a customer warranty"""
        instance = self.get_object()
        
        # Delete the image file
        if instance.warranty_image:
            instance.warranty_image.delete(save=False)
        
        self.perform_destroy(instance)
        return Response(
            {'message': 'Warranty deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )

