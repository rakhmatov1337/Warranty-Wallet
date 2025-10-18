from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import random

from accounts.models import CustomUser
from store.models import Store
from receipts.models import Receipt, ReceiptItem
from warranties.models import Warranty
from claims.models import Claim, ClaimNote
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Populate database with beautiful mock data for all models'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 Starting to populate mock data...\n'))
        
        # Common password
        password = 'Test1234!'
        
        # Clear existing data (optional - commented out for safety)
        # self.stdout.write(self.style.WARNING('⚠️  Clearing existing data...'))
        # Claim.objects.all().delete()
        # Warranty.objects.all().delete()
        # ReceiptItem.objects.all().delete()
        # Receipt.objects.all().delete()
        # Store.objects.all().delete()
        # CustomUser.objects.filter(role__in=['customer', 'retailer']).delete()
        
        # Create users
        customers = self.create_customers(password)
        retailers = self.create_retailers(password)
        
        # Create stores
        stores = self.create_stores(retailers)
        
        # Create receipts with items
        receipts = self.create_receipts(stores, retailers, customers)
        
        # Create warranties
        warranties = self.create_warranties()
        
        # Create claims
        claims = self.create_claims(customers, warranties)
        
        # Create notifications
        self.create_notifications(customers, retailers)
        
        # Final summary
        self.print_summary(customers, retailers, stores, receipts, warranties, claims)

    def create_customers(self, password):
        """Create customer accounts"""
        self.stdout.write(self.style.WARNING('\n👥 Creating Customers...'))
        
        customers_data = [
            {
                'email': 'alisher.toshkent@gmail.com',
                'full_name': 'Alisher Karimov',
                'phone_number': '+998 90 123 45 67',
            },
            {
                'email': 'dilnoza.samarkand@gmail.com',
                'full_name': 'Dilnoza Rahimova',
                'phone_number': '+998 91 234 56 78',
            },
            {
                'email': 'javohir.bukhara@gmail.com',
                'full_name': 'Javohir Usmanov',
                'phone_number': '+998 93 345 67 89',
            },
            {
                'email': 'madina.fergana@gmail.com',
                'full_name': 'Madina Ergasheva',
                'phone_number': '+998 94 456 78 90',
            },
            {
                'email': 'rustam.namangan@gmail.com',
                'full_name': 'Rustam Abdullayev',
                'phone_number': '+998 95 567 89 01',
            },
            {
                'email': 'shohruh.andijan@gmail.com',
                'full_name': 'Shohruh Ismoilov',
                'phone_number': '+998 97 678 90 12',
            },
            {
                'email': 'gulnora.qashqadaryo@gmail.com',
                'full_name': 'Gulnora Hamidova',
                'phone_number': '+998 88 789 01 23',
            },
            {
                'email': 'aziz.surxondaryo@gmail.com',
                'full_name': 'Aziz Saidov',
                'phone_number': '+998 90 890 12 34',
            },
            {
                'email': 'shahzoda.andijon@gmail.com',
                'full_name': 'Shahzoda Tursunova',
                'phone_number': '+998 91 901 23 45',
            },
            {
                'email': 'bobur.xorazm@gmail.com',
                'full_name': 'Bobur Yusupov',
                'phone_number': '+998 93 012 34 56',
            },
        ]
        
        customers = []
        for data in customers_data:
            try:
                customer, created = CustomUser.objects.get_or_create(
                    email=data['email'],
                    defaults={
                        'full_name': data['full_name'],
                        'phone_number': data['phone_number'],
                        'role': 'customer'
                    }
                )
                if created:
                    customer.set_password(password)
                    customer.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {customer.full_name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {customer.full_name} (already exists)'))
                customers.append(customer)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
        
        return customers

    def create_retailers(self, password):
        """Create retailer accounts"""
        self.stdout.write(self.style.WARNING('\n🏪 Creating Retailers...'))
        
        retailers_data = [
            {
                'email': 'techno.store@gmail.com',
                'full_name': 'Techno Store Manager',
                'phone_number': '+998 71 200 00 01',
            },
            {
                'email': 'electromart.uz@gmail.com',
                'full_name': 'ElectroMart Manager',
                'phone_number': '+998 71 200 00 02',
            },
            {
                'email': 'mega.planet@gmail.com',
                'full_name': 'Mega Planet Manager',
                'phone_number': '+998 71 200 00 03',
            },
            {
                'email': 'express24.shop@gmail.com',
                'full_name': 'Express 24 Manager',
                'phone_number': '+998 71 200 00 04',
            },
            {
                'email': 'smartech.uz@gmail.com',
                'full_name': 'Smartech Manager',
                'phone_number': '+998 71 200 00 05',
            },
        ]
        
        retailers = []
        for data in retailers_data:
            try:
                retailer, created = CustomUser.objects.get_or_create(
                    email=data['email'],
                    defaults={
                        'full_name': data['full_name'],
                        'phone_number': data['phone_number'],
                        'role': 'retailer'
                    }
                )
                if created:
                    retailer.set_password(password)
                    retailer.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {retailer.full_name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {retailer.full_name} (already exists)'))
                retailers.append(retailer)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
        
        return retailers

    def create_stores(self, retailers):
        """Create store locations"""
        self.stdout.write(self.style.WARNING('\n🏢 Creating Stores...'))
        
        stores_data = [
            {
                'name': 'Techno Store - Magic City',
                'phone_number': '+998 71 200 10 01',
                'email': 'magicity@technostore.uz',
                'address': 'Magic City Mall, Taras Shevchenko, Tashkent, Uzbekistan',
                'admin': retailers[0] if retailers else None,
            },
            {
                'name': 'ElectroMart - Next Mall',
                'phone_number': '+998 71 200 10 02',
                'email': 'next@electromart.uz',
                'address': 'Next Mall, Amir Temur Avenue, Tashkent, Uzbekistan',
                'admin': retailers[1] if len(retailers) > 1 else retailers[0],
            },
            {
                'name': 'Mega Planet - Samarkand',
                'phone_number': '+998 66 200 10 03',
                'email': 'samarkand@megaplanet.uz',
                'address': 'Samarkand City Center, Registon Street, Samarkand, Uzbekistan',
                'admin': retailers[2] if len(retailers) > 2 else retailers[0],
            },
            {
                'name': 'Express 24 - Chilanzar',
                'phone_number': '+998 71 200 10 04',
                'email': 'chilanzar@express24.uz',
                'address': 'Chilanzar District, Block 10, Tashkent, Uzbekistan',
                'admin': retailers[3] if len(retailers) > 3 else retailers[0],
            },
            {
                'name': 'Smartech - Compass Mall',
                'phone_number': '+998 71 200 10 05',
                'email': 'compass@smartech.uz',
                'address': 'Compass Shopping Mall, Mustaqillik Avenue, Tashkent, Uzbekistan',
                'admin': retailers[4] if len(retailers) > 4 else retailers[0],
            },
            {
                'name': 'Techno Store - Andijon',
                'phone_number': '+998 74 200 10 06',
                'email': 'andijon@technostore.uz',
                'address': 'Bobur Street, City Center, Andijan, Uzbekistan',
                'admin': retailers[0] if retailers else None,
            },
        ]
        
        stores = []
        for data in stores_data:
            try:
                store, created = Store.objects.get_or_create(
                    name=data['name'],
                    defaults={
                        'phone_number': data['phone_number'],
                        'email': data['email'],
                        'address': data['address'],
                    }
                )
                if data['admin']:
                    store.admins.add(data['admin'])
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {store.name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {store.name} (already exists)'))
                stores.append(store)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
        
        return stores

    def create_receipts(self, stores, retailers, customers):
        """Create receipts with items"""
        self.stdout.write(self.style.WARNING('\n🧾 Creating Receipts with Items...'))
        
        # Product catalog
        products = [
            {'name': 'iPhone 15 Pro Max', 'price': 12500000, 'warranty_months': 12, 'specs': {'color': 'Natural Titanium', 'storage': '256GB'}},
            {'name': 'Samsung Galaxy S24 Ultra', 'price': 11000000, 'warranty_months': 12, 'specs': {'color': 'Titanium Black', 'storage': '512GB'}},
            {'name': 'MacBook Pro 14"', 'price': 22000000, 'warranty_months': 24, 'specs': {'color': 'Space Gray', 'storage': '1TB SSD'}},
            {'name': 'iPad Air M2', 'price': 7500000, 'warranty_months': 12, 'specs': {'color': 'Starlight', 'storage': '256GB'}},
            {'name': 'AirPods Pro 2nd Gen', 'price': 2500000, 'warranty_months': 12, 'specs': {'color': 'White', 'storage': 'N/A'}},
            {'name': 'Samsung Galaxy Watch 6', 'price': 3200000, 'warranty_months': 12, 'specs': {'color': 'Graphite', 'storage': '16GB'}},
            {'name': 'Sony WH-1000XM5', 'price': 3800000, 'warranty_months': 24, 'specs': {'color': 'Silver', 'storage': 'N/A'}},
            {'name': 'Dell XPS 13', 'price': 15000000, 'warranty_months': 12, 'specs': {'color': 'Platinum', 'storage': '512GB'}},
            {'name': 'Nintendo Switch OLED', 'price': 3500000, 'warranty_months': 12, 'specs': {'color': 'White', 'storage': '64GB'}},
            {'name': 'LG 65" OLED TV', 'price': 18000000, 'warranty_months': 24, 'specs': {'color': 'Black', 'storage': 'N/A'}},
            {'name': 'Dyson V15 Vacuum', 'price': 5500000, 'warranty_months': 24, 'specs': {'color': 'Yellow/Nickel', 'storage': 'N/A'}},
            {'name': 'Canon EOS R6', 'price': 25000000, 'warranty_months': 12, 'specs': {'color': 'Black', 'storage': 'SD Card'}},
        ]
        
        payment_methods = ['Card', 'Cash', 'Payme', 'Click', 'Uzum Nasiya']
        
        receipts = []
        receipt_count = 0
        
        # Create 20-30 receipts distributed across time
        for i in range(25):
            try:
                # Random date within last 18 months
                days_ago = random.randint(0, 540)
                receipt_date = date.today() - timedelta(days=days_ago)
                receipt_time = datetime.now().time().replace(
                    hour=random.randint(9, 20),
                    minute=random.randint(0, 59)
                )
                
                store = random.choice(stores)
                retailer = random.choice(list(store.admins.all()))
                customer = random.choice(customers)
                
                # Random 1-3 items per receipt
                num_items = random.randint(1, 3)
                selected_products = random.sample(products, num_items)
                
                total = sum(Decimal(p['price']) / 100 for p in selected_products)
                
                receipt = Receipt.objects.create(
                    store=store,
                    retailer=retailer,
                    customer=customer,
                    total=total,
                    date=receipt_date,
                    time=receipt_time,
                    payment_method=random.choice(payment_methods),
                    notes=f'Purchase at {store.name}'
                )
                
                # Create receipt items
                for product in selected_products:
                    warranty_expiry = receipt_date + timedelta(days=30 * product['warranty_months'])
                    
                    ReceiptItem.objects.create(
                        receipt=receipt,
                        product_name=product['name'],
                        model=product['name'].split()[0],
                        serial_number=f'SN{random.randint(100000, 999999)}',
                        price=Decimal(product['price']) / 100,
                        quantity=1,
                        color=product['specs']['color'],
                        imei=f'IMEI{random.randint(100000000000000, 999999999999999)}' if 'Phone' in product['name'] or 'iPhone' in product['name'] else '',
                        storage=product['specs']['storage'],
                        warranty_coverage=f"{product['warranty_months']} months manufacturer warranty",
                        warranty_expiry=warranty_expiry
                    )
                
                receipts.append(receipt)
                receipt_count += 1
                
                if receipt_count % 5 == 0:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created {receipt_count} receipts...'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error creating receipt: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Total: {receipt_count} receipts created'))
        return receipts

    def create_warranties(self):
        """Create warranties for receipt items"""
        self.stdout.write(self.style.WARNING('\n🛡️  Creating Warranties...'))
        
        coverage_terms = [
            'Full hardware coverage including accidental damage',
            'Manufacturing defects, parts replacement',
            'Screen protection, battery replacement, water damage',
            'Complete device protection with free pickup and delivery',
            'Extended warranty with priority service',
        ]
        
        providers = [
            'Apple Inc.',
            'Samsung Electronics',
            'Manufacturer + Extended Protection',
            'TechCare Premium',
            'SmartGuard Insurance',
        ]
        
        warranties = []
        items = ReceiptItem.objects.filter(warranty__isnull=True)[:40]  # Create warranties for up to 40 items
        
        for item in items:
            try:
                # Calculate warranty period from item's warranty_coverage
                warranty_months = 12  # default
                if '24 months' in item.warranty_coverage or '2 year' in item.warranty_coverage.lower():
                    warranty_months = 24
                elif '36 months' in item.warranty_coverage or '3 year' in item.warranty_coverage.lower():
                    warranty_months = 36
                
                purchase_date = item.receipt.date
                expiry_date = purchase_date + timedelta(days=30 * warranty_months)
                
                warranty = Warranty.objects.create(
                    receipt_item=item,
                    coverage_period_months=warranty_months,
                    provider=random.choice(providers),
                    coverage_terms=random.choice(coverage_terms),
                    purchase_date=purchase_date,
                    expiry_date=expiry_date
                )
                warranties.append(warranty)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(warranties)} warranties'))
        return warranties

    def create_claims(self, customers, warranties):
        """Create claims for warranties"""
        self.stdout.write(self.style.WARNING('\n📋 Creating Claims...'))
        
        claim_scenarios = [
            {
                'summary': 'Screen cracked after accidental drop',
                'description': 'The device screen cracked when it accidentally fell from the table. The touch functionality is still working but there are visible cracks on the display.',
                'category': 'Accidental Damage',
                'priority': 'High',
            },
            {
                'summary': 'Battery draining too fast',
                'description': 'The battery is draining unusually fast, even with minimal usage. It drops from 100% to 20% within 3-4 hours of normal use.',
                'category': 'Manufacturing Defect',
                'priority': 'Medium',
            },
            {
                'summary': 'Device not turning on',
                'description': 'The device suddenly stopped turning on. Tried charging for several hours but no response. Power button is not responding.',
                'category': 'Malfunction',
                'priority': 'High',
            },
            {
                'summary': 'Camera producing blurry images',
                'description': 'The rear camera is producing blurry images even in good lighting conditions. Tried cleaning the lens but issue persists.',
                'category': 'Manufacturing Defect',
                'priority': 'Medium',
            },
            {
                'summary': 'Speaker making crackling noise',
                'description': 'The speaker produces crackling noise at higher volumes. Audio quality is significantly degraded.',
                'category': 'Manufacturing Defect',
                'priority': 'Low',
            },
            {
                'summary': 'Charging port not working',
                'description': 'The charging port is not recognizing the charging cable. Tried multiple cables but the issue remains.',
                'category': 'Malfunction',
                'priority': 'High',
            },
            {
                'summary': 'Overheating during normal use',
                'description': 'The device gets extremely hot during normal usage, making it uncomfortable to hold. Battery also drains faster when hot.',
                'category': 'Manufacturing Defect',
                'priority': 'High',
            },
            {
                'summary': 'Keyboard keys not responding',
                'description': 'Several keyboard keys are not responding properly. Have to press multiple times for input to register.',
                'category': 'Normal Wear',
                'priority': 'Medium',
            },
        ]
        
        statuses = ['In Review', 'In Review', 'Approved', 'Rejected']  # More "In Review"
        
        claims = []
        # Create 12-15 claims
        selected_warranties = random.sample(warranties, min(15, len(warranties)))
        
        for warranty in selected_warranties:
            try:
                scenario = random.choice(claim_scenarios)
                status = random.choice(statuses)
                
                claim = Claim.objects.create(
                    warranty=warranty,
                    issue_summary=scenario['summary'],
                    detailed_description=scenario['description'],
                    category=scenario['category'],
                    priority=scenario['priority'],
                    status=status,
                    estimated_cost=Decimal(random.randint(50, 500)) * 10000 / 100 if status in ['Approved', 'In Review'] else None,
                    actual_cost=Decimal(random.randint(50, 500)) * 10000 / 100 if status == 'Approved' else None,
                    created_by=warranty.customer
                )
                
                # Add some notes for In Review and Approved claims
                if status in ['In Review', 'Approved']:
                    ClaimNote.objects.create(
                        claim=claim,
                        author=warranty.retailer,
                        content='Claim received and under review. We will assess the issue and get back to you within 24-48 hours.'
                    )
                
                if status == 'Approved':
                    ClaimNote.objects.create(
                        claim=claim,
                        author=warranty.retailer,
                        content='Claim approved. Please bring your device to our service center for repair. Repair will be completed within 5-7 business days.'
                    )
                
                if status == 'Rejected':
                    ClaimNote.objects.create(
                        claim=claim,
                        author=warranty.retailer,
                        content='Unfortunately, this claim falls outside warranty coverage as it appears to be caused by physical damage not covered under the warranty terms.'
                    )
                
                claims.append(claim)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(claims)} claims with notes'))
        return claims

    def create_notifications(self, customers, retailers):
        """Create sample notifications"""
        self.stdout.write(self.style.WARNING('\n🔔 Creating Notifications...'))
        
        notification_count = 0
        
        # Welcome notifications for all users
        all_users = list(customers) + list(retailers)
        for user in all_users:
            try:
                Notification.objects.get_or_create(
                    user=user,
                    notification_type='WELCOME',
                    defaults={
                        'title': 'Welcome to Warranty Wallet!',
                        'message': f'Hi {user.full_name}, welcome to Warranty Wallet. Manage your warranties and claims easily.',
                    }
                )
                notification_count += 1
            except Exception as e:
                pass
        
        # Warranty expiring notifications for some customers
        for customer in random.sample(customers, min(3, len(customers))):
            try:
                Notification.objects.create(
                    user=customer,
                    notification_type='WARRANTY_EXPIRING',
                    title='Warranty Expiring Soon',
                    message='Your warranty for iPhone 15 Pro Max will expire in 30 days. Renew now to continue coverage.',
                )
                notification_count += 1
            except Exception as e:
                pass
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {notification_count} notifications'))

    def print_summary(self, customers, retailers, stores, receipts, warranties, claims):
        """Print final summary"""
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('✅ MOCK DATA POPULATION COMPLETE!'))
        self.stdout.write('='*70)
        self.stdout.write(self.style.WARNING(f'\n📊 Summary:'))
        self.stdout.write(f'   👥 Customers: {len(customers)}')
        self.stdout.write(f'   🏪 Retailers: {len(retailers)}')
        self.stdout.write(f'   🏢 Stores: {len(stores)}')
        self.stdout.write(f'   🧾 Receipts: {len(receipts)}')
        self.stdout.write(f'   📦 Receipt Items: {ReceiptItem.objects.count()}')
        self.stdout.write(f'   🛡️  Warranties: {len(warranties)}')
        self.stdout.write(f'   📋 Claims: {len(claims)}')
        self.stdout.write(f'   📝 Claim Notes: {ClaimNote.objects.count()}')
        self.stdout.write(f'   🔔 Notifications: {Notification.objects.count()}')
        
        self.stdout.write(self.style.WARNING(f'\n🔐 Login Credentials:'))
        self.stdout.write(f'   Password for all users: Test1234!')
        self.stdout.write(f'\n   Sample Customer: alisher.toshkent@gmail.com')
        self.stdout.write(f'   Sample Retailer: techno.store@gmail.com')
        
        self.stdout.write('\n' + '='*70 + '\n')

