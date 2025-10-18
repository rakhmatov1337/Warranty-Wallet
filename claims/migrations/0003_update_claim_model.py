# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0002_remove_user_field'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('warranties', '0004_switch_to_receipt_item'),
    ]

    operations = [
        # Add new fields with defaults
        migrations.AddField(
            model_name='claim',
            name='claim_number',
            field=models.CharField(blank=True, max_length=50, unique=True),
        ),
        migrations.AddField(
            model_name='claim',
            name='issue_summary',
            field=models.CharField(default='Issue reported', help_text='Brief summary of the issue', max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='claim',
            name='detailed_description',
            field=models.TextField(default='Details not provided', help_text='Detailed description of the issue'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='claim',
            name='category',
            field=models.CharField(choices=[('Accidental Damage', 'Accidental Damage'), ('Manufacturing Defect', 'Manufacturing Defect'), ('Normal Wear', 'Normal Wear'), ('Malfunction', 'Malfunction'), ('Other', 'Other')], default='Other', max_length=50),
        ),
        migrations.AddField(
            model_name='claim',
            name='assigned_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_claims', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='claim',
            name='actual_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='claim',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_claims', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='claim',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # Update existing fields
        migrations.AlterField(
            model_name='claim',
            name='status',
            field=models.CharField(choices=[('Submitted', 'Submitted'), ('Assigned', 'Assigned'), ('In Review', 'In Review'), ('Approved', 'Approved'), ('Rejected', 'Rejected'), ('Completed', 'Completed')], default='Submitted', max_length=20),
        ),
        migrations.AlterField(
            model_name='claim',
            name='submitted_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        # Remove old issue field
        migrations.RemoveField(
            model_name='claim',
            name='issue',
        ),
        # Create new models
        migrations.CreateModel(
            name='ClaimTimeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('claim', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeline', to='claims.claim')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='ClaimNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('claim', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='claims.claim')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AlterModelOptions(
            name='claim',
            options={'ordering': ['-submitted_at']},
        ),
    ]

