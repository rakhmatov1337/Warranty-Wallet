from django.db import models
from warranties.models import Warranty
from django.contrib.auth import get_user_model

User = get_user_model()

class Claim(models.Model):
    STATUS_CHOICES = [
        ('In Review', 'In Review'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]
    CATEGORY_CHOICES = [
        ('Accidental Damage', 'Accidental Damage'),
        ('Manufacturing Defect', 'Manufacturing Defect'),
        ('Normal Wear', 'Normal Wear'),
        ('Malfunction', 'Malfunction'),
        ('Other', 'Other'),
    ]

    claim_number = models.CharField(max_length=50, unique=True, blank=True)
    warranty = models.ForeignKey(Warranty, on_delete=models.CASCADE, related_name='claims')
    
    # Issue details
    issue_summary = models.CharField(max_length=255, help_text="Brief summary of the issue")
    detailed_description = models.TextField(help_text="Detailed description of the issue")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    
    # Status and priority
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='In Review')
    
    # Costs
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_claims')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.claim_number} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.claim_number:
            from datetime import datetime
            year = datetime.now().year
            last_claim = Claim.objects.filter(claim_number__startswith=f'CLM-{year}').order_by('-id').first()
            if last_claim:
                last_num = int(last_claim.claim_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.claim_number = f'CLM-{year}-{new_num:03d}'
        super().save(*args, **kwargs)
    
    @property
    def customer(self):
        """Get customer from warranty receipt"""
        return self.warranty.customer
    
    @property
    def retailer(self):
        """Get retailer from warranty receipt"""
        return self.warranty.retailer
    
    @property
    def assigned_to(self):
        """Automatically assigned to the retailer who needs to handle the claim"""
        return self.retailer
    
    @property
    def product_name(self):
        """Get product name from warranty"""
        return self.warranty.receipt_item.product_name
    
    class Meta:
        ordering = ['-submitted_at']


class ClaimNote(models.Model):
    """Internal notes for team communication"""
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Note on {self.claim.claim_number} by {self.author}"


class ClaimAttachment(models.Model):
    """Documents and images related to a claim"""
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='claim_attachments/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.claim.claim_number}"
    
    def save(self, *args, **kwargs):
        # Automatically set file_name and file_size if not provided
        if self.file and not self.file_name:
            self.file_name = self.file.name
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    @property
    def file_size_display(self):
        """Convert file size to human-readable format"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
