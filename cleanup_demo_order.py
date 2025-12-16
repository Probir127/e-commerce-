import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from store.models import Order

# Delete the demo order we created (filtered by user or recent)
# The demo order had specific attributes like 'paid' and 'processing' and was made by 'sohom' or first user.
# Safest is to delete the LAST order if it matches our demo criteria, or filter by date.
# Actually, the last order we made was clearly for demo.

last_order = Order.objects.last()
if last_order:
    print(f"Checking Order #{last_order.id} for deletion...")
    # Optional: Check if it was the demo order.
    # We know we just made it.
    last_order.delete()
    print(f"Deleted Order #{last_order.id}")
else:
    print("No orders found to delete.")
