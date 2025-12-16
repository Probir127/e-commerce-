import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from store.models import Order

order = Order.objects.last()
print(f"Order #{order.id} - Status: {order.status}, Payment: {order.payment_status}")
print(f"Total: {order.total}")

for item in order.items.all():
    print(f"Item: {item.product.name}")
    print(f"  Qty: {item.quantity}")
    print(f"  Price: {item.price}")
    print(f"  Purchase Price: {item.purchase_price}")
    print(f"  Profit: {item.profit}")
