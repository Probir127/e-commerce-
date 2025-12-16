from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/clear-history/', views.clear_history, name='clear_history'),
    path('order/invoice/<int:order_id>/', views.customer_order_invoice, name='customer_order_invoice'),
    path('order/cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
]
