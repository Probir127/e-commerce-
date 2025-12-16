from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    
    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    # brand = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Cost of goods (for profit calculation)')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Discount percentage (0-100)')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.IntegerField(default=0)
    available = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    @property
    def in_stock(self):
        return self.stock > 0
    
    @property
    def discounted_price(self):
        """Calculate price after discount"""
        if self.discount_percentage > 0:
            discount_amount = self.price * (self.discount_percentage / 100)
            return self.price - discount_amount
        return self.price
    
    @property
    def has_discount(self):
        """Check if product has a discount"""
        return self.discount_percentage > 0


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'product')
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def subtotal(self):
        return self.quantity * self.product.discounted_price


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    shipping_address = models.TextField()
    visible_to_customer = models.BooleanField(default=True, help_text="If false, hides order from customer profile (soft delete)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    price = models.DecimalField(max_digits=10, decimal_places=2)  # Store price at time of order
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0) # Store cost at time of order
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def subtotal(self):
        return self.quantity * self.price

    @property
    def profit(self):
        return (self.price - self.purchase_price) * self.quantity


class SiteSettings(models.Model):
    """Singleton model for site-wide settings"""
    email_host_user = models.CharField(
        max_length=255, 
        help_text="Your Gmail address (e.g., yourname@gmail.com). Acts as the sender."
    )
    email_host_password = models.CharField(
        max_length=255, 
        help_text="Your 16-character App Password. Go to Google Account > Security > 2-Step Verification > App Passwords to generate one."
    )
    
    # SSLCommerz Payment Gateway Settings
    sslcommerz_store_id = models.CharField(
        max_length=100, 
        blank=True,
        help_text="SSLCommerz Store ID (for production use real credentials)"
    )
    sslcommerz_store_pass = models.CharField(
        max_length=200, 
        blank=True,
        help_text="SSLCommerz Store Password"
    )
    sslcommerz_is_sandbox = models.BooleanField(
        default=True,
        help_text="Enable sandbox mode for testing"
    )
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteSettings.objects.exists():
            return
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Site Configuration"


class VerificationCode(models.Model):
    """Store email verification codes for new user registrations"""
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.email} - {self.code}"
    
    class Meta:
        ordering = ['-created_at']


    class Meta:
        ordering = ['-created_at']


class AccountingEntry(models.Model):
    ENTRY_TYPES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
    )
    
    date = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    related_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_entries')
    
    class Meta:
        verbose_name_plural = 'Accounting Entries'
        ordering = ['-date']
        
    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} - {self.description}: Tk {self.amount}"


class FinancialReport(Order):
    class Meta:
        proxy = True
        verbose_name = 'Financial Report'
        verbose_name_plural = 'Financial Reports'
