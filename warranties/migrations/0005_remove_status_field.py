# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('warranties', '0004_switch_to_receipt_item'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='warranty',
            name='status',
        ),
    ]

