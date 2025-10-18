# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0003_update_claim_model'),
    ]

    operations = [
        # Remove assigned_to field
        migrations.RemoveField(
            model_name='claim',
            name='assigned_to',
        ),
        # Update status field choices and default
        migrations.AlterField(
            model_name='claim',
            name='status',
            field=models.CharField(
                choices=[
                    ('In Review', 'In Review'),
                    ('Approved', 'Approved'),
                    ('Rejected', 'Rejected')
                ],
                default='In Review',
                max_length=20
            ),
        ),
    ]

