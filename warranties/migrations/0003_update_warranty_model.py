# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('warranties', '0002_remove_user_field'),
        ('receipts', '0005_add_product_specs_to_item'),
    ]

    operations = [
        migrations.AddField(
            model_name='warranty',
            name='coverage_period_months',
            field=models.IntegerField(default=12, help_text='Coverage period in months'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='warranty',
            name='coverage_terms',
            field=models.TextField(default='Standard warranty coverage', help_text='e.g., Full hardware coverage, liquid damage, theft protection'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='warranty',
            name='provider',
            field=models.CharField(default='Unknown', help_text='e.g., Apple Inc. + TechMart Extended', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='warranty',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]

