"""
Customer-uploaded warranty model
Allows customers to manually upload warranty documents
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


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

