from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .forms import CheckoutForm
from store.models import CartItem, Order, OrderItem, Product, SiteSettings
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F
from django.db import transaction

@login_required
def checkout(request):
    """Collection shipping address"""
    cart_items = CartItem.objects.filter(user=request.user)
    
    if not cart_items.exists():
        messages.error(request, 'Your cart is empty')
        return redirect('store:cart')
    
    total = sum(item.subtotal for item in cart_items)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Save shipping info to session
            request.session['shipping_address'] = f"{form.cleaned_data['full_name']}\n{form.cleaned_data['address']}\n{form.cleaned_data['city']}, {form.cleaned_data['state']} {form.cleaned_data['post_code']}\nPhone: {form.cleaned_data['phone']}"
            request.session['order_email'] = form.cleaned_data['email']
            return redirect('payment:payment_selection')
    else:
        # Pre-fill with user data if available
        initial_data = {
            'full_name': request.user.first_name + ' ' + request.user.last_name if request.user.first_name else '',
            'email': request.user.email
        }
        form = CheckoutForm(initial=initial_data)
        
    return render(request, 'payment/checkout.html', {
        'form': form,
        'total': total,
        'cart_items': cart_items
    })

@login_required
def payment_selection(request):
    """Render payment selection page"""
    cart_items = CartItem.objects.filter(user=request.user)
    
    if not cart_items.exists():
        return redirect('store:cart')
        
    total = sum(item.subtotal for item in cart_items)
    
    return render(request, 'payment/payment_selection.html', {
        'total': total,
        'cart_items': cart_items
    })

def send_order_confirmation_email(request, order, recipient_email=None):
    """Send detailed order confirmation email"""
    items_list = ""
    for item in order.items.all():
        items_list += f"- {item.product.name} x {item.quantity}: Tk {item.price}\n"
    
    # Needs update when urls are fixed
    invoice_url = request.build_absolute_uri(reverse('accounts:customer_order_invoice', args=[order.id]))
    track_url = request.build_absolute_uri(reverse('store:track_order', args=[order.id]))
    
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
        from django.core.mail import send_mail
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.email_host_user and site_settings.email_host_password:
            from django.core.mail.backends.smtp import EmailBackend
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
            recipient_list=[recipient_email or request.user.email, settings.ADMINS[0][1]],
            connection=connection, # Use custom connection if available
            fail_silently=False,
        )
        print(f"SUCCESS: Email sent to {recipient_email or request.user.email}")
    except Exception as e:
        print(f"FAILURE: Email sending failed: {e}")

