from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail, get_connection
from .forms import RegisterForm
from store.models import SiteSettings, VerificationCode, Order

def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('store:index')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('store:index')
        else:
            # Only add custom message for inactive users
            username = request.POST.get('username')
            if username:
                try:
                    user = User.objects.filter(username=username).first()
                    if user and not user.is_active:
                        messages.error(request, 'Please verify your email first. Check your inbox for the verification code.')
                except Exception:
                    pass  # Form will show default error
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('store:index')
    
    if request.method == 'POST':
        # Check for and remove existing inactive users to allow overwrite
        username = request.POST.get('username')
        email = request.POST.get('email')
        
        if username:
            User.objects.filter(username=username, is_active=False).delete()
        if email:
            User.objects.filter(email=email, is_active=False).delete()

        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False # Deactivate until email verified
            user.save()
            
            # Generate 6-digit verification code
            import random
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Store code in database
            VerificationCode.objects.filter(email=user.email).delete()  # Remove old codes
            VerificationCode.objects.create(email=user.email, code=code)
            
            # Send verification email with code
            subject = 'Your Verification Code - RB Trading'
            message = f"""
Hi {user.username},

Your verification code is: {code}

This code will expire in 10 minutes.

If you did not register, please ignore this email.
"""
            # Try to get dynamic settings for email
            connection = None
            from_email = settings.DEFAULT_FROM_EMAIL
            try:
                site_settings = SiteSettings.objects.first()
                if site_settings and site_settings.email_host_user and site_settings.email_host_password:
                    connection = get_connection(
                        host=settings.EMAIL_HOST,
                        port=settings.EMAIL_PORT,
                        username=site_settings.email_host_user,
                        password=site_settings.email_host_password,
                        use_tls=settings.EMAIL_USE_TLS,
                        fail_silently=False
                    )
                    from_email = site_settings.email_host_user
            except Exception as e:
                print(f"SiteSettings error: {e}")

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,
                    recipient_list=[user.email],
                    connection=connection,
                    fail_silently=False,
                )
                messages.success(request, 'Please check your email for a verification code.')
            except Exception as e:
                messages.error(request, f'Account created but error sending email. Please contact support.')
                
            # Store email in session for verification page
            request.session['pending_verification_email'] = user.email
            return redirect('accounts:verify_email') # Updated URL name
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = RegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request):
    """Verify email with  6-digit code"""
    email = request.session.get('pending_verification_email')
    
    if not email:
        messages.error(request, 'No pending verification found.')
        return redirect('accounts:register')
    
    if request.method == 'POST':
        entered_code = request.POST.get('code', '').strip()
        
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            # Find the most recent code for this email
            verification = VerificationCode.objects.filter(email=email).latest('created_at')
            
            # Check if code expired (10 minutes)
            expiry_time = verification.created_at + timedelta(minutes=10)
            if timezone.now() > expiry_time:
                messages.error(request, 'Verification code has expired. Please register again.')
                User.objects.filter(email=email, is_active=False).delete()
                del request.session['pending_verification_email']
                return redirect('accounts:register')
            
            # Check if code matches
            if verification.code == entered_code:
                # Activate user - get the most recent one if duplicates exist
                user = User.objects.filter(email=email, is_active=False).order_by('-date_joined').first()
                
                if not user:
                    # Try getting active user (edge case)
                    user = User.objects.filter(email=email).order_by('-date_joined').first()
                    if not user:
                        messages.error(request, 'User not found. Please register again.')
                        return redirect('accounts:register')
                
                # Delete any other duplicate inactive users with same email
                User.objects.filter(email=email, is_active=False).exclude(id=user.id).delete()
                
                user.is_active = True
                user.save()
                
                # Clean up
                VerificationCode.objects.filter(email=email).delete()
                del request.session['pending_verification_email']
                
                # Log user in
                login(request, user)
                messages.success(request, 'Your account has been activated successfully!')
                return redirect('store:index')
            else:
                messages.error(request, 'Invalid verification code. Please try again.')
        
        except VerificationCode.DoesNotExist:
            messages.error(request, 'No verification code found. Please register again.')
            return redirect('accounts:register')
        except User.DoesNotExist:
            messages.error(request, 'User not found. Please register again.')  
            return redirect('accounts:register')
    
    return render(request, 'accounts/verify_email.html', {'email': email})


@login_required
def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out')
    return redirect('store:index')


@login_required
def profile(request):
    """User profile and order history"""
    # Only show orders that haven't been 'cleared' by the customer
    orders = Order.objects.filter(user=request.user, visible_to_customer=True).order_by('-created_at')
    context = {
        'orders': orders,
        'user': request.user
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def clear_history(request):
    """Soft delete all order history for the user"""
    if request.method == 'POST':
        # Hide all orders for this user from their view
        Order.objects.filter(user=request.user).update(visible_to_customer=False)
        messages.success(request, 'Order history cleared successfully.')
    return redirect('accounts:profile')


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
        
    return redirect('accounts:profile')
