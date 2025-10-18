# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # Make username nullable and optional
        migrations.AlterField(
            model_name='customuser',
            name='username',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        # Add full_name field
        migrations.AddField(
            model_name='customuser',
            name='full_name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        # Add phone_number field
        migrations.AddField(
            model_name='customuser',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]

