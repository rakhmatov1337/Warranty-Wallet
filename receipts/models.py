from django.db import models
from django.contrib.auth import get_user_model
from store.models import Store

User = get_user_model()

class Receipt(models.Model):
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='receipts')
    retailer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='retailer_receipts', limit_choices_to={'role': 'retailer'})
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_receipts', limit_choices_to={'role': 'customer'})
    
    # Financial details
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Transaction details
    date = models.DateField()
    time = models.TimeField(blank=True, null=True)
    payment_method = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.receipt_number} - {self.customer.email} - ${self.total}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate receipt number like RCP-2024-001
            from datetime import datetime
            year = datetime.now().year
            last_receipt = Receipt.objects.filter(receipt_number__startswith=f'RCP-{year}').order_by('-id').first()
            if last_receipt:
                last_num = int(last_receipt.receipt_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.receipt_number = f'RCP-{year}-{new_num:03d}'
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']


class ReceiptItem(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=255)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    
    # Product specifications
    color = models.CharField(max_length=100, blank=True)
    imei = models.CharField(max_length=100, blank=True, help_text="IMEI or unique identifier")
    storage = models.CharField(max_length=50, blank=True, help_text="e.g., 256GB")
    
    # Warranty details
    warranty_coverage = models.CharField(max_length=255, blank=True, help_text="e.g., 12 months manufacturer")
    warranty_expiry = models.DateField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.product_name} - {self.receipt.receipt_number}"
    
    @property
    def item_total(self):
        return self.price * self.quantity
