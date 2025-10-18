# Generated manually

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('receipts', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL
            sql="""
                ALTER TABLE receipts_receipt DROP COLUMN IF EXISTS customer;
                ALTER TABLE receipts_receipt DROP COLUMN IF EXISTS user_id;
                ALTER TABLE receipts_receipt ADD COLUMN retailer_id INTEGER NOT NULL DEFAULT 1 REFERENCES accounts_customuser(id) ON DELETE CASCADE;
                ALTER TABLE receipts_receipt ADD COLUMN customer_id INTEGER NOT NULL DEFAULT 1 REFERENCES accounts_customuser(id) ON DELETE CASCADE;
                ALTER TABLE receipts_receipt ALTER COLUMN retailer_id DROP DEFAULT;
                ALTER TABLE receipts_receipt ALTER COLUMN customer_id DROP DEFAULT;
            """,
            # Reverse SQL (for rollback)
            reverse_sql="""
                ALTER TABLE receipts_receipt DROP COLUMN IF EXISTS retailer_id;
                ALTER TABLE receipts_receipt DROP COLUMN IF EXISTS customer_id;
                ALTER TABLE receipts_receipt ADD COLUMN customer VARCHAR(254);
                ALTER TABLE receipts_receipt ADD COLUMN user_id INTEGER REFERENCES accounts_customuser(id) ON DELETE CASCADE;
            """
        ),
    ]

