from django.core.management.base import BaseCommand
from store.models import Product
from django.core.files import File
from pathlib import Path
import shutil

class Command(BaseCommand):
    help = 'Links existing static images to products'

    def handle(self, *args, **kwargs):
        self.stdout.write('Linking images to products...')
        
        # Map product names to their image files
        image_mapping = {
            'Redmi Note 14 Pro+': 'Xiaomi-Redmi-Note-14-Pro-Plus-512GB-Silver.webp',
            'Vivo V29e 5G': 'Vivo-V29e-5G.jpg',
            'Realme 11 Pro+': 'Realme-11-Pro-Plus-5G-Oasis-Green-3265.jpg',
            'Redmi Note 13 Pro': 'Redmi-Note-13-Pro-5G.jpg',
            'Samsung S24+ 5G': 'samsung-s24-plus-price-in-bangladesh.webp',
            'OnePlus 12 5G': 'OnePlus-12-5G.jpg',
            'Google Pixel 6 5G': 'google-pixel-6-5g-smartphone-500x500.webp',
            'Mi Power Bank': 'xiaomi.jpeg',
            'OnePlus Charger': 'one plus.png',
        }
        
        static_image_dir = Path('store/static/store/image')
        media_products_dir = Path('media/products')
        media_products_dir.mkdir(parents=True, exist_ok=True)
        
        for product_name, image_file in image_mapping.items():
            try:
                product = Product.objects.get(name=product_name)
                source_path = static_image_dir / image_file
                
                if source_path.exists():
                    # Copy to media directory
                    dest_path = media_products_dir / image_file
                    shutil.copy2(source_path, dest_path)
                    
                    # Update product image field
                    product.image = f'products/{image_file}'
                    product.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Linked {image_file} to {product_name}'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'✗ Image not found: {source_path}'
                    ))
            except Product.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'✗ Product not found: {product_name}'
                ))
        
        self.stdout.write(self.style.SUCCESS('\nImage linking completed!'))
