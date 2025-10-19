from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Store(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='stores/', blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    is_verified = models.BooleanField(
        default=False,
        help_text="Indicates if the store is verified by admin"
    )
    admins = models.ManyToManyField(User, related_name='managed_stores', limit_choices_to={'role': 'retailer'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']