@login_required
def process_payment(request):
    """Process payment selection (COD or SSLCommerz)"""
    if request.method != 'POST':
        return redirect('payment:checkout')
        
    payment_method = request.POST.get('payment_method')
    cart_items = CartItem.objects.filter(user=request.user)
    
    if not cart_items.exists():
        return redirect('store:cart')
        
    total = sum(item.subtotal for item in cart_items)
    
    
    # Validate Stock First
    for cart_item in cart_items:
        if cart_item.product.stock < cart_item.quantity:
            messages.error(request, f"Sorry, {cart_item.product.name} is out of stock (Only {cart_item.product.stock} left).")
            return redirect('store:cart')

    # Create order
    shipping_address = request.session.get('shipping_address', 'Address not provided')
    
    order = Order.objects.create(
        user=request.user,
        total=total,
        shipping_address=shipping_address,
        status='pending',
        payment_status='pending'
    )
    
    # Create order items and decrement stock atomically
    for cart_item in cart_items:
        # Atomic Stock Decrement
        Product.objects.filter(id=cart_item.product.id).update(stock=F('stock') - cart_item.quantity)
        
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            price=cart_item.product.discounted_price,
            purchase_price=cart_item.product.purchase_price
        )
        
    if payment_method == 'cod':
        # Handle Cash on Delivery
        order.payment_intent_id = 'COD'
        order.save()
        
        # Clear cart
        cart_items.delete()
        
        # Send confirmation email
        order_email = request.session.get('order_email')
        send_order_confirmation_email(request, order, recipient_email=order_email)
        
        messages.success(request, 'Order placed successfully! Please pay on delivery.')
        return redirect(f"{reverse('payment:payment_success')}?order_id={order.id}")
        
    elif payment_method == 'sslcommerz':
        # Handle SSLCommerz
        from sslcommerz_lib import SSLCOMMERZ 
        
        # Get SSLCommerz credentials from SiteSettings or settings
        try:
            site_settings = SiteSettings.objects.first()
            if site_settings and site_settings.sslcommerz_store_id:
                store_id = site_settings.sslcommerz_store_id
                store_pass = site_settings.sslcommerz_store_pass
                is_sandbox = site_settings.sslcommerz_is_sandbox
            else:
                store_id = settings.SSLCOMMERZ_STORE_ID
                store_pass = settings.SSLCOMMERZ_STORE_PASS
                is_sandbox = settings.SSLCOMMERZ_IS_SANDBOX
        except:
            store_id = settings.SSLCOMMERZ_STORE_ID
            store_pass = settings.SSLCOMMERZ_STORE_PASS
            is_sandbox = settings.SSLCOMMERZ_IS_SANDBOX
        
        sslcz = SSLCOMMERZ({
            'store_id': store_id,
            'store_pass': store_pass,
            'issandbox': is_sandbox
        })
        
        # Prepare payment data
        post_body = {
            'total_amount': float(total),
            'currency': 'BDT',
            'tran_id': f"ORDER-{order.id}",
            'success_url': request.build_absolute_uri(reverse('payment:sslcommerz_success')),
            'fail_url': request.build_absolute_uri(reverse('payment:sslcommerz_fail')),
            'cancel_url': request.build_absolute_uri(reverse('payment:sslcommerz_cancel')),
            'emi_option': 0,
            'cus_name': request.user.username,
            'cus_email': request.session.get('order_email', request.user.email),
            'cus_phone': '01700000000',  # You can add this to checkout form
            'cus_add1': shipping_address[:100],
            'cus_city': 'Dhaka',
            'cus_country': 'Bangladesh',
            'shipping_method': 'NO',
            'product_name': f'Order #{order.id}',
            'product_category': 'Electronics',
            'product_profile': 'general',
        }
        
        try:
            response = sslcz.createSession(post_body)
            
            if response.get('status') == 'SUCCESS':
                # Save transaction ID
                order.payment_intent_id = post_body['tran_id']
                order.save()
                
                return redirect(response['GatewayPageURL'])
            else:
                messages.error(request, f"Payment gateway error: {response.get('failedreason', 'Unknown error')}")
                order.delete()
                return redirect('store:cart')
                
        except Exception as e:
            messages.error(request, f'Error creating payment session: {str(e)}')
            order.delete()
            return redirect('store:cart')
            
    return redirect('store:cart')


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
            order_email = request.session.get('order_email')
            send_order_confirmation_email(request, order, recipient_email=order_email)
            
        order.status = 'processing'
        order.save()
        
        # Clear cart
        CartItem.objects.filter(user=request.user).delete()
        
        context = {'order': order}
        return render(request, 'payment/payment_success.html', context)
    
    return redirect('store:index')


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
    
    return redirect('store:cart')

# SSLCommerz Payment Gateway Callback Views

@csrf_exempt
def sslcommerz_success(request):
    """Handle successful SSLCommerz payment"""
    if request.method == 'POST':
        # Extract payment data from SSLCommerz response
        val_id = request.POST.get('val_id')
        tran_id = request.POST.get('tran_id')
        
        if not val_id or not tran_id:
            messages.error(request, 'Invalid payment response')
            return redirect('store:cart')
        
        # Extract order ID from transaction ID (format: ORDER-{id})
        try:
            order_id = int(tran_id.split('-')[1])
            order = Order.objects.get(id=order_id, payment_intent_id=tran_id)
        except (ValueError, IndexError, Order.DoesNotExist):
            messages.error(request, 'Order not found')
            return redirect('store:cart')
        
        # Check payment status from SSLCommerz POST data
        # SSLCommerz sends VALID or VALIDATED for successful payments
        payment_status = request.POST.get('status', '')
        
        if payment_status in ['VALID', 'VALIDATED']:
            # Payment successful
            order.payment_status = 'paid'
            order.status = 'processing'
            order.save()
            
            # Clear cart
            CartItem.objects.filter(user=order.user).delete()
            
            # Send confirmation email
            send_order_confirmation_email(request, order, recipient_email=order.user.email)
            
            return redirect(f"{reverse('payment:payment_success')}?order_id={order.id}")
        else:
            messages.error(request, 'Payment validation failed')
            order.delete()
            return redirect('store:cart')
    
    return redirect('store:cart')

@csrf_exempt
def sslcommerz_fail(request):
    """Handle failed SSLCommerz payment"""
    messages.error(request, 'Payment failed. Please try again.')
    return redirect('store:cart')

@csrf_exempt
def sslcommerz_cancel(request):
    """Handle cancelled SSLCommerz payment"""
    messages.warning(request, 'Payment cancelled.')
    return redirect('store:cart')
