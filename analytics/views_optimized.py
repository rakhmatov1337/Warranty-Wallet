from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from receipts.models import Receipt, ReceiptItem
from warranties.models import Warranty
from claims.models import Claim, ClaimNote
from django.db.models import (
    Avg, Count, Sum, Q, F, ExpressionWrapper, DurationField,
    Case, When, IntegerField, CharField, Value, Subquery, OuterRef
)
from django.db.models.functions import TruncMonth, Lower
from django.utils import timezone
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from .ai_service import ClaimAnalyticsAI


class AnalyticsOverviewOptimized(APIView):
    """
    OPTIMIZED analytics endpoint with minimal database queries
    Uses subqueries, annotations, and conditional aggregation
    """
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
        
        # ==================== OPTIMIZED SUMMARY METRICS ====================
        # Use a SINGLE query with conditional aggregation for all summary stats
        
        summary_stats = Receipt.objects.filter(receipts_filter).aggregate(
            # Current month receipts
            receipts_this_month=Count('id', filter=Q(date__gte=current_month_start)),
            # Last month receipts
            receipts_last_month=Count('id', filter=Q(
                date__gte=last_month_start,
                date__lte=last_month_end
            )),
            # Average receipt value this month
            avg_receipt=Avg('total', filter=Q(date__gte=current_month_start)),
            # Average receipt value last month
            avg_receipt_last=Avg('total', filter=Q(
                date__gte=last_month_start,
                date__lte=last_month_end
            )),
        )
        
        # Warranty stats in one query
        warranty_stats = Warranty.objects.filter(warranties_filter).aggregate(
            active_warranties=Count('id', filter=Q(expiry_date__gte=now.date())),
            active_warranties_last=Count('id', filter=Q(expiry_date__gte=last_month_end.date())),
        )
        
        # Claim stats in one query
        claim_stats = Claim.objects.filter(claims_filter).aggregate(
            total_claims=Count('id', filter=~Q(status='In Review')),
            approved_claims=Count('id', filter=Q(status='Approved')),
            total_claims_last=Count('id', filter=Q(
                submitted_at__lte=last_month_end,
                ~Q(status='In Review')
            )),
            approved_claims_last=Count('id', filter=Q(
                status='Approved',
                submitted_at__lte=last_month_end
            )),
        )
        
        # Calculate changes
        receipts_change = self._calculate_change(
            summary_stats['receipts_this_month'],
            summary_stats['receipts_last_month']
        )
        warranties_change = self._calculate_change(
            warranty_stats['active_warranties'],
            warranty_stats['active_warranties_last']
        )
        
        approval_rate = (claim_stats['approved_claims'] / claim_stats['total_claims'] * 100) \
            if claim_stats['total_claims'] > 0 else 0
        approval_rate_last = (claim_stats['approved_claims_last'] / claim_stats['total_claims_last'] * 100) \
            if claim_stats['total_claims_last'] > 0 else 0
        approval_change = round(approval_rate - approval_rate_last, 1)
        
        avg_receipt_change = self._calculate_change(
            float(summary_stats['avg_receipt'] or 0),
            float(summary_stats['avg_receipt_last'] or 0)
        )
        
        # ==================== OPTIMIZED RECEIPT VOLUME TREND ====================
        # Single query using GROUP BY month
        
        start_date = current_month_start - relativedelta(months=months_count - 1)
        
        receipt_trend_data = Receipt.objects.filter(
            receipts_filter,
            date__gte=start_date
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            receipts=Count('id')
        ).order_by('month')
        
        # Create a dict for fast lookup
        trend_dict = {item['month']: item['receipts'] for item in receipt_trend_data}
        
        # Build the response array
        receipt_trend = []
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_key = month_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            receipt_trend.append({
                'month': month_start.strftime('%b'),
                'receipts': trend_dict.get(month_key, 0)
            })
        
        # ==================== OPTIMIZED PRODUCT CATEGORIES ====================
        # Use database CASE WHEN for categorization instead of Python loop
        
        product_categories_data = ReceiptItem.objects.filter(
            receipt__in=Receipt.objects.filter(receipts_filter).values('id')
        ).annotate(
            category=Case(
                # Smartphones
                When(Q(product_name__icontains='iphone') |
                     Q(product_name__icontains='phone') |
                     Q(product_name__icontains='smartphone') |
                     Q(product_name__icontains='samsung') |
                     Q(product_name__icontains='galaxy'),
                     then=Value('Smartphones')),
                # Laptops
                When(Q(product_name__icontains='laptop') |
                     Q(product_name__icontains='macbook') |
                     Q(product_name__icontains='notebook') |
                     Q(product_name__icontains='thinkpad'),
                     then=Value('Laptops')),
                # Tablets
                When(Q(product_name__icontains='ipad') |
                     Q(product_name__icontains='tablet'),
                     then=Value('Tablets')),
                # Audio
                When(Q(product_name__icontains='airpods') |
                     Q(product_name__icontains='headphone') |
                     Q(product_name__icontains='speaker') |
                     Q(product_name__icontains='audio') |
                     Q(product_name__icontains='earbuds'),
                     then=Value('Audio')),
                # Other
                default=Value('Other'),
                output_field=CharField(),
            )
        ).values('category').annotate(
            count=Count('id')
        )
        
        # Calculate total
        total_items = sum(item['count'] for item in product_categories_data)
        
        product_categories = [
            {
                'name': item['category'],
                'value': item['count'],
                'percentage': round((item['count'] / total_items * 100) if total_items > 0 else 0, 1)
            }
            for item in product_categories_data
        ]
        
        # ==================== OPTIMIZED WARRANTY MANAGEMENT ====================
        # Use conditional aggregation for all months in ONE query
        
        warranty_conditions = {}
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            warranty_conditions[f'active_{i}'] = Count('id', filter=Q(
                purchase_date__lte=month_end.date(),
                expiry_date__gte=month_start.date()
            ))
            warranty_conditions[f'new_{i}'] = Count('id', filter=Q(
                created_at__gte=month_start,
                created_at__lte=month_end
            ))
            warranty_conditions[f'expired_{i}'] = Count('id', filter=Q(
                expiry_date__gte=month_start.date(),
                expiry_date__lte=month_end.date()
            ))
        
        warranty_data = Warranty.objects.filter(warranties_filter).aggregate(**warranty_conditions)
        
        warranty_management = []
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            warranty_management.append({
                'month': month_start.strftime('%b'),
                'active': warranty_data[f'active_{i}'],
                'new': warranty_data[f'new_{i}'],
                'expired': warranty_data[f'expired_{i}']
            })
        
        # ==================== OPTIMIZED CLAIMS PROCESSING ====================
        # Single query with conditional aggregation
        
        claims_conditions = {}
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            claims_conditions[f'approved_{i}'] = Count('id', filter=Q(
                status='Approved',
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ))
            claims_conditions[f'pending_{i}'] = Count('id', filter=Q(
                status='In Review',
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ))
            claims_conditions[f'rejected_{i}'] = Count('id', filter=Q(
                status='Rejected',
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ))
        
        claims_data = Claim.objects.filter(claims_filter).aggregate(**claims_conditions)
        
        claims_processing = []
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            claims_processing.append({
                'month': month_start.strftime('%b'),
                'approved': claims_data[f'approved_{i}'],
                'pending': claims_data[f'pending_{i}'],
                'rejected': claims_data[f'rejected_{i}']
            })
        
        # ==================== OPTIMIZED REVENUE VS WARRANTY COSTS ====================
        # Single query with conditional aggregation
        
        revenue_conditions = {}
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            revenue_conditions[f'revenue_{i}'] = Sum('total', filter=Q(
                date__gte=month_start,
                date__lte=month_end
            ))
        
        revenue_data = Receipt.objects.filter(receipts_filter).aggregate(**revenue_conditions)
        
        # Warranty costs
        costs_conditions = {}
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            month_end = (month_start + relativedelta(months=1)) - timedelta(seconds=1)
            
            costs_conditions[f'costs_{i}'] = Sum('actual_cost', filter=Q(
                status='Approved',
                submitted_at__gte=month_start,
                submitted_at__lte=month_end
            ))
        
        costs_data = Claim.objects.filter(claims_filter).aggregate(**costs_conditions)
        
        revenue_costs = []
        for i in range(months_count - 1, -1, -1):
            month_start = current_month_start - relativedelta(months=i)
            revenue_costs.append({
                'month': month_start.strftime('%b'),
                'revenue': float(revenue_data[f'revenue_{i}'] or 0),
                'warranty_costs': float(costs_data[f'costs_{i}'] or 0)
            })
        
        # ==================== RESPONSE ====================
        return Response({
            'summary': {
                'total_receipts': {
                    'value': summary_stats['receipts_this_month'],
                    'change': receipts_change,
                    'label': 'Total Receipts'
                },
                'active_warranties': {
                    'value': warranty_stats['active_warranties'],
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
                    'value': round(float(summary_stats['avg_receipt'] or 0), 2),
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
            },
            'query_info': {
                'note': 'Optimized with subqueries and conditional aggregation',
                'estimated_queries': '~10-15 queries (down from 66)'
            }
        })
    
    def _calculate_change(self, current, previous):
        """Calculate percentage change"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)


class RetailerAIInsightsOptimized(APIView):
    """
    OPTIMIZED AI-powered insights for retailers
    Uses efficient querying with minimal database hits
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Generate AI-powered insights for retailer analytics"""
        user = request.user
        
        # Only retailers and admins can access this
        if user.role not in ['retailer', 'admin']:
            return Response({
                'error': 'This endpoint is only available for retailers and administrators'
            }, status=403)
        
        period = request.query_params.get('period', '6months')
        
        # Determine date filter
        now = timezone.now()
        if period == '30days':
            start_date = now - timedelta(days=30)
        elif period == '90days':
            start_date = now - timedelta(days=90)
        elif period == '12months':
            start_date = now - timedelta(days=365)
        elif period == 'all':
            start_date = None
        else:  # 6months default
            start_date = now - timedelta(days=180)
        
        # Filter claims by user role
        if user.role == 'retailer':
            claims_filter = Q(warranty__receipt_item__receipt__retailer=user)
        else:  # admin
            claims_filter = Q()
        
        # Apply date filter
        if start_date:
            claims_filter &= Q(submitted_at__gte=start_date)
        
        # ==================== OPTIMIZED TOP CLAIMED PRODUCTS ====================
        # Single query with all aggregations
        
        top_claimed_products = list(Claim.objects.filter(claims_filter).values(
            product_name=F('warranty__receipt_item__product_name'),
            model=F('warranty__receipt_item__model')
        ).annotate(
            claim_count=Count('id'),
            approved_count=Count('id', filter=Q(status='Approved')),
            rejected_count=Count('id', filter=Q(status='Rejected')),
            pending_count=Count('id', filter=Q(status='In Review'))
        ).annotate(
            approval_rate=Case(
                When(claim_count=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    F('approved_count') * 100.0 / F('claim_count'),
                    output_field=IntegerField()
                )
            )
        ).order_by('-claim_count')[:10].values(
            'product_name', 'model', 'claim_count', 'approved_count',
            'rejected_count', 'pending_count', 'approval_rate'
        ))
        
        # Format response
        top_claimed_products = [
            {
                'product_name': item['product_name'],
                'model': item['model'] or 'N/A',
                'claim_count': item['claim_count'],
                'approved': item['approved_count'],
                'rejected': item['rejected_count'],
                'pending': item['pending_count'],
                'approval_rate': round(float(item['approval_rate']), 1)
            }
            for item in top_claimed_products
        ]
        
        # ==================== OPTIMIZED SLOW PROCESSING ====================
        # Single query with processing time calculation
        
        slow_processing_data = Claim.objects.filter(
            claims_filter,
            status__in=['Approved', 'Rejected']
        ).annotate(
            processing_time=ExpressionWrapper(
                F('updated_at') - F('submitted_at'),
                output_field=DurationField()
            ),
            product_name=F('warranty__receipt_item__product_name'),
            model=F('warranty__receipt_item__model')
        ).values('product_name', 'model').annotate(
            avg_processing_seconds=Avg(
                ExpressionWrapper(
                    F('processing_time'),
                    output_field=DurationField()
                )
            ),
            claim_count=Count('id')
        ).order_by('-avg_processing_seconds')[:10]
        
        slow_processing_claims = [
            {
                'product_name': item['product_name'],
                'model': item['model'] or 'N/A',
                'avg_processing_days': round(item['avg_processing_seconds'].total_seconds() / 86400, 1),
                'claim_count': item['claim_count']
            }
            for item in slow_processing_data
        ]
        
        # ==================== AI ANALYSIS ====================
        # Fetch all claims data in ONE query with prefetch
        
        all_claims = list(Claim.objects.filter(claims_filter).select_related(
            'warranty__receipt_item'
        ).values(
            'id', 'claim_number', 'issue_summary', 'detailed_description',
            'category', product_name=F('warranty__receipt_item__product_name')
        ))
        
        # Initialize AI service
        ai_service = ClaimAnalyticsAI()
        
        # Analyze claim reasons with AI
        claim_reasons_analysis = ai_service.analyze_claim_reasons(all_claims)
        
        # ==================== REJECTION REASONS ====================
        # Fetch rejected claims with notes in ONE query
        
        rejected_claims = Claim.objects.filter(
            claims_filter,
            status='Rejected'
        ).select_related('warranty__receipt_item').prefetch_related('notes')
        
        rejected_claims_data = []
        for claim in rejected_claims:
            notes = [note.content for note in claim.notes.all()]
            rejected_claims_data.append({
                'id': claim.id,
                'claim_number': claim.claim_number,
                'product_name': claim.warranty.receipt_item.product_name,
                'notes': notes
            })
        
        # Analyze rejection reasons with AI
        rejection_reasons_analysis = ai_service.analyze_rejection_reasons(rejected_claims_data)
        
        # ==================== OVERALL STATISTICS ====================
        # Single query for all stats
        
        overall_stats_data = Claim.objects.filter(claims_filter).aggregate(
            total_claims=Count('id'),
            approved_claims=Count('id', filter=Q(status='Approved')),
            rejected_claims=Count('id', filter=Q(status='Rejected')),
            pending_claims=Count('id', filter=Q(status='In Review'))
        )
        
        overall_stats = {
            'total_claims': overall_stats_data['total_claims'],
            'approved_claims': overall_stats_data['approved_claims'],
            'rejected_claims': overall_stats_data['rejected_claims'],
            'pending_claims': overall_stats_data['pending_claims'],
            'approval_rate': round(
                (overall_stats_data['approved_claims'] / overall_stats_data['total_claims'] * 100)
                if overall_stats_data['total_claims'] > 0 else 0, 1
            ),
            'rejection_rate': round(
                (overall_stats_data['rejected_claims'] / overall_stats_data['total_claims'] * 100)
                if overall_stats_data['total_claims'] > 0 else 0, 1
            )
        }
        
        # ==================== GENERATE AI SUMMARY ====================
        analytics_data = {
            'top_claimed_products': top_claimed_products,
            'slow_processing_claims': slow_processing_claims,
            'claim_reasons': claim_reasons_analysis,
            'rejection_reasons': rejection_reasons_analysis
        }
        
        ai_summary = ai_service.generate_insights_summary(analytics_data)
        
        # ==================== RESPONSE ====================
        return Response({
            'period': period,
            'generated_at': now.isoformat(),
            'overall_statistics': overall_stats,
            'top_claimed_products': top_claimed_products,
            'slow_processing_claims': slow_processing_claims,
            'claim_reasons': claim_reasons_analysis,
            'rejection_reasons': rejection_reasons_analysis,
            'ai_summary': ai_summary,
            'recommendations': self._generate_recommendations(
                top_claimed_products,
                slow_processing_claims,
                claim_reasons_analysis,
                rejection_reasons_analysis
            ),
            'query_info': {
                'note': 'Optimized with subqueries and select_related/prefetch_related',
                'estimated_queries': '~5-8 queries (highly optimized)'
            }
        })
    
    def _generate_recommendations(self, top_claimed, slow_processing, claim_reasons, rejection_reasons):
        """Generate actionable recommendations"""
        recommendations = []
        
        if top_claimed and len(top_claimed) > 0:
            top_product = top_claimed[0]
            if top_product['claim_count'] > 5:
                recommendations.append({
                    'type': 'product_quality',
                    'priority': 'high',
                    'title': f'High claim rate for {top_product["product_name"]}',
                    'description': f'This product has {top_product["claim_count"]} claims. Consider reviewing product quality or supplier.',
                    'action': 'Review supplier quality or consider alternative products'
                })
        
        if slow_processing and len(slow_processing) > 0:
            slowest = slow_processing[0]
            if slowest['avg_processing_days'] > 7:
                recommendations.append({
                    'type': 'processing_time',
                    'priority': 'medium',
                    'title': f'Slow processing for {slowest["product_name"]}',
                    'description': f'Average processing time is {slowest["avg_processing_days"]} days.',
                    'action': 'Streamline claim processing workflow'
                })
        
        if claim_reasons.get('categories') and len(claim_reasons['categories']) > 0:
            top_reason = claim_reasons['categories'][0]
            if top_reason['percentage'] > 30:
                recommendations.append({
                    'type': 'claim_pattern',
                    'priority': 'high',
                    'title': f'High incidence of {top_reason["category"]}',
                    'description': f'{top_reason["percentage"]}% of claims are related to {top_reason["category"]}.',
                    'action': 'Investigate root cause and implement preventive measures'
                })
        
        if rejection_reasons.get('rejection_reasons') and len(rejection_reasons['rejection_reasons']) > 0:
            top_rejection = rejection_reasons['rejection_reasons'][0]
            if top_rejection['percentage'] > 25:
                recommendations.append({
                    'type': 'rejection_pattern',
                    'priority': 'medium',
                    'title': f'Common rejection: {top_rejection["reason"]}',
                    'description': f'{top_rejection["percentage"]}% of rejections.',
                    'action': 'Improve customer education about warranty terms'
                })
        
        return recommendations

