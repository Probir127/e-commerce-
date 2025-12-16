import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from store.models import Product

try:
    p = Product.objects.get(name='Mi Power Bank') # Verify exact name from previous logs
    p.purchase_price = 20.00
    p.save()
    print(f"SUCCESS: Updated {p.name}: Price={p.price}, Cost={p.purchase_price}")
except Product.DoesNotExist:
    # Fallback to finding by ID if name mismatch
    p = Product.objects.filter(name__icontains='Power Bank').first()
    if p:
        p.purchase_price = 20.00
        p.save()
        print(f"SUCCESS: Updated {p.name}: Price={p.price}, Cost={p.purchase_price}")
    else:
        print("ERROR: Product not found")
