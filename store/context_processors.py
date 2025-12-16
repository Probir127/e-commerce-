from .models import Category, Brand

def global_store_data(request):
    """
    Makes categories and brands available to all templates
    """
    return {
        'nav_categories': Category.objects.all()[:8], # Limit to 8 for nav
        'nav_brands': Brand.objects.all()[:10], # Limit to 10 for nav
    }
