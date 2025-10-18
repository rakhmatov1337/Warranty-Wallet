from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Receipt, ReceiptItem
from .serializers import (
    ReceiptSerializer, ReceiptCreateSerializer, ReceiptItemWithReceiptSerializer,
    CustomerReceiptListSerializer, CustomerReceiptDetailSerializer
)
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from django.http import HttpResponse
from notifications.utils import notify_new_receipt

class IsRetailerOrAdmin(permissions.BasePermission):
    """
    Custom permission: Only retailers and admins can manage receipts
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['retailer', 'admin']
    
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.role == 'admin':
            return True
        # Retailers can only manage their own receipts
        return obj.retailer == request.user


class ReceiptViewSet(viewsets.ModelViewSet):
    permission_classes = [IsRetailerOrAdmin]
    # Only allow GET, POST, DELETE - no PUT/PATCH (no updates allowed)
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    
    def get_queryset(self):
        user = self.request.user
        
        # Base queryset based on user role
        if user.role == 'admin':
            queryset = Receipt.objects.all()
        elif user.role == 'retailer':
            queryset = Receipt.objects.filter(retailer=user)
        elif user.role == 'customer':
            queryset = Receipt.objects.filter(customer=user)
        else:
            return Receipt.objects.none()
        
        # Apply search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(receipt_number__icontains=search) |
                Q(customer__username__icontains=search) |
                Q(customer__email__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(items__product_name__icontains=search)
            ).distinct()
        
        # Apply warranty filter
        warranty_filter = self.request.query_params.get('warranty', None)
        if warranty_filter and warranty_filter != 'all':
            if warranty_filter == 'active':
                queryset = queryset.filter(items__warranty_expiry__gte=timezone.now().date()).distinct()
            elif warranty_filter == 'expired':
                queryset = queryset.filter(items__warranty_expiry__lt=timezone.now().date()).distinct()
            elif warranty_filter == 'pending':
                queryset = queryset.filter(items__warranty_expiry__isnull=True).distinct()
        
        return queryset.select_related('store', 'retailer', 'customer').prefetch_related('items')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReceiptCreateSerializer
        return ReceiptSerializer
    
    def perform_create(self, serializer):
        """Override to send notification when receipt is created"""
        receipt = serializer.save()
        # Notify customer about new receipt
        notify_new_receipt(receipt, actor=self.request.user)
        return receipt
    
    def list(self, request, *args, **kwargs):
        """
        List receipts with statistics included
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate statistics for all receipts (without filters)
        user = request.user
        if user.role == 'admin':
            stats_queryset = Receipt.objects.all()
        elif user.role == 'retailer':
            stats_queryset = Receipt.objects.filter(retailer=user)
        elif user.role == 'customer':
            stats_queryset = Receipt.objects.filter(customer=user)
        else:
            stats_queryset = Receipt.objects.none()
        
        # Total receipts
        total_receipts = stats_queryset.count()
        
        # This month receipts
        now = timezone.now()
        this_month = stats_queryset.filter(
            date__year=now.year,
            date__month=now.month
        ).count()
        
        # Total value
        total_value = stats_queryset.aggregate(total=Sum('total'))['total'] or 0
        
        # Paginate receipts
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['statistics'] = {
                'total_receipts': total_receipts,
                'this_month': this_month,
                'total_value': float(total_value)
            }
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'statistics': {
                'total_receipts': total_receipts,
                'this_month': this_month,
                'total_value': float(total_value)
            },
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def my_receipts(self, request):
        """
        Get receipts created by the current retailer
        """
        receipts = Receipt.objects.filter(retailer=request.user)
        serializer = self.get_serializer(receipts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_store(self, request):
        """
        Get receipts filtered by store
        Query param: store_id
        """
        store_id = request.query_params.get('store_id')
        if not store_id:
            return Response({'error': 'store_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        receipts = self.get_queryset().filter(store_id=store_id)
        serializer = self.get_serializer(receipts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """
        Resend receipt to customer (placeholder - implement email logic)
        """
        receipt = self.get_object()
        return Response({'message': 'Receipt resent successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def download_csv(self, request, pk=None):
        """
        Download single receipt as CSV with items
        """
        receipt = self.get_object()
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="receipt_{receipt.receipt_number}.csv"'
        
        writer = csv.writer(response)
        
        # Write receipt header info
        writer.writerow(['RECEIPT DETAILS'])
        writer.writerow(['Receipt Number', receipt.receipt_number])
        writer.writerow(['Date', receipt.date])
        writer.writerow(['Time', receipt.time or 'N/A'])
        writer.writerow(['Store', receipt.store.name])
        writer.writerow(['Customer', receipt.customer.email])
        writer.writerow(['Retailer', receipt.retailer.email])
        writer.writerow(['Payment Method', receipt.payment_method or 'N/A'])
        writer.writerow([])
        
        # Write items header
        writer.writerow(['ITEMS'])
        writer.writerow([
            'Product Name', 'Model', 'Serial Number', 
            'Price', 'Quantity', 'Item Total', 
            'Warranty Coverage', 'Warranty Expiry'
        ])
        
        # Write items
        for item in receipt.items.all():
            writer.writerow([
                item.product_name,
                item.model or '',
                item.serial_number or '',
                item.price,
                item.quantity,
                item.item_total,
                item.warranty_coverage or '',
                item.warranty_expiry or ''
            ])
        
        # Write total
        writer.writerow([])
        writer.writerow(['TOTAL', '', '', '', '', receipt.total])
        
        if receipt.notes:
            writer.writerow([])
            writer.writerow(['NOTES'])
            writer.writerow([receipt.notes])
        
        return response
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export all receipts to CSV (summary only, no items)
        """
        queryset = self.get_queryset()
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="receipts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Receipt Number', 'Store', 'Customer', 'Retailer', 
            'Total', 'Items Count', 'Date', 'Time', 'Payment Method', 'Notes'
        ])
        
        for receipt in queryset:
            writer.writerow([
                receipt.receipt_number,
                receipt.store.name,
                receipt.customer.email,
                receipt.retailer.email,
                receipt.total,
                receipt.items.count(),
                receipt.date,
                receipt.time or '',
                receipt.payment_method or '',
                receipt.notes or ''
            ])
        
        return response


class ReceiptItemsWithoutWarrantyView(generics.ListAPIView):
    """
    Get all receipt items that don't have a warranty registered yet
    """
    serializer_class = ReceiptItemWithReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return receipt items without warranties
        Optionally filter by store or customer based on user role
        """
        user = self.request.user
        
        # Base queryset: items without warranties
        queryset = ReceiptItem.objects.filter(warranty__isnull=True).select_related(
            'receipt', 'receipt__store', 'receipt__customer', 'receipt__retailer'
        )
        
        # Filter based on user role
        if user.role == 'retailer':
            # Retailers see items from their stores
            queryset = queryset.filter(receipt__retailer=user)
        elif user.role == 'customer':
            # Customers see only their own items
            queryset = queryset.filter(receipt__customer=user)
        # Admins see all items (no additional filter)
        
        # Optional filters from query params
        store_id = self.request.query_params.get('store_id', None)
        if store_id:
            queryset = queryset.filter(receipt__store_id=store_id)
        
        customer_id = self.request.query_params.get('customer_id', None)
        if customer_id:
            queryset = queryset.filter(receipt__customer_id=customer_id)
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(product_name__icontains=search) |
                Q(model__icontains=search) |
                Q(serial_number__icontains=search) |
                Q(imei__icontains=search)
            )
        
        return queryset.order_by('-receipt__date')


class StoreCustomersView(generics.ListAPIView):
    """
    Get list of customers who have purchased from retailer's stores
    Retailers automatically see customers from their stores
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """
        Get customers with purchase statistics
        Optional query params: store_id (to filter by specific store)
        """
        from django.contrib.auth import get_user_model
        from django.db.models import Count, Sum, Max
        
        User = get_user_model()
        user = request.user
        
        # Only retailers and admins can access
        if user.role not in ['retailer', 'admin']:
            return Response({'error': 'Permission denied. Only retailers and admins can view customers.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get store IDs based on user role
        if user.role == 'retailer':
            # Retailers see customers from their stores
            store_ids = user.managed_stores.values_list('id', flat=True)
            if not store_ids:
                return Response({'count': 0, 'results': []})
        else:
            # Admins see all customers
            from store.models import Store
            store_ids = Store.objects.values_list('id', flat=True)
        
        # Optional: filter by specific store
        store_id = request.query_params.get('store_id', None)
        if store_id:
            if user.role == 'retailer':
                # Verify retailer has access to this store
                if int(store_id) not in store_ids:
                    return Response({'error': 'You do not have access to this store'}, status=status.HTTP_403_FORBIDDEN)
            store_ids = [int(store_id)]
        
        # Get unique customers who have receipts from these stores
        customers = User.objects.filter(
            customer_receipts__store_id__in=store_ids,
            role='customer'
        ).distinct().annotate(
            total_receipts=Count('customer_receipts', filter=Q(customer_receipts__store_id__in=store_ids)),
            total_spent=Sum('customer_receipts__total', filter=Q(customer_receipts__store_id__in=store_ids)),
            last_purchase=Max('customer_receipts__date', filter=Q(customer_receipts__store_id__in=store_ids)),
            total_items=Count('customer_receipts__items', filter=Q(customer_receipts__store_id__in=store_ids))
        ).order_by('-last_purchase')
        
        # Apply search filter
        search = request.query_params.get('search', None)
        if search:
            customers = customers.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search)
            )
        
        # Serialize customer data
        customer_data = []
        for customer in customers:
            customer_data.append({
                'id': customer.id,
                'email': customer.email,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'username': customer.username,
                'full_name': customer.get_full_name(),
                'statistics': {
                    'total_receipts': customer.total_receipts,
                    'total_spent': float(customer.total_spent or 0),
                    'last_purchase': customer.last_purchase,
                    'total_items': customer.total_items
                }
            })
        
        return Response({
            'count': len(customer_data),
            'results': customer_data
        })


# ==================== CUSTOMER-FACING VIEWS ====================

class CustomerReceiptsView(generics.ListAPIView):
    """
    Customer mobile app receipts list endpoint
    """
    serializer_class = CustomerReceiptListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get receipts for the authenticated customer"""
        user = self.request.user
        
        # Only customers can use this endpoint
        if user.role != 'customer':
            return Receipt.objects.none()
        
        queryset = Receipt.objects.filter(customer=user).select_related('store').prefetch_related('items')
        
        # Search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(store__name__icontains=search) |
                Q(items__product_name__icontains=search)
            ).distinct()
        
        # Status filter
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            today = timezone.now().date()
            if status_filter == 'active':
                queryset = queryset.filter(items__warranty_expiry__gte=today).distinct()
            elif status_filter == 'expiring':
                expiring_date = today + timedelta(days=30)
                queryset = queryset.filter(
                    items__warranty_expiry__gte=today,
                    items__warranty_expiry__lte=expiring_date
                ).distinct()
            elif status_filter == 'expired':
                queryset = queryset.filter(items__warranty_expiry__lt=today).distinct()
        
        return queryset.order_by('-date')


class CustomerReceiptDetailView(generics.RetrieveAPIView):
    """
    Customer mobile app receipt detail endpoint
    """
    serializer_class = CustomerReceiptDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get receipt for the authenticated customer"""
        user = self.request.user
        
        # Only customers can use this endpoint
        if user.role != 'customer':
            return Receipt.objects.none()
        
        return Receipt.objects.filter(customer=user).select_related('store').prefetch_related('items')


class CustomerHomeView(generics.GenericAPIView):
    """
    Customer mobile app home/dashboard endpoint
    Returns:
    - User greeting
    - Warranty summary (active, expiring, expired counts)
    - Expiring soon warranties
    - Recent purchases
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        # Only customers can use this endpoint
        if user.role != 'customer':
            return Response({'error': 'Only customers can use this endpoint'}, status=status.HTTP_403_FORBIDDEN)
        
        today = timezone.now().date()
        expiring_soon_date = today + timedelta(days=30)
        
        # Get all receipts with items for the customer
        receipts = Receipt.objects.filter(customer=user).select_related('store').prefetch_related('items')
        
        # Calculate warranty summary
        all_items_with_warranty = ReceiptItem.objects.filter(
            receipt__customer=user,
            warranty_expiry__isnull=False
        )
        
        active_count = all_items_with_warranty.filter(warranty_expiry__gte=today).count()
        expiring_count = all_items_with_warranty.filter(
            warranty_expiry__gte=today,
            warranty_expiry__lte=expiring_soon_date
        ).count()
        expired_count = all_items_with_warranty.filter(warranty_expiry__lt=today).count()
        
        # Get expiring soon items (within 30 days, sorted by nearest expiry)
        expiring_soon_items = ReceiptItem.objects.filter(
            receipt__customer=user,
            warranty_expiry__gte=today,
            warranty_expiry__lte=expiring_soon_date
        ).select_related('receipt__store').order_by('warranty_expiry')[:5]
        
        expiring_soon_list = []
        for item in expiring_soon_items:
            days_left = (item.warranty_expiry - today).days
            expiring_soon_list.append({
                'id': item.id,
                'product_name': item.product_name,
                'store_name': item.receipt.store.name,
                'days_left': days_left,
                'warranty_expiry': item.warranty_expiry,
                'receipt_id': item.receipt.id,
                'price': str(item.price)
            })
        
        # Get recent purchases (last 10 receipts)
        recent_receipts = receipts.order_by('-date')[:10]
        recent_purchases_list = []
        
        for receipt in recent_receipts:
            # Get the main/first product from receipt
            first_item = receipt.items.first()
            if first_item:
                # Check if any item in receipt has active warranty
                has_active_warranty = receipt.items.filter(warranty_expiry__gte=today).exists()
                
                recent_purchases_list.append({
                    'receipt_id': receipt.id,
                    'product_name': first_item.product_name,
                    'store_name': receipt.store.name,
                    'date': receipt.date.strftime('%b %d, %Y'),
                    'price': f"${receipt.total}",
                    'total': str(receipt.total),
                    'has_active_warranty': has_active_warranty,
                    'items_count': receipt.items.count()
                })
        
        # Response data
        response_data = {
            'user': {
                'full_name': user.full_name,
                'email': user.email,
                'phone_number': user.phone_number or ''
            },
            'warranty_summary': {
                'active': active_count,
                'expiring': expiring_count,
                'expired': expired_count
            },
            'expiring_soon': expiring_soon_list,
            'recent_purchases': recent_purchases_list
        }
        
        return Response(response_data)
