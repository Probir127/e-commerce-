
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .forms import CheckoutForm, RegisterForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Category, CartItem, Order, OrderItem
from decimal import Decimal
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

def index(request):
    """Homepage with discounted products"""
    discounted_products = Product.objects.filter(discount_percentage__gt=0, available=True)[:8]
    categories = Category.objects.all()[:6]
    context = {
        'featured_products': discounted_products,  # Keep variable name for template compatibility
        'categories': categories,
    }
    return render(request, 'store/index.html', context)


def category(request):
    """Product listing with filters"""
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()
    
    # Get all unique brands for filter
    all_brands = Product.objects.filter(available=True).exclude(brand='').values_list('brand', flat=True).distinct().order_by('brand')
    
    # Filter by category
    category_slug = request.GET.get('category')
    if category_slug:
        # Removed hardcoded 'phones' -> 'smartphones' conversion for better dynamic behavior
        products = products.filter(category__slug=category_slug)
    
    # Filter by brand
    brand = request.GET.get('brand')
    if brand:
        products = products.filter(brand=brand)
    
    # Filter by search
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(brand__icontains=search) |
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
        'brands': all_brands,
        'selected_brand': brand,
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
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product_obj,
            defaults={'quantity': 1}
        )
        if not created:
            cart_item.quantity += 1
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


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('index')
        else:
            messages.error(request, 'Invalid username or password')
    else:
        form = AuthenticationForm()
    
    return render(request, 'store/login.html', {'form': form})


def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('index')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = RegisterForm()
    
    return render(request, 'store/register.html', {'form': form})


@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out')
    return redirect('index')


@login_required
def checkout(request):
    """Collection shipping address"""
    cart_items = CartItem.objects.filter(user=request.user)
    
    if not cart_items.exists():
        messages.error(request, 'Your cart is empty')
        return redirect('cart')
    
    total = sum(item.subtotal for item in cart_items)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Save shipping info to session
            request.session['shipping_address'] = f"{form.cleaned_data['full_name']}\n{form.cleaned_data['address']}\n{form.cleaned_data['city']}, {form.cleaned_data['state']} {form.cleaned_data['post_code']}\nPhone: {form.cleaned_data['phone']}"
            return redirect('payment_selection')
    else:
        # Pre-fill with user data if available
        initial_data = {
            'full_name': request.user.first_name + ' ' + request.user.last_name if request.user.first_name else '',
            'email': request.user.email
        }
        form = CheckoutForm(initial=initial_data)
        
    return render(request, 'store/checkout.html', {
        'form': form,
        'total': total,
        'cart_items': cart_items
    })

@login_required
def payment_selection(request):
    """Render payment selection page"""
    cart_items = CartItem.objects.filter(user=request.user)
    
    if not cart_items.exists():
        return redirect('cart')
        
    total = sum(item.subtotal for item in cart_items)
    
    return render(request, 'store/payment_selection.html', {
        'total': total,
        'cart_items': cart_items
    })

def send_order_confirmation_email(request, order):
    """Send detailed order confirmation email"""
    items_list = ""
    for item in order.items.all():
        items_list += f"- {item.product.name} x {item.quantity}: Tk {item.price}\n"
    
    invoice_url = request.build_absolute_uri(reverse('customer_order_invoice', args=[order.id]))
    track_url = request.build_absolute_uri(reverse('track_order', args=[order.id]))
    
    subject = f'Order Invoice - #{order.id}'
    message = f"""
Hi {request.user.username},

Thank you for your order! Here are your order details:

Order ID: #{order.id}
Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}
Status: {order.get_status_display()}
Payment: {order.get_payment_status_display()}

Shipping Address:
{order.shipping_address}

Items:
{items_list}
Total Amount: Tk {order.total}

You can view and print your official invoice here:
{invoice_url}

Track your order status:
{track_url}

Thank you for shopping with RB Trading!
"""
    # Try to get dynamic settings
    connection = None
    from_email = settings.DEFAULT_FROM_EMAIL
    
    try:
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.email_host_user and site_settings.email_host_password:
            from django.core.mail.backends.smtp.EmailBackend import EmailBackend
            connection = EmailBackend(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=site_settings.email_host_user,
                password=site_settings.email_host_password,
                use_tls=settings.EMAIL_USE_TLS,
                fail_silently=False
            )
            from_email = site_settings.email_host_user
    except Exception as e:
        print(f"Using default email settings. Dynamic config error: {e}")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[request.user.email, settings.ADMINS[0][1]],
            connection=connection, # Use custom connection if available
            fail_silently=False,
        )
        print(f"SUCCESS: Email sent to {request.user.email}")
    except Exception as e:
        print(f"FAILURE: Email sending failed: {e}")

