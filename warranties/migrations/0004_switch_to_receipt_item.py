# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warranties', '0003_update_warranty_model'),
        ('receipts', '0006_add_product_specs_to_item'),
    ]

    operations = [
        # Remove old fields that are no longer in the model
        migrations.RemoveField(
            model_name='warranty',
            name='receipt',
        ),
        migrations.RemoveField(
            model_name='warranty',
            name='product_name',
        ),
        migrations.RemoveField(
            model_name='warranty',
            name='serial_number',
        ),
        # Add the new receipt_item field
        migrations.AddField(
            model_name='warranty',
            name='receipt_item',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='warranty',
                to='receipts.receiptitem',
                null=True,  # Temporarily allow null
                blank=True
            ),
        ),
    ]

