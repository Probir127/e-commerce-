import os
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Product, Order, AccountingEntry

@receiver(post_delete, sender=Product)
def delete_product_image(sender, instance, **kwargs):
    if instance.image:
        if os.path.isfile(instance.image.path):
            try:
                os.remove(instance.image.path)
            except Exception as e:
                print(f"Error deleting file: {e}")

@receiver(post_save, sender=Order)
def sync_order_to_ledger(sender, instance, created, **kwargs):
    """
    Auto-sync Order state to Accounting Ledger.
    1. Paid -> Income
    2. Cancelled/Refunded -> Expense (Refund)
    """
    # 1. Handle Income (Paid)
    if instance.payment_status == 'paid':
        # Check if entry already exists to prevent duplicate income
        entry, created_entry = AccountingEntry.objects.get_or_create(
            related_order=instance,
            entry_type='income',
            defaults={
                'amount': instance.total,
                'description': f"Order #{instance.id} Revenue",
                'date': instance.created_at
            }
        )
        # If amount changed (unlikely for paid, but possible in admin), update it
        if not created_entry and entry.amount != instance.total:
            entry.amount = instance.total
            entry.save()
            
    # 2. Handle Refund/Cancellation
    if instance.status == 'cancelled' or instance.payment_status == 'refunded':
        # If order was previously paid, we need to negate it or add a refund entry.
        # Strategy: Add a generic "Refund" expense entry linked to this order.
        
        # First check if we ever recorded income
        income_entry = AccountingEntry.objects.filter(related_order=instance, entry_type='income').first()
        
        if income_entry:
            # Create a refund/cancellation entry if not exists
            refund_entry, refund_created = AccountingEntry.objects.get_or_create(
                related_order=instance,
                entry_type='expense',
                defaults={
                    'amount': instance.total,
                    'description': f"Refund/Cancel Order #{instance.id}",
                    'date': instance.updated_at
                }
            )
