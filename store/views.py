from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.conf import settings
from .models import Product, Category, CartItem, Order, SiteSettings, Brand
from decimal import Decimal
from django.contrib.auth.models import User

def index(request):
    """Homepage with latest products and special offers"""
    # Slider: Show latest 5 products so new uploads appear immediately
    latest_products = Product.objects.filter(available=True).order_by('-created_at')[:5]
    
    # Special Offers: Show ONLY discounted products
    discounted_products = Product.objects.filter(discount_percentage__gt=0, available=True)[:12]
    
    categories = Category.objects.all()[:6]
    context = {
        'slider_products': latest_products,     # For Hero Slider
        'special_offers': discounted_products,  # For 'Special Offers' Grid
        'categories': categories,
    }
    return render(request, 'store/index.html', context)


def category(request):
    """Product listing with filters"""
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()
    
    # Get all unique brands for filter
    brands = Brand.objects.all()
    
    # Filter by category
    category_slug = request.GET.get('category')
    if category_slug:
        # Removed hardcoded 'phones' -> 'smartphones' conversion for better dynamic behavior
        products = products.filter(category__slug=category_slug)
    
    # Filter by brand
    brand_name = request.GET.get('brand')
    if brand_name:
        products = products.filter(brand__name=brand_name)
    
    # Filter by search
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(brand__name__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=Decimal(min_price))
    if max_price:
        products = products.filter(price__lte=Decimal(max_price))
    
    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page = request.GET.get('page')
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    context = {
        'products': products,
        'categories': categories,
        'brands': brands,
        'selected_brand': brand_name,
        'min_price': min_price or '',
        'max_price': max_price or '',
    }
    return render(request, 'store/category_v2.html', context)


def product(request):
    """Product detail page"""
    product_id = request.GET.get('id')
    product_obj = get_object_or_404(Product, id=product_id, available=True)
    related_products = Product.objects.filter(
        category=product_obj.category,
        available=True
    ).exclude(id=product_id)[:4]
    
    context = {
        'product': product_obj,
        'related_products': related_products,
    }
    return render(request, 'store/product.html', context)


@login_required
def cart(request):
    """Shopping cart page"""
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.subtotal for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total,
    }
    return render(request, 'store/cart.html', context)


@login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    if request.method == 'POST':
        product_obj = get_object_or_404(Product, id=product_id)
        
        # Parse quantity from JSON body or POST data
        import json
        quantity = 1
        try:
            if request.body:
                data = json.loads(request.body)
                quantity = int(data.get('quantity', 1))
        except:
            pass
            
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product_obj,
            defaults={'quantity': 0} 
        )
        
        # Check stock limits
        current_qty = cart_item.quantity
        if current_qty + quantity > product_obj.stock:
            return JsonResponse({
                'success': False, 
                'message': f'Sorry, only {product_obj.stock} left in stock!'
            }, status=200) # Return 200 so frontend can handle custom message
            
        if created:
            cart_item.quantity = quantity
        else:
            cart_item.quantity += quantity
            
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{product_obj.name} added to cart',
            'cart_count': CartItem.objects.filter(user=request.user).count()
        })
    return JsonResponse({'success': False}, status=400)


@login_required
def update_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity > 0:
            if quantity > cart_item.product.stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {cart_item.product.stock} items available'
                }, status=400)

            cart_item.quantity = quantity
            cart_item.save()
            return JsonResponse({
                'success': True,
                'subtotal': float(cart_item.subtotal)
            })
        else:
            cart_item.delete()
            return JsonResponse({'success': True, 'deleted': True})
    return JsonResponse({'success': False}, status=400)


@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
        cart_item.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'store/admin_order_invoice.html', {'order': order})



@login_required
def track_order(request, order_id):
    """Track order status and timeline"""
    if request.user.is_staff:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Calculate progress for timeline
    steps = ['pending', 'processing', 'shipped', 'delivered']
    current_step_index = 0
    if order.status in steps:
        current_step_index = steps.index(order.status)
        
    context = {
        'order': order,
        'current_step_index': current_step_index,
        'steps': steps
    }
    return render(request, 'store/track_order.html', context)
