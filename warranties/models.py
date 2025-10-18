from django.db import models
from receipts.models import ReceiptItem
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Warranty(models.Model):
    # Link to receipt item (which contains the product with all details)
    # OneToOneField ensures each receipt item can only have one warranty
    receipt_item = models.OneToOneField(
        ReceiptItem, 
        on_delete=models.CASCADE, 
        related_name='warranty',
        help_text='Each receipt item can only have one warranty'
    )
    
    # Warranty coverage details
    coverage_period_months = models.IntegerField(help_text="Coverage period in months")
    provider = models.CharField(max_length=255, help_text="e.g., Apple Inc. + TechMart Extended")
    coverage_terms = models.TextField(help_text="e.g., Full hardware coverage, liquid damage, theft protection")
    purchase_date = models.DateField()
    expiry_date = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.receipt_item.product_name} - {self.status}"
    
    @property
    def status(self):
        """Automatically determine status based on expiry date"""
        today = timezone.now().date()
        if today <= self.expiry_date:
            return 'Active'
        else:
            return 'Expired'
    
    @property
    def receipt(self):
        """Get receipt from receipt_item"""
        return self.receipt_item.receipt
    
    @property
    def customer(self):
        """Get customer from receipt"""
        return self.receipt_item.receipt.customer
    
    @property
    def retailer(self):
        """Get retailer from receipt"""
        return self.receipt_item.receipt.retailer
    
    @property
    def store(self):
        """Get store from receipt"""
        return self.receipt_item.receipt.store
    
    @property
    def remaining_days(self):
        """Calculate remaining days of warranty"""
        today = timezone.now().date()
        if today >= self.expiry_date:
            return 0
        return (self.expiry_date - today).days
    
    @property
    def coverage_value(self):
        """Get the purchase price from receipt item"""
        return self.receipt_item.price
    
    @property
    def claims_count(self):
        """Count of claims filed for this warranty"""
        return self.claims.count()
    
    class Meta:
        verbose_name_plural = 'Warranties'
        ordering = ['-created_at']


class CustomerWarranty(models.Model):
    """
    Manual warranty uploads by customers
    Independent of receipts - just image, name, and expiry date
    """
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='customer_warranties',
        limit_choices_to={'role': 'customer'}
    )
    
    # Basic info
    product_name = models.CharField(max_length=255, help_text="Product name")
    expiry_date = models.DateField(help_text="Warranty expiry date")
    
    # Warranty document image
    warranty_image = models.ImageField(
        upload_to='customer_warranties/%Y/%m/',
        help_text="Photo or scan of warranty document"
    )
    
    # Optional notes
    notes = models.TextField(blank=True, help_text="Additional notes about this warranty")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer Warranty'
        verbose_name_plural = 'Customer Warranties'
    
    def __str__(self):
        return f"{self.product_name} - {self.customer.email}"
    
    @property
    def is_active(self):
        """Check if warranty is still active"""
        return self.expiry_date >= timezone.now().date()
    
    @property
    def days_remaining(self):
        """Calculate days remaining until expiry"""
        if self.is_active:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return 0
    
    @property
    def status(self):
        """Get warranty status"""
        if self.is_active:
            if self.days_remaining <= 30:
                return 'Expiring Soon'
            return 'Active'
        return 'Expired'
