"""
Complete migration fix - clears history and re-fakes everything
This is safe for development as it doesn't touch your actual database tables
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

def fix_migrations():
    """Clear migration history and prepare for --fake"""
    with connection.cursor() as cursor:
        print("Clearing migration history...")
        cursor.execute("DELETE FROM django_migrations")
        print("[OK] Migration history cleared!")
        
    print("\n" + "="*60)
    print("Migration history has been reset.")
    print("="*60)
    print("\nNext steps:")
    print("1. Run: python manage.py migrate --fake")
    print("   This will record all migrations as applied without changing the database")
    print("\n2. If you get errors, run: python manage.py migrate --fake-initial")
    print("\nThis is safe because:")
    print("- Your database tables are not modified")
    print("- Only the migration tracking table is updated")

if __name__ == '__main__':
    fix_migrations()