@login_required
def process_payment(request):
    """Process payment selection (COD or Stripe)"""
    if request.method != 'POST':
        return redirect('checkout')
        
    payment_method = request.POST.get('payment_method')
    cart_items = CartItem.objects.filter(user=request.user)
    
    if not cart_items.exists():
        return redirect('cart')
        
    total = sum(item.subtotal for item in cart_items)
    
    
    # Create order
    shipping_address = request.session.get('shipping_address', 'Address not provided')
    
    order = Order.objects.create(
        user=request.user,
        total=total,
        shipping_address=shipping_address,
        status='pending',
        payment_status='pending'
    )
    
    # Create order items
    for cart_item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            price=cart_item.product.discounted_price
        )
        
    if payment_method == 'cod':
        # Handle Cash on Delivery
        order.payment_intent_id = 'COD'
        order.save()
        
        # Clear cart
        cart_items.delete()
        
        # Send confirmation email
        send_order_confirmation_email(request, order)
        
        messages.success(request, 'Order placed successfully! Please pay on delivery.')
        return redirect(f"{reverse('payment_success')}?order_id={order.id}")
        
    elif payment_method == 'stripe':
        # Handle Stripe
        line_items = []
        for cart_item in cart_items:
            line_items.append({
                'price_data': {
                    'currency': 'bdt',
                    'product_data': {
                        'name': cart_item.product.name,
                    },
                    'unit_amount': int(cart_item.product.discounted_price * 100),
                },
                'quantity': cart_item.quantity,
            })

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri(reverse('payment_success')) + f'?order_id={order.id}&session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=request.build_absolute_uri(reverse('payment_cancel')) + '?order_id=' + str(order.id),
                metadata={
                    'order_id': order.id
                }
            )
            return redirect(checkout_session.url)
        except Exception as e:
            messages.error(request, f'Error creating payment session: {str(e)}')
            return redirect('cart')
            
    return redirect('cart')


@login_required
def payment_success(request):
    """Handle successful payment"""
    order_id = request.GET.get('order_id')
    
    if order_id:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Only mark as paid if it's a Stripe payment (not COD)
        if order.payment_intent_id != 'COD' and order.payment_status != 'paid':
            order.payment_status = 'paid'
            
            # Send confirmation email for Stripe
            send_order_confirmation_email(request, order)
            
        order.status = 'processing'
        order.save()
        
        # Clear cart
        CartItem.objects.filter(user=request.user).delete()
        
        context = {'order': order}
        return render(request, 'store/payment_success.html', context)
    
    return redirect('index')


@login_required
def payment_cancel(request):
    """Handle cancelled payment"""
    order_id = request.GET.get('order_id')
    
    if order_id:
        # Delete the cancelled order
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            order.delete()
            messages.info(request, 'Payment cancelled. Your order has been removed.')
        except Order.DoesNotExist:
            pass
    
    return redirect('cart')


@login_required
def profile(request):
    """User profile and order history"""
    # Only show orders that haven't been 'cleared' by the customer
    orders = Order.objects.filter(user=request.user, visible_to_customer=True).order_by('-created_at')
    context = {
        'orders': orders,
        'user': request.user
    }
    return render(request, 'store/profile.html', context)

@login_required
def clear_history(request):
    """Soft delete all order history for the user"""
    if request.method == 'POST':
        # Hide all orders for this user from their view
        Order.objects.filter(user=request.user).update(visible_to_customer=False)
        messages.success(request, 'Order history cleared successfully.')
    return redirect('profile')

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'store/admin_order_invoice.html', {'order': order})

@login_required
def customer_order_invoice(request, order_id):
    """Allow customers to view their own invoices"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/admin_order_invoice.html', {'order': order})

@login_required
def cancel_order(request, order_id):
    """Allow customers to cancel their own order if eligible"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status in ['pending', 'processing']:
        order.status = 'cancelled'
        order.save()
        
        # Notify Admin of cancellation
        try:
            send_mail(
                subject=f'Order Cancelled - #{order.id}',
                message=f'Order #{order.id} has been cancelled by user {request.user.username}.\nAmount: Tk {order.total}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin[1] for admin in settings.ADMINS],
                fail_silently=True,
            )
        except Exception:
            pass
            
        messages.success(request, 'Order has been cancelled successfully.')
    else:
        messages.error(request, 'Order cannot be cancelled at this stage.')
        
    return redirect('profile')

@login_required
def track_order(request, order_id):
    """Track order status and timeline"""
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
