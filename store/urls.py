from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('product/', views.product, name='product'),
    path('category/', views.category, name='category'),
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('order-invoice/<int:order_id>/', views.admin_order_invoice, name='admin_order_invoice'),
    path('track-order/<int:order_id>/', views.track_order, name='track_order'),
]