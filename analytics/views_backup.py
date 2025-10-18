from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from receipts.models import Receipt, ReceiptItem
from warranties.models import Warranty
from claims.models import Claim, ClaimNote
from django.db.models import Avg, Count, Sum, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from .ai_service import ClaimAnalyticsAI


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


class RetailerAIInsights(APIView):
    """
    AI-powered insights for retailers
    Analyzes:
    1. Which products are being submitted for claims the most
    2. Which products' claim processes are taking the most time
    3. Reasons for product claims (AI categorized)
    4. Reasons for claim rejections (AI analyzed from notes)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Generate AI-powered insights for retailer analytics
        Query params:
        - period: '30days', '90days', '6months' (default), '12months', 'all'
        """
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
        
        # Apply date filter if specified
        if start_date:
            claims_filter &= Q(submitted_at__gte=start_date)
        
        # ==================== 1. TOP CLAIMED PRODUCTS ====================
        # Get products with most claims
        claims_by_product = Claim.objects.filter(claims_filter).values(
            product_name=F('warranty__receipt_item__product_name'),
            model=F('warranty__receipt_item__model')
        ).annotate(
            claim_count=Count('id'),
            approved_count=Count('id', filter=Q(status='Approved')),
            rejected_count=Count('id', filter=Q(status='Rejected')),
            pending_count=Count('id', filter=Q(status='In Review'))
        ).order_by('-claim_count')[:10]
        
        top_claimed_products = [
            {
                'product_name': item['product_name'],
                'model': item['model'] or 'N/A',
                'claim_count': item['claim_count'],
                'approved': item['approved_count'],
                'rejected': item['rejected_count'],
                'pending': item['pending_count'],
                'approval_rate': round((item['approved_count'] / item['claim_count'] * 100), 1) if item['claim_count'] > 0 else 0
            }
            for item in claims_by_product
        ]
        
        # ==================== 2. SLOW PROCESSING CLAIMS ====================
        # Claims taking longest to process (resolved claims only)
        resolved_claims = Claim.objects.filter(
            claims_filter,
            status__in=['Approved', 'Rejected']
        ).annotate(
            processing_time=ExpressionWrapper(
                F('updated_at') - F('submitted_at'),
                output_field=DurationField()
            )
        ).values(
            product_name=F('warranty__receipt_item__product_name'),
            model=F('warranty__receipt_item__model')
        ).annotate(
            avg_processing_time=Avg('processing_time'),
            claim_count=Count('id')
        ).order_by('-avg_processing_time')[:10]
        
        slow_processing_claims = []
        for item in resolved_claims:
            avg_seconds = item['avg_processing_time'].total_seconds()
            avg_days = round(avg_seconds / 86400, 1)
            
            slow_processing_claims.append({
                'product_name': item['product_name'],
                'model': item['model'] or 'N/A',
                'avg_processing_days': avg_days,
                'claim_count': item['claim_count']
            })
        
        # ==================== 3. AI ANALYSIS OF CLAIM REASONS ====================
        # Get all claims with their descriptions for AI analysis
        all_claims = Claim.objects.filter(claims_filter).select_related(
            'warranty__receipt_item'
        ).values(
            'id',
            'claim_number',
            'issue_summary',
            'detailed_description',
            'category',
            product_name=F('warranty__receipt_item__product_name')
        )
        
        claims_data = list(all_claims)
        
        # Initialize AI service
        ai_service = ClaimAnalyticsAI()
        
        # Analyze claim reasons with AI
        claim_reasons_analysis = ai_service.analyze_claim_reasons(claims_data)
        
        # ==================== 4. AI ANALYSIS OF REJECTION REASONS ====================
        # Get rejected claims with notes
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
        
        # ==================== 5. OVERALL STATISTICS ====================
        total_claims = Claim.objects.filter(claims_filter).count()
        approved_claims = Claim.objects.filter(claims_filter, status='Approved').count()
        rejected_claims_count = Claim.objects.filter(claims_filter, status='Rejected').count()
        pending_claims = Claim.objects.filter(claims_filter, status='In Review').count()
        
        overall_stats = {
            'total_claims': total_claims,
            'approved_claims': approved_claims,
            'rejected_claims': rejected_claims_count,
            'pending_claims': pending_claims,
            'approval_rate': round((approved_claims / total_claims * 100), 1) if total_claims > 0 else 0,
            'rejection_rate': round((rejected_claims_count / total_claims * 100), 1) if total_claims > 0 else 0
        }
        
        # ==================== 6. GENERATE AI SUMMARY ====================
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
            )
        })
    
    def _generate_recommendations(self, top_claimed, slow_processing, claim_reasons, rejection_reasons):
        """
        Generate actionable recommendations based on the analytics
        """
        recommendations = []
        
        # Recommendation based on top claimed products
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
        
        # Recommendation based on slow processing
        if slow_processing and len(slow_processing) > 0:
            slowest = slow_processing[0]
            if slowest['avg_processing_days'] > 7:
                recommendations.append({
                    'type': 'processing_time',
                    'priority': 'medium',
                    'title': f'Slow processing for {slowest["product_name"]}',
                    'description': f'Average processing time is {slowest["avg_processing_days"]} days. This may affect customer satisfaction.',
                    'action': 'Streamline claim processing workflow or allocate more resources'
                })
        
        # Recommendation based on claim reasons
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
        
        # Recommendation based on rejection reasons
        if rejection_reasons.get('rejection_reasons') and len(rejection_reasons['rejection_reasons']) > 0:
            top_rejection = rejection_reasons['rejection_reasons'][0]
            if top_rejection['percentage'] > 25:
                recommendations.append({
                    'type': 'rejection_pattern',
                    'priority': 'medium',
                    'title': f'Common rejection reason: {top_rejection["reason"]}',
                    'description': f'{top_rejection["percentage"]}% of rejections are due to {top_rejection["reason"]}.',
                    'action': 'Improve customer education about warranty terms and coverage'
                })
        
        return recommendations
