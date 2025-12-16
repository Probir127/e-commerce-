from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from store.models import Product, Category, Brand
import os
from django.utils.text import slugify
from decimal import Decimal

class Command(BaseCommand):
    help = 'Imports products from static images that are not yet in the database'

    def handle(self, *args, **kwargs):
        # Source directory (static images)
        static_img_dir = settings.BASE_DIR / 'store' / 'static' / 'store' / 'image'
        
        # Ensure category exists
        category_name = 'Smartphones'
        category, created = Category.objects.get_or_create(
            name=category_name,
            defaults={'description': 'Automatically imported smartphones'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created category: {category_name}'))

        # Extensions to look for
        valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        
        # Counters
        created_count = 0
        skipped_count = 0
        error_count = 0

        if not static_img_dir.exists():
            self.stdout.write(self.style.ERROR(f'Static image directory not found: {static_img_dir}'))
            return

        self.stdout.write(f'Scanning directory: {static_img_dir}')
        
        for filename in os.listdir(static_img_dir):
            file_path = static_img_dir / filename
            
            # Skip directories or invalid files
            if not file_path.is_file():
                continue
                
            ext = os.path.splitext(filename)[1].lower()
            if ext not in valid_extensions:
                continue
                
            # Skip system files or logic-less files like admin_login_bg
            if 'admin' in filename.lower() or 'placeholder' in filename.lower() or 'images' in filename.lower():
                skipped_count += 1
                continue

            # Convert filename to product name
            # Remove extension
            name_raw = os.path.splitext(filename)[0]
            # Replace dashes/underscores with spaces
            name_clean = name_raw.replace('-', ' ').replace('_', ' ')
            # Title case
            product_name = name_clean.title()
            
            # Infer brand (first word)
            brand_name = product_name.split()[0] if product_name else 'Unknown'
            brand, _ = Brand.objects.get_or_create(name=brand_name)
            
            # Check if product exists
            if Product.objects.filter(name__iexact=product_name).exists():
                skipped_count += 1
                # self.stdout.write(f'Skipped existing: {product_name}')
                continue
                
            try:
                # Create product
                product = Product(
                    name=product_name,
                    category=category,
                    brand=brand,
                    price=Decimal('50000.00'), # Default price
                    description=f"High quality {product_name} available now.",
                    stock=50,
                    available=True,
                    featured=False
                )
                
                # Assign image
                # We open the local file and save t to the ImageField
                # This automatically handles copying to MEDIA_ROOT
                with open(file_path, 'rb') as f:
                    product.image.save(filename, ContentFile(f.read()), save=False)
                    
                product.save()
                self.stdout.write(self.style.SUCCESS(f'Imported: {product_name}'))
                created_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to import {filename}: {e}'))
                error_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nImport complete!'))
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        self.stdout.write(f'Errors: {error_count}')
