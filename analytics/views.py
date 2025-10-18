from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from receipts.models import Receipt, ReceiptItem
from warranties.models import Warranty
from claims.models import Claim
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal


class AnalyticsOverview(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Comprehensive analytics endpoint with all charts and metrics
        Query params:
        - period: '6months' (default), '12months', '1month'
        """
        period = request.query_params.get('period', '6months')
        
        # Determine months to analyze
        if period == '12months':
            months_count = 12
        elif period == '1month':
            months_count = 1
        else:
            months_count = 6
        
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate previous period for comparison
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(seconds=1)
        
        # Filter by user role
        user = request.user
        if user.role == 'retailer':
            receipts_filter = Q(retailer=user)
            warranties_filter = Q(receipt_item__receipt__retailer=user)
            claims_filter = Q(warranty__receipt_item__receipt__retailer=user)
        elif user.role == 'admin':
            receipts_filter = Q()
            warranties_filter = Q()
            claims_filter = Q()
        else:
            # Customers see only their own data
            receipts_filter = Q(customer=user)
            warranties_filter = Q(receipt_item__receipt__customer=user)
            claims_filter = Q(warranty__receipt_item__receipt__customer=user)
        
        # ==================== SUMMARY METRICS ====================
        
        # 1. Total Receipts
        receipts_this_month = Receipt.objects.filter(receipts_filter, date__gte=current_month_start).count()
        receipts_last_month = Receipt.objects.filter(receipts_filter, date__gte=last_month_start, date__lte=last_month_end).count()
        receipts_change = self._calculate_change(receipts_this_month, receipts_last_month)
        
        # 2. Active Warranties
        active_warranties = Warranty.objects.filter(warranties_filter, expiry_date__gte=now.date()).count()
        active_warranties_last_month = Warranty.objects.filter(warranties_filter, expiry_date__gte=last_month_end.date()).count()
        warranties_change = self._calculate_change(active_warranties, active_warranties_last_month)
        
        # 3. Claim Approval Rate
        total_claims = Claim.objects.filter(claims_filter).exclude(status='In Review').count()
        approved_claims = Claim.objects.filter(claims_filter, status='Approved').count()
        approval_rate = (approved_claims / total_claims * 100) if total_claims > 0 else 0
        
        total_claims_last = Claim.objects.filter(claims_filter, submitted_at__lte=last_month_end).exclude(status='In Review').count()
        approved_claims_last = Claim.objects.filter(claims_filter, status='Approved', submitted_at__lte=last_month_end).count()
        approval_rate_last = (approved_claims_last / total_claims_last * 100) if total_claims_last > 0 else 0
        approval_change = round(approval_rate - approval_rate_last, 1)
        
        # 4. Average Receipt Value
        avg_receipt = Receipt.objects.filter(receipts_filter, date__gte=current_month_start).aggregate(avg=Avg('total'))['avg'] or 0
        avg_receipt_last = Receipt.objects.filter(receipts_filter, date__gte=last_month_start, date__lte=last_month_end).aggregate(avg=Avg('total'))['avg'] or 0
        avg_receipt_change = self._calculate_change(float(avg_receipt), float(avg_receipt_last))
        
        # ==================== RECEIPT VOLUME TREND ====================
        receipt_trend = []
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            count = Receipt.objects.filter(
                receipts_filter,
                date__gte=month_start,
                date__lte=month_end
            ).count()
            
            receipt_trend.append({
                'month': month_start.strftime('%b'),
                'receipts': count
            })
        
        # ==================== PRODUCT CATEGORIES ====================
        # Get all receipt items with product categories
        items = ReceiptItem.objects.filter(receipt__in=Receipt.objects.filter(receipts_filter))
        
        # Categorize products (you can enhance this logic based on your needs)
        categories = {
            'Smartphones': 0,
            'Laptops': 0,
            'Tablets': 0,
            'Audio': 0,
            'Other': 0
        }
        
        total_items = items.count()
        if total_items > 0:
            for item in items:
                product_lower = item.product_name.lower()
                if any(keyword in product_lower for keyword in ['iphone', 'phone', 'smartphone', 'samsung', 'galaxy']):
                    categories['Smartphones'] += 1
                elif any(keyword in product_lower for keyword in ['laptop', 'macbook', 'notebook', 'thinkpad']):
                    categories['Laptops'] += 1
                elif any(keyword in product_lower for keyword in ['ipad', 'tablet']):
                    categories['Tablets'] += 1
                elif any(keyword in product_lower for keyword in ['airpods', 'headphone', 'speaker', 'audio', 'earbuds']):
                    categories['Audio'] += 1
                else:
                    categories['Other'] += 1
        
        product_categories = [
            {'name': name, 'value': count, 'percentage': round((count / total_items * 100) if total_items > 0 else 0, 1)}
            for name, count in categories.items()
        ]
        
        # ==================== WARRANTY MANAGEMENT ====================
        warranty_management = []
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            active = Warranty.objects.filter(
                warranties_filter,
                purchase_date__lte=month_end.date(),
                expiry_date__gte=month_start.date()
            ).count()
            
            new = Warranty.objects.filter(
                warranties_filter,
                created_at__gte=month_start,
                created_at__lte=month_end
            ).count()
            
            expired = Warranty.objects.filter(
                warranties_filter,
                expiry_date__gte=month_start.date(),
                expiry_date__lte=month_end.date()
            ).count()
            
            warranty_management.append({
                'month': month_start.strftime('%b'),
                'active': active,
                'new': new,
                'expired': expired
            })
        
        # ==================== CLAIMS PROCESSING ====================
        claims_processing = []
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            approved = Claim.objects.filter(
                claims_filter,
                status='Approved',
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ).count()
            
            pending = Claim.objects.filter(
                claims_filter,
                status='In Review',
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ).count()
            
            rejected = Claim.objects.filter(
                claims_filter,
                status='Rejected',
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ).count()
            
            claims_processing.append({
                'month': month_start.strftime('%b'),
                'approved': approved,
                'pending': pending,
                'rejected': rejected
            })
        
        # ==================== REVENUE VS WARRANTY COSTS ====================
        revenue_costs = []
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            # Revenue from receipts
            revenue = Receipt.objects.filter(
                receipts_filter,
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(total=Sum('total'))['total'] or 0
            
            # Warranty costs (estimated from approved claims)
            warranty_costs = Claim.objects.filter(
                claims_filter,
                status='Approved',
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ).aggregate(total=Sum('actual_cost'))['total'] or 0
            
            revenue_costs.append({
                'month': month_start.strftime('%b'),
                'revenue': float(revenue),
                'warranty_costs': float(warranty_costs)
            })
        
        # ==================== RESPONSE ====================
        return Response({
            'summary': {
                'total_receipts': {
                    'value': receipts_this_month,
                    'change': receipts_change,
                    'label': 'Total Receipts'
                },
                'active_warranties': {
                    'value': active_warranties,
                    'change': warranties_change,
                    'label': 'Active Warranties'
                },
                'claim_approval_rate': {
                    'value': round(approval_rate, 1),
                    'change': approval_change,
                    'label': 'Claim Approval Rate',
                    'unit': '%'
                },
                'avg_receipt_value': {
                    'value': round(float(avg_receipt), 2),
                    'change': avg_receipt_change,
                    'label': 'Avg Receipt Value',
                    'unit': '$'
                }
            },
            'charts': {
                'receipt_volume_trend': receipt_trend,
                'product_categories': product_categories,
                'warranty_management': warranty_management,
                'claims_processing': claims_processing,
                'revenue_costs': revenue_costs
            }
        })
    
    def _calculate_change(self, current, previous):
        """Calculate percentage change"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)
