# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Admin'), ('retailer', 'Retailer'), ('customer', 'Customer')],
                default='customer',
                max_length=20
            ),
        ),
    ]

