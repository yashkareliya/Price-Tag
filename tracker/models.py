from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    url = models.URLField()
    image_url = models.URLField(max_length=500, null=True, blank=True)
    currency = models.CharField(max_length=5, default='₹')
    target_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_below_threshold(self):
        if self.current_price is not None:
            return self.current_price <= self.target_price
        return False

class PriceHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.product.name} - {self.price} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Price History'
