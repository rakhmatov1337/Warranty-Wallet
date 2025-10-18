# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0004_remove_tax_and_subtotal'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='receipt',
            name='status',
        ),
    ]

