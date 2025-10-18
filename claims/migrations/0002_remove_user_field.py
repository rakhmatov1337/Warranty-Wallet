# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0001_initial'),
        ('warranties', '0002_remove_user_field'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE claims_claim DROP COLUMN IF EXISTS user_id;",
            reverse_sql="ALTER TABLE claims_claim ADD COLUMN user_id INTEGER REFERENCES accounts_customuser(id) ON DELETE CASCADE;"
        ),
    ]

