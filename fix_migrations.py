"""
Script to fix inconsistent migration history
Run with: python fix_migrations.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def fix_migration_history():
    """
    Fix the inconsistent migration history by marking missing receipts migrations as applied
    """
    migrations_to_add = [
        ('receipts', '0005_add_product_specs_to_item'),
        ('receipts', '0006_alter_receipt_options'),
    ]
    
    with connection.cursor() as cursor:
        for app, migration_name in migrations_to_add:
            # Check if migration is already recorded
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app = %s AND name = %s",
                [app, migration_name]
            )
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"Adding {app}.{migration_name} to migration history...")
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
                    [app, migration_name]
                )
                print(f"[OK] {app}.{migration_name} added!")
            else:
                print(f"[SKIP] {app}.{migration_name} already exists")
        
        # Show current migration status
        print("\nCurrent migration status:")
        cursor.execute(
            """
            SELECT app, name, applied 
            FROM django_migrations 
            WHERE app IN ('receipts', 'warranties')
            ORDER BY app, applied
            """
        )
        for row in cursor.fetchall():
            print(f"  {row[0]}.{row[1]} - Applied: {row[2]}")

if __name__ == '__main__':
    try:
        fix_migration_history()
        print("\n[DONE] Now try running: python manage.py migrate")
    except Exception as e:
        print(f"[ERROR] {e}")
        print("\nIf this fails, you may need to manually fix the database.")
        print("Alternative: Drop and recreate the database (development only)")

