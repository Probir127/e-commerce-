from django.core.management.base import BaseCommand
from store.models import Category, Product
from decimal import Decimal
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Seeds the database with initial categories and products'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')
        
        # Create categories
        categories_data = [
            {'name': 'Smartphones', 'description': 'Latest smartphones and mobile devices'},
            {'name': 'Electronics', 'description': 'Electronic gadgets and accessories'},
            {'name': 'Audio', 'description': 'Headphones, earbuds, and audio equipment'},
            {'name': 'Home Appliances', 'description': 'Home and kitchen appliances'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
        
        # Create products
        products_data = [
            {
                'name': 'Redmi Note 14 Pro+',
                'category': 'Smartphones',
                'description': 'Premium smartphone with 512GB storage and advanced camera system',
                'price': Decimal('399.00'),
                'stock': 25,
                'featured': True,
                'image_name': 'Xiaomi-Redmi-Note-14-Pro-Plus-512GB-Silver.webp'
            },
            {
                'name': 'Vivo V29e 5G',
                'category': 'Smartphones',
                'description': '5G enabled smartphone with stunning display',
                'price': Decimal('449.00'),
                'stock': 30,
                'featured': True,
                'image_name': 'Vivo-V29e-5G.jpg'
            },
            {
                'name': 'Realme 11 Pro+',
                'category': 'Smartphones',
                'description': 'High-performance smartphone with Oasis Green finish',
                'price': Decimal('379.00'),
                'stock': 20,
                'featured': True,
                'image_name': 'Realme-11-Pro-Plus-5G-Oasis-Green-3265.jpg'
            },
            {
                'name': 'Redmi Note 13 Pro',
                'category': 'Smartphones',
                'description': '5G smartphone with excellent camera and battery life',
                'price': Decimal('329.00'),
                'stock': 35,
                'featured': True,
                'image_name': 'Redmi-Note-13-Pro-5G.jpg'
            },
            {
                'name': 'Samsung S24+ 5G',
                'category': 'Smartphones',
                'description': 'Flagship Samsung smartphone with advanced AI features',
                'price': Decimal('1199.00'),
                'stock': 15,
                'featured': True,
                'image_name': 'samsung-s24-plus-price-in-bangladesh.webp'
            },
            {
                'name': 'OnePlus 12 5G',
                'category': 'Smartphones',
                'description': 'Never Settle - Premium performance smartphone',
                'price': Decimal('899.00'),
                'stock': 18,
                'featured': True,
                'image_name': 'OnePlus-12-5G.jpg'
            },
            {
                'name': 'Google Pixel 6 5G',
                'category': 'Smartphones',
                'description': 'The smartest Google phone with advanced AI',
                'price': Decimal('599.00'),
                'stock': 22,
                'featured': True,
                'image_name': 'google-pixel-6-5g-smartphone-500x500.webp'
            },
            {
                'name': 'Mi Power Bank',
                'category': 'Electronics',
                'description': '10000mAh fast charging power bank',
                'price': Decimal('45.00'),
                'stock': 50,
                'featured': False,
                'image_name': 'xiaomi.jpeg'
            },
            {
                'name': 'OnePlus Charger',
                'category': 'Electronics',
                'description': 'Warp Charge 65W fast charger',
                'price': Decimal('60.00'),
                'stock': 40,
                'featured': False,
                'image_name': 'one plus.png'
            },
        ]
        
        for prod_data in products_data:
            category = categories[prod_data['category']]
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'category': category,
                    'description': prod_data['description'],
                    'price': prod_data['price'],
                    'stock': prod_data['stock'],
                    'featured': prod_data['featured'],
                    'available': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))
        
        self.stdout.write(self.style.SUCCESS('Database seeding completed!'))
