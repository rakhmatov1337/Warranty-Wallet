from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Claim, ClaimNote, ClaimAttachment
from .serializers import (
    ClaimListSerializer, ClaimDetailSerializer, ClaimCreateSerializer,
    ClaimUpdateSerializer, ClaimNoteSerializer, ClaimAttachmentSerializer,
    CustomerClaimCreateSerializer, CustomerClaimListSerializer
)
from django.db.models import Q, Count, Avg, Sum, F, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta
import csv
from django.http import HttpResponse
from notifications.utils import notify_new_claim, notify_claim_status_update, notify_claim_note_added, notify_claim_attachment_added


class IsRetailerOrAdminForUpdate(permissions.BasePermission):
    """
    Customers and retailers can create claims and upload attachments
    Only retailers and admins can update claims and add notes
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Anyone authenticated can view and create
        if view.action in ['list', 'retrieve', 'create']:
            return True
        
        # Both customers and retailers can upload attachments, view attachments, and download claims
        if view.action in ['upload_attachment', 'attachments', 'download']:
            return True
        
        # Only retailers and admins can update claims and add notes
        if view.action in ['update', 'partial_update', 'add_note']:
            return request.user.role in ['retailer', 'admin']
        
        return False
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admins can do anything
        if user.role == 'admin':
            return True
        
        # Retailers can manage claims for their warranties
        if user.role == 'retailer':
            return obj.retailer == user
        
        # Customers can view and upload attachments to their own claims
        if user.role == 'customer':
            return obj.customer == user
        
        return False


class ClaimViewSet(viewsets.ModelViewSet):
    permission_classes = [IsRetailerOrAdminForUpdate]
    # No DELETE allowed
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']
    
    def get_queryset(self):
        user = self.request.user
        
        # Base queryset with all related data
        queryset = Claim.objects.select_related(
            'warranty',
            'warranty__receipt_item',
            'warranty__receipt_item__receipt',
            'warranty__receipt_item__receipt__customer',
            'warranty__receipt_item__receipt__retailer',
            'warranty__receipt_item__receipt__store',
            'created_by'
        ).prefetch_related('notes', 'attachments')
        
        # Filter based on user role
        if user.role == 'admin':
            pass  # Admins see all
        elif user.role == 'retailer':
            queryset = queryset.filter(warranty__receipt_item__receipt__retailer=user)
        elif user.role == 'customer':
            queryset = queryset.filter(warranty__receipt_item__receipt__customer=user)
        else:
            return Claim.objects.none()
        
        # Apply search filter
        # Search by customer, product, or issue (matches UI placeholder)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(claim_number__icontains=search) |
                Q(issue_summary__icontains=search) |
                Q(detailed_description__icontains=search) |
                Q(warranty__receipt_item__product_name__icontains=search) |
                Q(warranty__receipt_item__model__icontains=search) |
                Q(warranty__receipt_item__serial_number__icontains=search) |
                Q(warranty__receipt_item__imei__icontains=search) |
                Q(warranty__receipt_item__receipt__customer__email__icontains=search) |
                Q(warranty__receipt_item__receipt__customer__first_name__icontains=search) |
                Q(warranty__receipt_item__receipt__customer__last_name__icontains=search) |
                Q(warranty__receipt_item__receipt__customer__username__icontains=search)
            )
        
        # Apply status filter
        status_filter = self.request.query_params.get('status', None)
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Apply priority filter
        priority_filter = self.request.query_params.get('priority', None)
        if priority_filter and priority_filter != 'all':
            queryset = queryset.filter(priority=priority_filter)
        
        # Apply category filter
        category_filter = self.request.query_params.get('category', None)
        if category_filter and category_filter != 'all':
            queryset = queryset.filter(category=category_filter)
        
        return queryset.order_by('-submitted_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ClaimCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClaimUpdateSerializer
        elif self.action == 'retrieve':
            return ClaimDetailSerializer
        return ClaimListSerializer
    
    def perform_create(self, serializer):
        """Override to send notification when claim is created"""
        claim = serializer.save()
        # Notify retailer about new claim
        notify_new_claim(claim, actor=self.request.user)
        return claim
    
    def perform_update(self, serializer):
        """Override to send notification when claim status is updated"""
        claim = serializer.instance
        old_status = claim.status
        
        # Save the update
        updated_claim = serializer.save()
        
        # Check if status changed
        if old_status != updated_claim.status:
            # Notify customer about status change
            notify_claim_status_update(updated_claim, actor=self.request.user, old_status=old_status, new_status=updated_claim.status)
        
        return updated_claim
    
    def list(self, request, *args, **kwargs):
        """
        List claims with statistics included
        Matches UI: Pending Review, In Review, Approved, Avg Response
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate statistics for all claims (without filters except role-based)
        user = request.user
        if user.role == 'admin':
            stats_queryset = Claim.objects.all()
        elif user.role == 'retailer':
            stats_queryset = Claim.objects.filter(warranty__receipt_item__receipt__retailer=user)
        elif user.role == 'customer':
            stats_queryset = Claim.objects.filter(warranty__receipt_item__receipt__customer=user)
        else:
            stats_queryset = Claim.objects.none()
        
        # Count by status
        pending_review_count = stats_queryset.filter(status='In Review').count()
        in_review_count = pending_review_count  # Same as pending (for UI compatibility)
        approved_count = stats_queryset.filter(status='Approved').count()
        rejected_count = stats_queryset.filter(status='Rejected').count()
        
        # Calculate average response time (in days)
        # Time from submission to resolution (Approved/Rejected status)
        resolved_claims = stats_queryset.filter(status__in=['Approved', 'Rejected'])
        
        if resolved_claims.exists():
            total_days = 0
            count = 0
            for claim in resolved_claims:
                # Time difference between submission and last update
                time_diff = claim.updated_at - claim.submitted_at
                total_days += time_diff.total_seconds() / 86400  # Convert to days
                count += 1
            avg_response_days = round(total_days / count, 1) if count > 0 else 0
        else:
            avg_response_days = 0
        
        # Paginate claims
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['statistics'] = {
                'pending_review': pending_review_count,
                'in_review': in_review_count,
                'approved': approved_count,
                'rejected': rejected_count,
                'avg_response_days': avg_response_days
            }
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'statistics': {
                'pending_review': pending_review_count,
                'in_review': in_review_count,
                'approved': approved_count,
                'rejected': rejected_count,
                'avg_response_days': avg_response_days
            },
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """
        Add an internal note to a claim (retailer/admin only)
        """
        claim = self.get_object()
        serializer = ClaimNoteSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            note = serializer.save(claim=claim, author=request.user)
            # Notify customer about new note
            notify_claim_note_added(claim, note, actor=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_attachment(self, request, pk=None):
        """
        Upload an attachment to a claim
        Both customers and retailers can upload attachments
        """
        claim = self.get_object()
        
        # Check if file is provided
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create attachment
        attachment = ClaimAttachment.objects.create(
            claim=claim,
            file=file,
            file_name=file.name,
            file_size=file.size,
            uploaded_by=request.user
        )
        
        # Notify the other party about new attachment
        notify_claim_attachment_added(claim, attachment, actor=request.user)
        
        serializer = ClaimAttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def attachments(self, request, pk=None):
        """
        List all attachments for a claim
        """
        claim = self.get_object()
        attachments = claim.attachments.all()
        serializer = ClaimAttachmentSerializer(attachments, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download single claim as CSV with all details
        """
        claim = self.get_object()
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="claim_{claim.claim_number}.csv"'
        
        writer = csv.writer(response)
        
        # Claim Header Information
        writer.writerow(['CLAIM DETAILS'])
        writer.writerow(['Claim Number', claim.claim_number])
        writer.writerow(['Status', claim.status])
        writer.writerow(['Priority', claim.priority])
        writer.writerow(['Category', claim.category])
        writer.writerow(['Submitted Date', claim.submitted_at.strftime('%Y-%m-%d %H:%M')])
        writer.writerow(['Last Updated', claim.updated_at.strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])
        
        # Issue Details
        writer.writerow(['ISSUE INFORMATION'])
        writer.writerow(['Issue Summary', claim.issue_summary])
        writer.writerow(['Detailed Description', claim.detailed_description])
        writer.writerow([])
        
        # Product Information
        writer.writerow(['PRODUCT INFORMATION'])
        writer.writerow(['Product Name', claim.product_name])
        writer.writerow(['Model', claim.warranty.receipt_item.model or 'N/A'])
        writer.writerow(['Serial Number', claim.warranty.receipt_item.serial_number or 'N/A'])
        writer.writerow(['IMEI', claim.warranty.receipt_item.imei or 'N/A'])
        writer.writerow(['Purchase Date', claim.warranty.purchase_date])
        writer.writerow([])
        
        # Customer Information
        writer.writerow(['CUSTOMER INFORMATION'])
        writer.writerow(['Name', claim.customer.get_full_name() or claim.customer.username])
        writer.writerow(['Email', claim.customer.email])
        writer.writerow([])
        
        # Retailer/Assigned Information
        writer.writerow(['ASSIGNED TO'])
        writer.writerow(['Name', claim.assigned_to.get_full_name() or claim.assigned_to.username])
        writer.writerow(['Email', claim.assigned_to.email])
        writer.writerow(['Store', claim.warranty.store.name])
        writer.writerow([])
        
        # Cost Information
        writer.writerow(['COST INFORMATION'])
        writer.writerow(['Estimated Cost', f'${claim.estimated_cost}' if claim.estimated_cost else 'Not set'])
        writer.writerow(['Actual Cost', f'${claim.actual_cost}' if claim.actual_cost else 'Not set'])
        writer.writerow([])
        
        # Warranty Information
        writer.writerow(['WARRANTY INFORMATION'])
        writer.writerow(['Status', claim.warranty.status])
        writer.writerow(['Coverage Period', f'{claim.warranty.coverage_period_months} months'])
        writer.writerow(['Expiry Date', claim.warranty.expiry_date])
        writer.writerow(['Remaining Days', claim.warranty.remaining_days])
        writer.writerow(['Provider', claim.warranty.provider])
        writer.writerow([])
        
        # Notes
        notes = claim.notes.all()
        if notes:
            writer.writerow(['INTERNAL NOTES'])
            writer.writerow(['Date', 'Author', 'Content'])
            for note in notes:
                author_name = note.author.get_full_name() or note.author.email if note.author else 'Unknown'
                writer.writerow([
                    note.created_at.strftime('%Y-%m-%d %H:%M'),
                    author_name,
                    note.content
                ])
            writer.writerow([])
        
        # Attachments
        attachments = claim.attachments.all()
        if attachments:
            writer.writerow(['ATTACHMENTS'])
            writer.writerow(['File Name', 'Size', 'Uploaded By', 'Upload Date'])
            for attachment in attachments:
                uploader_name = attachment.uploaded_by.get_full_name() or attachment.uploaded_by.email if attachment.uploaded_by else 'Unknown'
                writer.writerow([
                    attachment.file_name,
                    attachment.file_size_display,
                    uploader_name,
                    attachment.uploaded_at.strftime('%Y-%m-%d %H:%M')
                ])
        
        return response
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export all claims to CSV
        """
        queryset = self.get_queryset()
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="claims_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Claim Number', 'Product', 'Customer', 'Status', 'Priority',
            'Category', 'Issue Summary', 'Submitted Date', 'Assigned To',
            'Estimated Cost', 'Actual Cost'
        ])
        
        for claim in queryset:
            writer.writerow([
                claim.claim_number,
                claim.product_name,
                claim.customer.email,
                claim.status,
                claim.priority,
                claim.category,
                claim.issue_summary,
                claim.submitted_at.strftime('%Y-%m-%d'),
                claim.assigned_to.email if claim.assigned_to else '-',
                claim.estimated_cost or '',
                claim.actual_cost or ''
            ])
        
        return response


