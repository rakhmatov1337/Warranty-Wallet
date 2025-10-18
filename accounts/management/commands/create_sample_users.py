from django.core.management.base import BaseCommand
from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Creates sample customers and retailers for testing'

    def handle(self, *args, **options):
        # Common password for all users
        password = 'Test1234!'
        
        # Sample customers
        customers_data = [
            {
                'email': 'alisher.toshkent@gmail.com',
                'full_name': 'Alisher Karimov',
                'phone_number': '+998 90 123 45 67',
                'role': 'customer'
            },
            {
                'email': 'dilnoza.samarkand@gmail.com',
                'full_name': 'Dilnoza Rahimova',
                'phone_number': '+998 91 234 56 78',
                'role': 'customer'
            },
            {
                'email': 'javohir.bukhara@gmail.com',
                'full_name': 'Javohir Usmanov',
                'phone_number': '+998 93 345 67 89',
                'role': 'customer'
            },
            {
                'email': 'madina.fergana@gmail.com',
                'full_name': 'Madina Ergasheva',
                'phone_number': '+998 94 456 78 90',
                'role': 'customer'
            },
            {
                'email': 'rustam.namangan@gmail.com',
                'full_name': 'Rustam Abdullayev',
                'phone_number': '+998 95 567 89 01',
                'role': 'customer'
            },
            {
                'email': 'shohruh.andijan@gmail.com',
                'full_name': 'Shohruh Ismoilov',
                'phone_number': '+998 97 678 90 12',
                'role': 'customer'
            },
            {
                'email': 'gulnora.qashqadaryo@gmail.com',
                'full_name': 'Gulnora Hamidova',
                'phone_number': '+998 88 789 01 23',
                'role': 'customer'
            },
            {
                'email': 'aziz.surxondaryo@gmail.com',
                'full_name': 'Aziz Saidov',
                'phone_number': '+998 90 890 12 34',
                'role': 'customer'
            },
        ]
        
        # Sample retailers
        retailers_data = [
            {
                'email': 'techno.store@gmail.com',
                'full_name': 'Techno Store',
                'phone_number': '+998 71 200 00 01',
                'role': 'retailer'
            },
            {
                'email': 'electromart.uz@gmail.com',
                'full_name': 'ElectroMart Uzbekistan',
                'phone_number': '+998 71 200 00 02',
                'role': 'retailer'
            },
            {
                'email': 'mega.planet@gmail.com',
                'full_name': 'Mega Planet',
                'phone_number': '+998 71 200 00 03',
                'role': 'retailer'
            },
            {
                'email': 'express24.shop@gmail.com',
                'full_name': 'Express 24 Shop',
                'phone_number': '+998 71 200 00 04',
                'role': 'retailer'
            },
            {
                'email': 'smartech.uz@gmail.com',
                'full_name': 'Smartech Uzbekistan',
                'phone_number': '+998 71 200 00 05',
                'role': 'retailer'
            },
        ]
        
        # Create customers
        self.stdout.write(self.style.WARNING('Creating customers...'))
        for customer_data in customers_data:
            try:
                if CustomUser.objects.filter(email=customer_data['email']).exists():
                    self.stdout.write(
                        self.style.WARNING(f'Customer {customer_data["email"]} already exists. Skipping...')
                    )
                else:
                    user = CustomUser.objects.create_user(
                        email=customer_data['email'],
                        full_name=customer_data['full_name'],
                        phone_number=customer_data['phone_number'],
                        password=password,
                        role=customer_data['role']
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Created customer: {user.full_name} ({user.email})')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error creating customer {customer_data["email"]}: {str(e)}')
                )
        
        # Create retailers
        self.stdout.write(self.style.WARNING('\nCreating retailers...'))
        for retailer_data in retailers_data:
            try:
                if CustomUser.objects.filter(email=retailer_data['email']).exists():
                    self.stdout.write(
                        self.style.WARNING(f'Retailer {retailer_data["email"]} already exists. Skipping...')
                    )
                else:
                    user = CustomUser.objects.create_user(
                        email=retailer_data['email'],
                        full_name=retailer_data['full_name'],
                        phone_number=retailer_data['phone_number'],
                        password=password,
                        role=retailer_data['role']
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Created retailer: {user.full_name} ({user.email})')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error creating retailer {retailer_data["email"]}: {str(e)}')
                )
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Sample users created successfully!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.WARNING(f'\n📧 All users password: {password}'))
        self.stdout.write(self.style.WARNING(f'📊 Total customers: {len(customers_data)}'))
        self.stdout.write(self.style.WARNING(f'🏪 Total retailers: {len(retailers_data)}'))
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))

