from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Category, Product, CartItem, Order, OrderItem, SiteSettings
from django.utils.safestring import mark_safe

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    readonly_fields = ['subtotal_display']

    def subtotal_display(self, obj):
        return f"Tk {obj.subtotal}"
    subtotal_display.short_description = "Subtotal"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    ordering = ['name']

    def product_count(self, obj):
        count = obj.products.count()
        url = (
            reverse("admin:store_product_changelist")
            + f"?category__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{} Products</a>', url, count)
    product_count.short_description = "Products"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['image_preview', 'name', 'category', 'price', 'discounted_price_display', 'stock_status', 'available', 'featured', 'created_at']
    list_filter = ['available', 'featured', 'category', 'brand', 'created_at']
    list_editable = ['price', 'available', 'featured']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    actions = ['make_unavailable', 'make_available', 'apply_10_percent_discount', 'remove_discount']
    list_per_page = 20

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Image"

    def discounted_price_display(self, obj):
        if obj.has_discount:
            return format_html(
                '<span style="color: green; font-weight: bold;">Tk {}</span> <span style="color: red; text-decoration: line-through; font-size: 0.8em;">Tk {}</span>',
                obj.discounted_price, obj.price
            )
        return f"Tk {obj.price}"
    discounted_price_display.short_description = "Price (Discounted)"
    
    def stock_status(self, obj):
        """Visual stock status with color indicators"""
        if obj.stock == 0:
            return format_html(
                '<span style="background: #fee2e2; color: #991b1b; padding: 4px 10px; border-radius: 6px; font-weight: bold; display: inline-block;">⚠ OUT OF STOCK</span>'
            )
        elif obj.stock < 10:
            return format_html(
                '<span style="background: #fef3c7; color: #92400e; padding: 4px 10px; border-radius: 6px; font-weight: 600; display: inline-block;">⚡ LOW ({} left)</span>',
                obj.stock
            )
        return format_html(
            '<span style="color: #059669; font-weight: 600;">✓ {} in stock</span>',
            obj.stock
        )
    stock_status.short_description = "Stock Status"

    @admin.action(description='Mark selected products as unavailable')
    def make_unavailable(self, request, queryset):
        queryset.update(available=False)

    @admin.action(description='Mark selected products as available')
    def make_available(self, request, queryset):
        queryset.update(available=True)

    @admin.action(description='Apply 10%% discount to selected products')
    def apply_10_percent_discount(self, request, queryset):
        queryset.update(discount_percentage=10)

    @admin.action(description='Remove discount from selected products')
    def remove_discount(self, request, queryset):
        queryset.update(discount_percentage=0)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'subtotal_display', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name']
    
    def subtotal_display(self, obj):
        return f"Tk {obj.subtotal}"
    subtotal_display.short_description = "Subtotal"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_display', 'status_badge', 'payment_status_badge', 'created_at', 'invoice_link', 'short_address']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['user__username', 'id', 'shipping_address']
    readonly_fields = ['created_at', 'updated_at', 'shipping_address']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    actions = ['mark_processing', 'mark_shipped', 'mark_delivered', 'mark_cancelled']

    def total_display(self, obj):
        return f"Tk {obj.total}"
    total_display.short_description = "Total Amount"

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px;">{}</span>',
            colors.get(obj.status, 'grey'),
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def payment_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'failed': 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.payment_status, 'grey'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = "Payment"

    def invoice_link(self, obj):
        url = reverse('admin_order_invoice', args=[obj.id])
        return mark_safe(f'<a href="{url}" class="button" target="_blank">Print Invoice</a>')
    invoice_link.short_description = "Actions"

    @admin.action(description='Mark selected orders as Processing')
    def mark_processing(self, request, queryset):
        queryset.update(status='processing')
        
    @admin.action(description='Mark selected orders as Shipped')
    def mark_shipped(self, request, queryset):
        queryset.update(status='shipped')

    @admin.action(description='Mark selected orders as Delivered')
    def mark_delivered(self, request, queryset):
        queryset.update(status='delivered')

    @admin.action(description='Mark selected orders as Cancelled')
    def mark_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        
    def short_address(self, obj):
        return format_html('<span style="white-space: pre-wrap;">{}</span>', obj.shipping_address)
    short_address.short_description = "Shipping Address"

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'email_host_user']
    
    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        if SiteSettings.objects.exists():
            return False
        return True
    def mark_delivered(self, request, queryset):
        queryset.update(status='delivered', payment_status='paid')

    @admin.action(description='Mark selected orders as Cancelled')
    def mark_cancelled(self, request, queryset):
        queryset.update(status='cancelled')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']
    list_filter = ['order__created_at']
    search_fields = ['product__name', 'order__id']
