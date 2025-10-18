# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0003_add_store_and_receipt_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='receipt',
            name='tax',
        ),
        migrations.RemoveField(
            model_name='receipt',
            name='subtotal',
        ),
    ]