# ==================== CUSTOMER-FACING VIEWS ====================

class CustomerClaimCreateView(generics.CreateAPIView):
    """
    Customer mobile app claim creation endpoint (JSON only)
    Use separate endpoint to add images after claim creation
    """
    serializer_class = CustomerClaimCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Only customers can create claims through this endpoint
        if request.user.role != 'customer':
            return Response({'error': 'Only customers can use this endpoint'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        
        # Notify retailer about new claim
        notify_new_claim(claim, actor=request.user)
        
        # Return detailed claim response
        from .serializers import ClaimDetailSerializer
        response_serializer = ClaimDetailSerializer(claim, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CustomerClaimListView(generics.ListAPIView):
    """
    Customer mobile app claims list endpoint
    """
    serializer_class = CustomerClaimListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Only customers can use this endpoint
        if user.role != 'customer':
            return Claim.objects.none()
        
        return Claim.objects.filter(
            warranty__receipt_item__receipt__customer=user
        ).select_related(
            'warranty__receipt_item__receipt__store'
        ).order_by('-submitted_at')


class CustomerClaimDetailView(generics.RetrieveAPIView):
    """
    Customer mobile app claim detail endpoint
    """
    serializer_class = ClaimDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Only customers can use this endpoint
        if user.role != 'customer':
            return Claim.objects.none()
        
        return Claim.objects.filter(
            warranty__receipt_item__receipt__customer=user
        ).select_related(
            'warranty',
            'warranty__receipt_item',
            'warranty__receipt_item__receipt',
            'warranty__receipt_item__receipt__customer',
            'warranty__receipt_item__receipt__retailer',
            'warranty__receipt_item__receipt__store',
            'created_by'
        ).prefetch_related('notes', 'attachments')


class CustomerClaimAddAttachmentView(generics.CreateAPIView):
    """
    Customer endpoint to add images/files to their claim
    """
    serializer_class = ClaimAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def create(self, request, *args, **kwargs):
        user = request.user
        claim_id = kwargs.get('pk')
        
        # Only customers can use this endpoint
        if user.role != 'customer':
            return Response({'error': 'Only customers can use this endpoint'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get the claim and verify ownership
        try:
            claim = Claim.objects.select_related('warranty__receipt_item__receipt').get(
                id=claim_id,
                warranty__receipt_item__receipt__customer=user
            )
        except Claim.DoesNotExist:
            return Response({'error': 'Claim not found or does not belong to you'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if file is provided
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size > max_size:
            return Response({'error': 'File exceeds maximum size of 10MB'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check maximum attachments (max 10 per claim)
        current_attachments = claim.attachments.count()
        if current_attachments >= 10:
            return Response({'error': 'Maximum 10 attachments allowed per claim'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create attachment
        attachment = ClaimAttachment.objects.create(
            claim=claim,
            file=file,
            file_name=file.name,
            file_size=file.size,
            uploaded_by=user
        )
        
        # Notify the other party about new attachment
        notify_claim_attachment_added(claim, attachment, actor=user)
        
        serializer = self.get_serializer(attachment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
