from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Store
from .serializers import StoreSerializer, StoreListSerializer, StoreDetailSerializer
from django.db.models import Count, Q, Avg, Sum, F, Case, When, FloatField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta, datetime
from receipts.models import Receipt
from warranties.models import Warranty
from claims.models import Claim


class IsAdminOrStoreAdmin(permissions.BasePermission):
    """
    Custom permission: Only admins and users who are admins of the store can manage it.
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated and request.user.role == 'admin':
            return True
        if view.action in ['list', 'retrieve', 'dashboard']:
            return request.user.is_authenticated
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        return request.user in obj.admins.all()


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsAdminOrStoreAdmin]
    
    def get_queryset(self):
        user = self.request.user
        # Prefetch admins to avoid N+1 queries
        if user.role == 'admin':
            return Store.objects.prefetch_related('admins').all()
        elif user.role == 'retailer':
            # Retailers can only see stores they manage
            return user.managed_stores.prefetch_related('admins').all()
        return Store.objects.none()
    
    def list(self, request, *args, **kwargs):
        """
        List stores with dashboard statistics for retailers
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # If retailer, include dashboard statistics
        if request.user.role == 'retailer' and queryset.exists():
            stores_with_stats = []
            for store in queryset:
                serializer = self.get_serializer(store)
                store_data = serializer.data
                
                # Get dashboard statistics for this store
                stats = self._get_store_statistics(store)
                store_data['statistics'] = stats['statistics']
                store_data['recent_activity'] = stats['recent_activity']
                
                stores_with_stats.append(store_data)
            
            return Response(stores_with_stats)
        
        # For admins, return standard list
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _get_store_statistics(self, store):
        """
        Get dashboard statistics for a store (helper method)
        """
        now = timezone.now()
        
        # Define time periods
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = this_month_start - timedelta(seconds=1)
        
        # STATISTICS
        
        # 1. Total Receipts Issued
        receipts_this_month = Receipt.objects.filter(
            store=store,
            date__gte=this_month_start
        ).count()
        
        receipts_last_month = Receipt.objects.filter(
            store=store,
            date__gte=last_month_start,
            date__lte=last_month_end
        ).count()
        
        receipts_change = self._calculate_percentage_change(receipts_this_month, receipts_last_month)
        
        # 2. Active Warranties
        warranties_this_month = Warranty.objects.filter(
            receipt_item__receipt__store=store,
            expiry_date__gte=now.date()
        ).count()
        
        # Warranties that were active last month
        last_month_date = last_month_end.date()
        warranties_last_month = Warranty.objects.filter(
            receipt_item__receipt__store=store,
            expiry_date__gte=last_month_date
        ).count()
        
        warranties_change = self._calculate_percentage_change(warranties_this_month, warranties_last_month)
        
        # 3. Open Claims
        open_claims_this_month = Claim.objects.filter(
            warranty__receipt_item__receipt__store=store,
            status='In Review'
        ).count()
        
        open_claims_last_month = Claim.objects.filter(
            warranty__receipt_item__receipt__store=store,
            status='In Review',
            submitted_at__gte=last_month_start,
            submitted_at__lte=last_month_end
        ).count()
        
        claims_change = self._calculate_percentage_change(open_claims_this_month, open_claims_last_month)
        
        # 4. Average Resolution Time
        resolved_claims_this_month = Claim.objects.filter(
            warranty__receipt_item__receipt__store=store,
            status__in=['Approved', 'Rejected'],
            updated_at__gte=this_month_start
        )
        
        avg_resolution_this_month = 0
        if resolved_claims_this_month.exists():
            total_days = 0
            for claim in resolved_claims_this_month:
                resolution_time = (claim.updated_at - claim.submitted_at).total_seconds() / 86400
                total_days += resolution_time
            avg_resolution_this_month = round(total_days / resolved_claims_this_month.count(), 1)
        
        resolved_claims_last_month = Claim.objects.filter(
            warranty__receipt_item__receipt__store=store,
            status__in=['Approved', 'Rejected'],
            updated_at__gte=last_month_start,
            updated_at__lte=last_month_end
        )
        
        avg_resolution_last_month = 0
        if resolved_claims_last_month.exists():
            total_days = 0
            for claim in resolved_claims_last_month:
                resolution_time = (claim.updated_at - claim.submitted_at).total_seconds() / 86400
                total_days += resolution_time
            avg_resolution_last_month = round(total_days / resolved_claims_last_month.count(), 1)
        
        resolution_change = self._calculate_percentage_change(avg_resolution_this_month, avg_resolution_last_month, inverse=True)
        
        # RECENT ACTIVITY (Last 24 hours)
        # Only show activities performed by store's retailer admins
        recent_activity = []
        last_24h = now - timedelta(hours=24)
        
        # Get store admins (retailers)
        store_admins = store.admins.all()
        
        # Recent Claims (Approved/Rejected by store retailers)
        recent_claims = Claim.objects.filter(
            warranty__receipt_item__receipt__store=store,
            warranty__receipt_item__receipt__retailer__in=store_admins,
            updated_at__gte=last_24h
        ).exclude(status='In Review').select_related(
            'warranty__receipt_item__receipt__retailer'
        ).order_by('-updated_at')[:10]
        
        for claim in recent_claims:
            activity_type = 'claim_approved' if claim.status == 'Approved' else 'claim_rejected'
            retailer_name = claim.warranty.receipt_item.receipt.retailer.full_name or claim.warranty.receipt_item.receipt.retailer.email
            recent_activity.append({
                'type': activity_type,
                'title': f"Claim #{claim.claim_number} {claim.status}",
                'description': f"{claim.product_name} warranty claim",
                'timestamp': claim.updated_at,
                'status': claim.status,
                'icon': 'check' if claim.status == 'Approved' else 'x',
                'performed_by': retailer_name
            })
        
        # Recent Receipts (sent by store retailers)
        recent_receipts = Receipt.objects.filter(
            store=store,
            retailer__in=store_admins,
            created_at__gte=last_24h
        ).select_related('retailer', 'customer').order_by('-created_at')[:10]
        
        for receipt in recent_receipts:
            retailer_name = receipt.retailer.full_name or receipt.retailer.email
            recent_activity.append({
                'type': 'receipt_sent',
                'title': f"Receipt sent to {receipt.customer.email}",
                'description': f"Receipt #{receipt.receipt_number} - ${receipt.total}",
                'timestamp': receipt.created_at,
                'status': None,
                'icon': 'dollar',
                'performed_by': retailer_name
            })
        
        # Recent Warranties (registered by store retailers)
        recent_warranties = Warranty.objects.filter(
            receipt_item__receipt__store=store,
            receipt_item__receipt__retailer__in=store_admins,
            created_at__gte=last_24h
        ).select_related(
            'receipt_item__receipt__retailer',
            'receipt_item'
        ).order_by('-created_at')[:10]
        
        for warranty in recent_warranties:
            retailer_name = warranty.receipt_item.receipt.retailer.full_name or warranty.receipt_item.receipt.retailer.email
            recent_activity.append({
                'type': 'warranty_registered',
                'title': "New warranty registered",
                'description': f"{warranty.receipt_item.product_name} - {warranty.coverage_period_months} months coverage",
                'timestamp': warranty.created_at,
                'status': None,
                'icon': 'shield',
                'performed_by': retailer_name
            })
        
        # Sort all activities by timestamp
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Format timestamps
        for activity in recent_activity[:10]:  # Limit to 10 most recent
            time_diff = now - activity['timestamp']
            if time_diff < timedelta(minutes=1):
                activity['time_ago'] = 'Just now'
            elif time_diff < timedelta(hours=1):
                minutes = int(time_diff.total_seconds() / 60)
                activity['time_ago'] = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif time_diff < timedelta(days=1):
                hours = int(time_diff.total_seconds() / 3600)
                activity['time_ago'] = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = time_diff.days
                activity['time_ago'] = f"{days} day{'s' if days != 1 else ''} ago"
            
            # Remove timestamp from final output
            del activity['timestamp']
        
        return {
            'statistics': {
                'total_receipts': {
                    'value': receipts_this_month,
                    'change': receipts_change,
                    'label': 'Total Receipts Issued'
                },
                'active_warranties': {
                    'value': warranties_this_month,
                    'change': warranties_change,
                    'label': 'Active Warranties'
                },
                'open_claims': {
                    'value': open_claims_this_month,
                    'change': claims_change,
                    'label': 'Open Claims'
                },
                'avg_resolution_time': {
                    'value': avg_resolution_this_month,
                    'unit': 'days',
                    'change': resolution_change,
                    'label': 'Avg. Resolution Time'
                }
            },
            'recent_activity': recent_activity[:10]
        }
    
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """
        Get dashboard statistics and recent activity for a store
        (Alternative endpoint - same as list but for specific store)
        """
        store = self.get_object()
        stats = self._get_store_statistics(store)
        return Response(stats)
    
    def _calculate_percentage_change(self, current, previous, inverse=False):
        """
        Calculate percentage change between two values
        inverse=True means lower is better (like resolution time)
        """
        if previous == 0:
            if current > 0:
                return 100.0
            return 0.0
        
        change = ((current - previous) / previous) * 100
        
        if inverse:
            change = -change
        
        return round(change, 1)


