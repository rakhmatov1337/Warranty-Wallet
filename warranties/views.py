from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Warranty
from .serializers import (
    WarrantyListSerializer, WarrantyDetailSerializer, 
    WarrantyCreateSerializer, CustomerWarrantyMeSerializer
)
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from datetime import timedelta
import csv
from django.http import HttpResponse


class IsAuthenticatedUser(permissions.BasePermission):
    """
    Custom permission: Authenticated users can view/create warranties based on role
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.role == 'admin':
            return True
        # Retailers can manage warranties for their receipts
        if request.user.role == 'retailer':
            return obj.retailer == request.user
        # Customers can view their own warranties
        if request.user.role == 'customer':
            return obj.customer == request.user
        return False


class WarrantyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedUser]
    # Only allow GET and POST - no PUT/PATCH/DELETE (warranties are immutable)
    http_method_names = ['get', 'post', 'head', 'options']
    
    def get_queryset(self):
        user = self.request.user
        
        # Base queryset with related data
        queryset = Warranty.objects.select_related(
            'receipt_item', 
            'receipt_item__receipt',
            'receipt_item__receipt__store',
            'receipt_item__receipt__customer',
            'receipt_item__receipt__retailer'
        ).prefetch_related('claims')
        
        # Filter based on user role
        if user.role == 'admin':
            pass  # Admins see all
        elif user.role == 'retailer':
            queryset = queryset.filter(receipt_item__receipt__retailer=user)
        elif user.role == 'customer':
            queryset = queryset.filter(receipt_item__receipt__customer=user)
        else:
            return Warranty.objects.none()
        
        # Apply search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(receipt_item__product_name__icontains=search) |
                Q(receipt_item__serial_number__icontains=search) |
                Q(receipt_item__imei__icontains=search) |
                Q(receipt_item__receipt__customer__email__icontains=search) |
                Q(receipt_item__receipt__customer__first_name__icontains=search) |
                Q(receipt_item__receipt__customer__last_name__icontains=search)
            )
        
        # Apply status filter
        status_filter = self.request.query_params.get('status', None)
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Apply coverage filter (based on expiry)
        coverage_filter = self.request.query_params.get('coverage', None)
        today = timezone.now().date()
        
        if coverage_filter == 'active':
            queryset = queryset.filter(expiry_date__gte=today)
        elif coverage_filter == 'expiring_soon':
            # Expiring within 30 days
            soon_date = today + timedelta(days=30)
            queryset = queryset.filter(
                expiry_date__gte=today,
                expiry_date__lte=soon_date
            )
        elif coverage_filter == 'expired':
            queryset = queryset.filter(expiry_date__lt=today)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return WarrantyCreateSerializer
        elif self.action == 'retrieve':
            return WarrantyDetailSerializer
        return WarrantyListSerializer
    
    def list(self, request, *args, **kwargs):
        """
        List warranties with statistics included
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate statistics for all warranties (without filters except role-based)
        user = request.user
        if user.role == 'admin':
            stats_queryset = Warranty.objects.all()
        elif user.role == 'retailer':
            stats_queryset = Warranty.objects.filter(receipt_item__receipt__retailer=user)
        elif user.role == 'customer':
            stats_queryset = Warranty.objects.filter(receipt_item__receipt__customer=user)
        else:
            stats_queryset = Warranty.objects.none()
        
        today = timezone.now().date()
        soon_date = today + timedelta(days=30)
        
        # Active warranties (not expired)
        active_count = stats_queryset.filter(expiry_date__gte=today).count()
        
        # Expiring soon (within 30 days, not yet expired)
        expiring_soon_count = stats_queryset.filter(
            expiry_date__gte=today,
            expiry_date__lte=soon_date
        ).count()
        
        # Expired
        expired_count = stats_queryset.filter(expiry_date__lt=today).count()
        
        # Total coverage value (sum of all coverage values)
        total_coverage = stats_queryset.aggregate(
            total=Sum('receipt_item__price')
        )['total'] or 0
        
        # Paginate warranties
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['statistics'] = {
                'active_warranties': active_count,
                'expiring_soon': expiring_soon_count,
                'expired': expired_count,
                'total_coverage': float(total_coverage)
            }
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'statistics': {
                'active_warranties': active_count,
                'expiring_soon': expiring_soon_count,
                'expired': expired_count,
                'total_coverage': float(total_coverage)
            },
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export all warranties to CSV
        """
        queryset = self.get_queryset()
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="warranties_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Warranty ID', 'Product Name', 'Model', 'Serial Number', 'IMEI',
            'Customer', 'Store', 'Status', 'Purchase Date', 'Expiry Date',
            'Remaining Days', 'Coverage Value', 'Provider', 'Coverage Terms', 'Claims Count'
        ])
        
        for warranty in queryset:
            writer.writerow([
                warranty.id,
                warranty.receipt_item.product_name,
                warranty.receipt_item.model or '',
                warranty.receipt_item.serial_number or '',
                warranty.receipt_item.imei or '',
                warranty.customer.email,
                warranty.store.name,
                warranty.status,
                warranty.purchase_date,
                warranty.expiry_date,
                warranty.remaining_days,
                warranty.coverage_value,
                warranty.provider,
                warranty.coverage_terms,
                warranty.claims_count
            ])
        
        return response


class CustomerWarrantyMeView(APIView):
    """
    GET /api/warranties/me/
    Returns all warranties for the authenticated customer with receipt item details.
    Only accessible to customers.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Ensure user is a customer
        if request.user.role != 'customer':
            return Response(
                {'error': 'This endpoint is only accessible to customers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all warranties for this customer with optimized query
        warranties = Warranty.objects.filter(
            receipt_item__receipt__customer=request.user
        ).select_related(
            'receipt_item',
            'receipt_item__receipt',
            'receipt_item__receipt__store',
            'receipt_item__receipt__retailer'
        ).prefetch_related('claims').order_by('-created_at')
        
        # Apply optional filters
        status_filter = request.query_params.get('status', None)
        if status_filter:
            today = timezone.now().date()
            if status_filter == 'active':
                warranties = warranties.filter(expiry_date__gte=today)
            elif status_filter == 'expired':
                warranties = warranties.filter(expiry_date__lt=today)
            elif status_filter == 'expiring_soon':
                soon_date = today + timedelta(days=30)
                warranties = warranties.filter(
                    expiry_date__gte=today,
                    expiry_date__lte=soon_date
                )
        
        # Search by product name
        search = request.query_params.get('search', None)
        if search:
            warranties = warranties.filter(
                Q(receipt_item__product_name__icontains=search) |
                Q(receipt_item__model__icontains=search) |
                Q(receipt_item__serial_number__icontains=search)
            )
        
        # Serialize and return
        serializer = CustomerWarrantyMeSerializer(warranties, many=True, context={'request': request})
        
        # Calculate statistics
        today = timezone.now().date()
        soon_date = today + timedelta(days=30)
        
        total_count = warranties.count()
        active_count = warranties.filter(expiry_date__gte=today).count()
        expired_count = warranties.filter(expiry_date__lt=today).count()
        expiring_soon_count = warranties.filter(
            expiry_date__gte=today,
            expiry_date__lte=soon_date
        ).count()
        
        return Response({
            'count': total_count,
            'statistics': {
                'total': total_count,
                'active': active_count,
                'expired': expired_count,
                'expiring_soon': expiring_soon_count
            },
            'results': serializer.data
        })
