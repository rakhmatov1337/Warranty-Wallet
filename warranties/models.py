from django.db import models
from receipts.models import ReceiptItem
from django.utils import timezone

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
