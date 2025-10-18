# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('warranties', '0001_initial'),
        ('receipts', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE warranties_warranty DROP COLUMN IF EXISTS user_id;",
            reverse_sql="ALTER TABLE warranties_warranty ADD COLUMN user_id INTEGER REFERENCES accounts_customuser(id) ON DELETE CASCADE;"
        ),
    ]

