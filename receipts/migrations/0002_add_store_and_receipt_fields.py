# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
        ('receipts', '0001_initial'),
    ]

    operations = [
        # Create ReceiptItem model
        migrations.CreateModel(
            name='ReceiptItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=255)),
                ('model', models.CharField(blank=True, max_length=100)),
                ('serial_number', models.CharField(blank=True, max_length=100)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('quantity', models.IntegerField(default=1)),
                ('warranty_coverage', models.CharField(blank=True, help_text='e.g., 12 months manufacturer', max_length=255)),
                ('warranty_expiry', models.DateField(blank=True, null=True)),
            ],
        ),
        # Add new fields to Receipt
        migrations.AddField(
            model_name='receipt',
            name='store',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='store.store'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='receipt',
            name='receipt_number',
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
        migrations.AddField(
            model_name='receipt',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='receipt',
            name='tax',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='receipt',
            name='time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='receipt',
            name='payment_method',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='receipt',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='receipt',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # Remove old items TextField
        migrations.RemoveField(
            model_name='receipt',
            name='items',
        ),
        # Add ForeignKey to ReceiptItem
        migrations.AddField(
            model_name='receiptitem',
            name='receipt',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='receipts.receipt'),
        ),
    ]

