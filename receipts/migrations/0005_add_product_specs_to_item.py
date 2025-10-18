# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0004_remove_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='receiptitem',
            name='color',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='receiptitem',
            name='imei',
            field=models.CharField(blank=True, help_text='IMEI or unique identifier', max_length=100),
        ),
        migrations.AddField(
            model_name='receiptitem',
            name='storage',
            field=models.CharField(blank=True, help_text='e.g., 256GB', max_length=50),
        ),
    ]