# ==================== PUBLIC STORE APIs ====================

class PublicStoreListView(generics.ListAPIView):
    """
    Public API to list all stores with map URLs.
    No authentication required - accessible to everyone.
    Optimized with annotations to prevent N+1 queries.
    """
    serializer_class = StoreListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Annotate with claim statistics to prevent N+1 queries
        queryset = Store.objects.annotate(
            # Total resolved claims (Approved + Rejected)
            total_claims_count=Count(
                'receipts__items__warranty__claims',
                filter=~Q(receipts__items__warranty__claims__status='In Review'),
                distinct=True
            ),
            # Approved claims count
            approved_claims_count=Count(
                'receipts__items__warranty__claims',
                filter=Q(receipts__items__warranty__claims__status='Approved'),
                distinct=True
            ),
            # Rejected claims count
            rejected_claims_count=Count(
                'receipts__items__warranty__claims',
                filter=Q(receipts__items__warranty__claims__status='Rejected'),
                distinct=True
            ),
            # Success rate calculation
            calculated_success_rate=Case(
                When(total_claims_count=0, then=None),
                default=ExpressionWrapper(
                    F('approved_claims_count') * 100.0 / F('total_claims_count'),
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        ).order_by('-created_at')
        
        # Optional search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(email__icontains=search) |
                Q(phone_number__icontains=search)
            )
        
        # Filter by verified status (optional)
        verified = self.request.query_params.get('verified', None)
        if verified is not None:
            if verified.lower() == 'true':
                queryset = queryset.filter(is_verified=True)
            elif verified.lower() == 'false':
                queryset = queryset.filter(is_verified=False)
        
        return queryset


class PublicStoreDetailView(generics.RetrieveAPIView):
    """
    Public API to get store details with map URLs.
    No authentication required - accessible to everyone.
    Optimized with annotations to prevent N+1 queries.
    """
    serializer_class = StoreDetailSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Annotate with claim statistics and prefetch admins
        return Store.objects.annotate(
            # Total resolved claims (Approved + Rejected)
            total_claims_count=Count(
                'receipts__items__warranty__claims',
                filter=~Q(receipts__items__warranty__claims__status='In Review'),
                distinct=True
            ),
            # Approved claims count
            approved_claims_count=Count(
                'receipts__items__warranty__claims',
                filter=Q(receipts__items__warranty__claims__status='Approved'),
                distinct=True
            ),
            # Rejected claims count
            rejected_claims_count=Count(
                'receipts__items__warranty__claims',
                filter=Q(receipts__items__warranty__claims__status='Rejected'),
                distinct=True
            ),
            # Pending claims count
            pending_claims_count=Count(
                'receipts__items__warranty__claims',
                filter=Q(receipts__items__warranty__claims__status='In Review'),
                distinct=True
            ),
            # Success rate calculation
            calculated_success_rate=Case(
                When(total_claims_count=0, then=None),
                default=ExpressionWrapper(
                    F('approved_claims_count') * 100.0 / F('total_claims_count'),
                    output_field=FloatField()
                ),
                output_field=FloatField()
            ),
            # Admin count
            admin_count_annotated=Count('admins', distinct=True)
        ).prefetch_related('admins')
