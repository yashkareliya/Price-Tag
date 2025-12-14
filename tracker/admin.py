from django.contrib import admin
from .models import Product, PriceHistory

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'current_price', 'target_price', 'is_active', 'last_checked')
    list_filter = ('is_active', 'currency', 'created_at')
    search_fields = ('name', 'url', 'user__email')
    readonly_fields = ('created_at', 'last_checked')

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'price', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('product__name',)
