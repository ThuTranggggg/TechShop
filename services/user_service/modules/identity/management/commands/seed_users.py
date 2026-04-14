"""
Management command to seed sample data for testing and demo.

Creates sample users (admin, staff, customers) with addresses.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from modules.identity.infrastructure.models import User, Address
from modules.identity.domain.enums import UserRole, AddressType


class Command(BaseCommand):
    """Seed sample data for user service."""
    
    help = "Seed sample users and addresses for development and testing"
    
    def handle(self, *args, **options):
        """Execute the seed command."""
        with transaction.atomic():
            self.create_users()
            self.create_addresses()
        
        self.stdout.write(self.style.SUCCESS("✓ Sample data seeded successfully"))
    
    def create_users(self):
        """Create sample users."""
        users_data = [
            {
                "email": "admin@techshop.com",
                "full_name": "Admin User",
                "phone_number": "+84912345678",
                "role": UserRole.ADMIN,
                "is_verified": True,
            },
            {
                "email": "staff@techshop.com",
                "full_name": "Staff Member",
                "phone_number": "+84912345679",
                "role": UserRole.STAFF,
                "is_verified": True,
            },
            {
                "email": "john@example.com",
                "full_name": "John Doe",
                "phone_number": "+84912345680",
                "role": UserRole.CUSTOMER,
                "is_verified": True,
            },
            {
                "email": "jane@example.com",
                "full_name": "Jane Smith",
                "phone_number": "+84912345681",
                "role": UserRole.CUSTOMER,
                "is_verified": True,
            },
            {
                "email": "bob@example.com",
                "full_name": "Bob Johnson",
                "phone_number": "+84912345682",
                "role": UserRole.CUSTOMER,
                "is_verified": False,
            },
        ]
        
        for user_data in users_data:
            if User.objects.filter(email=user_data["email"]).exists():
                self.stdout.write(
                    self.style.WARNING(f"  ✗ User {user_data['email']} already exists, skipping")
                )
                continue
            
            password = "Demo@123456"
            user = User.objects.create_user(
                email=user_data["email"],
                password=password,
                full_name=user_data["full_name"],
                phone_number=user_data["phone_number"],
                role=user_data["role"],
                is_verified=user_data.get("is_verified", False),
                is_staff=user_data["role"] != UserRole.CUSTOMER,
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Created {user_data['role'].upper()}: {user_data['email']}")
            )
    
    def create_addresses(self):
        """Create sample addresses for users."""
        # Address data mapped to user emails
        addresses_data = [
            {
                "user_email": "john@example.com",
                "addresses": [
                    {
                        "receiver_name": "John Doe",
                        "phone_number": "+84912345680",
                        "line1": "123 Tran Hung Dao",
                        "line2": "Building A",
                        "ward": "Ward 1",
                        "district": "District 1",
                        "city": "Ho Chi Minh",
                        "country": "Vietnam",
                        "postal_code": "700000",
                        "address_type": AddressType.HOME,
                        "is_default": True,
                    },
                    {
                        "receiver_name": "John Doe",
                        "phone_number": "+84912345680",
                        "line1": "456 Nguyen Hue",
                        "line2": "Floor 5",
                        "district": "District 5",
                        "city": "Ho Chi Minh",
                        "country": "Vietnam",
                        "postal_code": "700000",
                        "address_type": AddressType.OFFICE,
                        "is_default": False,
                    },
                ]
            },
            {
                "user_email": "jane@example.com",
                "addresses": [
                    {
                        "receiver_name": "Jane Smith",
                        "phone_number": "+84912345681",
                        "line1": "789 Vo Thi Sau",
                        "ward": "Ward 2",
                        "district": "District 3",
                        "city": "Ho Chi Minh",
                        "country": "Vietnam",
                        "postal_code": "700000",
                        "address_type": AddressType.HOME,
                        "is_default": True,
                    },
                ]
            },
            {
                "user_email": "bob@example.com",
                "addresses": [
                    {
                        "receiver_name": "Bob Johnson",
                        "phone_number": "+84912345682",
                        "line1": "321 Cach Mang Thang Tam",
                        "ward": "Ward 5",
                        "district": "District 10",
                        "city": "Ho Chi Minh",
                        "country": "Vietnam",
                        "postal_code": "700000",
                        "address_type": AddressType.HOME,
                        "is_default": True,
                    },
                ]
            },
        ]
        
        for user_addresses in addresses_data:
            user_email = user_addresses["user_email"]
            
            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ User {user_email} not found, skipping addresses")
                )
                continue
            
            for addr_data in user_addresses["addresses"]:
                if Address.objects.filter(user=user, line1=addr_data["line1"]).exists():
                    continue
                
                Address.objects.create(
                    user=user,
                    **addr_data
                )
            
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Created {len(user_addresses['addresses'])} addresses for {user_email}")
            )
