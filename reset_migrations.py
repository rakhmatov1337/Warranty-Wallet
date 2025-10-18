"""
Script to completely reset migration history to match current migration files
WARNING: This will delete all migration history and re-record it
Run with: python reset_migrations.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def reset_migration_history():
    """
    Delete all migration records and let Django recreate them
    """
    with connection.cursor() as cursor:
        print("Current migration records:")
        cursor.execute(
            "SELECT app, name FROM django_migrations ORDER BY app, id"
        )
        migrations = cursor.fetchall()
        for app, name in migrations:
            print(f"  {app}.{name}")
        
        print("\n" + "="*60)
        response = input("Do you want to DELETE ALL migration history? (yes/no): ")
        
        if response.lower() != 'yes':
            print("Operation cancelled.")
            return
        
        print("\nDeleting all migration records...")
        cursor.execute("DELETE FROM django_migrations")
        print("[OK] All migration records deleted!")
        
        print("\nNow run these commands:")
        print("1. python manage.py migrate --fake")
        print("   This will recreate the migration history based on current database schema")

if __name__ == '__main__':
    try:
        reset_migration_history()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

