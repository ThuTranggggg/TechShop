"""
Comprehensive tests for Identity module.

Tests for authentication, profile management, addresses, admin operations, and permissions.
"""
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.hashers import make_password
import json

from modules.identity.infrastructure.models import User, Address
from modules.identity.domain.enums import UserRole, AddressType


class UserModelTest(TestCase):
    """Tests for User model."""
    
    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(
            email="test@example.com",
            password="TestPassword123",
            full_name="Test User"
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.role, UserRole.CUSTOMER)
        self.assertTrue(user.check_password("TestPassword123"))
        self.assertFalse(user.is_staff)
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123",
            full_name="Admin User"
        )
        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_verified)
    
    def test_email_unique(self):
        """Test that email is unique."""
        User.objects.create_user(
            email="unique@example.com",
            password="Password123",
            full_name="User 1"
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                email="unique@example.com",
                password="Password123",
                full_name="User 2"
            )
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(
            email="test@example.com",
            password="Password123",
            full_name="Test User"
        )
        self.assertEqual(str(user), "Test User (test@example.com)")


class AddressModelTest(TestCase):
    """Tests for Address model."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            email="test@example.com",
            password="Password123",
            full_name="Test User"
        )
    
    def test_create_address(self):
        """Test creating an address."""
        address = Address.objects.create(
            user=self.user,
            receiver_name="John Doe",
            phone_number="+84912345678",
            line1="123 Main St",
            district="District 1",
            city="Ho Chi Minh",
            country="Vietnam",
            address_type=AddressType.HOME
        )
        self.assertEqual(address.receiver_name, "John Doe")
        self.assertEqual(address.user, self.user)
    
    def test_default_address_uniqueness(self):
        """Test that only one address can be default per user."""
        addr1 = Address.objects.create(
            user=self.user,
            receiver_name="John Doe",
            phone_number="+84912345678",
            line1="123 Main St",
            district="District 1",
            city="Ho Chi Minh",
            country="Vietnam",
            is_default=True
        )
        
        addr2 = Address.objects.create(
            user=self.user,
            receiver_name="Jane Doe",
            phone_number="+84912345679",
            line1="456 Oak Ave",
            district="District 2",
            city="Ho Chi Minh",
            country="Vietnam",
            is_default=True
        )
        
        # Refresh addr1 from DB
        addr1.refresh_from_db()
        
        # Only addr2 should be default
        self.assertTrue(addr2.is_default)
        self.assertFalse(addr1.is_default)


class AuthenticationAPITest(APITestCase):
    """Tests for authentication endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
    
    def test_register_success(self):
        """Test successful user registration."""
        data = {
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123",
            "phone_number": "+84912345678"
        }
        
        response = self.client.post(reverse("identity:register"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "newuser@example.com")
        self.assertEqual(response.data["data"]["role"], UserRole.CUSTOMER)
        
        # Verify user was created
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        User.objects.create_user(
            email="existing@example.com",
            password="Password123",
            full_name="Existing User"
        )
        
        data = {
            "email": "existing@example.com",
            "full_name": "Another User",
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123"
        }
        
        response = self.client.post(reverse("identity:register"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
    
    def test_register_weak_password(self):
        """Test registration with weak password."""
        data = {
            "email": "user@example.com",
            "full_name": "User",
            "password": "123",
            "confirm_password": "123"
        }
        
        response = self.client.post(reverse("identity:register"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
    
    def test_register_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = {
            "email": "user@example.com",
            "full_name": "User",
            "password": "SecurePassword123",
            "confirm_password": "DifferentPassword123"
        }
        
        response = self.client.post(reverse("identity:register"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
    
    def test_login_success(self):
        """Test successful login."""
        user = User.objects.create_user(
            email="user@example.com",
            password="TestPassword123",
            full_name="Test User"
        )
        
        data = {
            "email": "user@example.com",
            "password": "TestPassword123"
        }
        
        response = self.client.post(reverse("identity:login"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"])
        self.assertIn("refresh", response.data["data"])
        self.assertEqual(response.data["data"]["user"]["email"], "user@example.com")
    
    def test_login_wrong_password(self):
        """Test login with wrong password."""
        User.objects.create_user(
            email="user@example.com",
            password="CorrectPassword123",
            full_name="Test User"
        )
        
        data = {
            "email": "user@example.com",
            "password": "WrongPassword123"
        }
        
        response = self.client.post(reverse("identity:login"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
    
    def test_login_inactive_user(self):
        """Test login with inactive user."""
        user = User.objects.create_user(
            email="user@example.com",
            password="TestPassword123",
            full_name="Test User"
        )
        user.is_active = False
        user.save()
        
        data = {
            "email": "user@example.com",
            "password": "TestPassword123"
        }
        
        response = self.client.post(reverse("identity:login"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
    
    def test_get_current_user_authenticated(self):
        """Test getting current user info when authenticated."""
        user = User.objects.create_user(
            email="user@example.com",
            password="TestPassword123",
            full_name="Test User"
        )
        
        self.client.force_authenticate(user)
        response = self.client.get(reverse("identity:me"))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "user@example.com")
    
    def test_get_current_user_not_authenticated(self):
        """Test getting current user when not authenticated."""
        response = self.client.get(reverse("identity:me"))
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileAPITest(APITestCase):
    """Tests for profile endpoints."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            email="user@example.com",
            password="Password123",
            full_name="John Doe",
            phone_number="+84912345678"
        )
    
    def setUp(self):
        """Set up test client and authenticate."""
        self.client = APIClient()
        self.client.force_authenticate(self.user)
    
    def test_get_profile(self):
        """Test getting user profile."""
        response = self.client.get(reverse("identity:profile"))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "user@example.com")
        self.assertEqual(response.data["data"]["full_name"], "John Doe")
    
    def test_update_profile(self):
        """Test updating user profile."""
        data = {
            "full_name": "Jane Doe",
            "phone_number": "+84987654321"
        }
        
        response = self.client.patch(reverse("identity:update-profile"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["full_name"], "Jane Doe")
        
        # Verify changes were saved
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Jane Doe")


class AddressAPITest(APITestCase):
    """Tests for address endpoints."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            email="user@example.com",
            password="Password123",
            full_name="Test User"
        )
        cls.other_user = User.objects.create_user(
            email="other@example.com",
            password="Password123",
            full_name="Other User"
        )
    
    def setUp(self):
        """Set up test client and authenticate."""
        self.client = APIClient()
        self.client.force_authenticate(self.user)
    
    def test_create_address(self):
        """Test creating an address."""
        data = {
            "receiver_name": "John Doe",
            "phone_number": "+84912345678",
            "line1": "123 Main St",
            "district": "District 1",
            "city": "Ho Chi Minh",
            "country": "Vietnam",
            "address_type": AddressType.HOME
        }
        
        response = self.client.post(reverse("identity:addresses"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["receiver_name"], "John Doe")
    
    def test_list_addresses(self):
        """Test listing user addresses."""
        Address.objects.create(
            user=self.user,
            receiver_name="John Doe",
            phone_number="+84912345678",
            line1="123 Main St",
            district="District 1",
            city="Ho Chi Minh",
            country="Vietnam"
        )
        
        response = self.client.get(reverse("identity:addresses"))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(response.data["data"]), 1)
    
    def test_set_default_address(self):
        """Test setting an address as default."""
        addr1 = Address.objects.create(
            user=self.user,
            receiver_name="John Doe",
            phone_number="+84912345678",
            line1="123 Main St",
            district="District 1",
            city="Ho Chi Minh",
            country="Vietnam",
            is_default=True
        )
        
        addr2 = Address.objects.create(
            user=self.user,
            receiver_name="Jane Doe",
            phone_number="+84912345679",
            line1="456 Oak Ave",
            district="District 2",
            city="Ho Chi Minh",
            country="Vietnam",
            is_default=False
        )
        
        response = self.client.post(
            reverse("identity:set-default-address", kwargs={"pk": addr2.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        
        # Verify default changed
        addr1.refresh_from_db()
        addr2.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)


class AdminAPITest(APITestCase):
    """Tests for admin endpoints."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPass123",
            full_name="Admin User"
        )
        cls.staff = User.objects.create_user(
            email="staff@example.com",
            password="StaffPass123",
            full_name="Staff Member",
            role=UserRole.STAFF
        )
        cls.customer = User.objects.create_user(
            email="customer@example.com",
            password="CustomerPass123",
            full_name="Customer User"
        )
    
    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
    
    def test_admin_list_users_requires_auth(self):
        """Test that list users requires authentication."""
        response = self.client.get(reverse("identity:admin-users"))
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_list_users_requires_staff(self):
        """Test that list users requires staff/admin role."""
        self.client.force_authenticate(self.customer)
        
        response = self.client.get(reverse("identity:admin-users"))
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_list_users_staff_access(self):
        """Test that staff can list users."""
        self.client.force_authenticate(self.staff)
        
        response = self.client.get(reverse("identity:admin-users"))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertGreater(response.data["data"]["count"], 0)
    
    def test_admin_deactivate_user(self):
        """Test admin deactivating a user."""
        self.client.force_authenticate(self.admin)
        
        data = {"user_id": str(self.customer.id)}
        response = self.client.post(reverse("identity:admin-deactivate-user"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
    
    def test_admin_change_role(self):
        """Test admin changing user role."""
        self.client.force_authenticate(self.admin)
        
        data = {
            "user_id": str(self.customer.id),
            "role": UserRole.STAFF
        }
        
        response = self.client.post(reverse("identity:admin-change-role"), data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, UserRole.STAFF)


class InternalAPITest(APITestCase):
    """Tests for internal service API endpoints."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = User.objects.create_user(
            email="user@example.com",
            password="Password123",
            full_name="Test User",
            is_verified=True,
            is_active=True
        )
    
    def setUp(self):
        """Set up test client with internal headers."""
        self.client = APIClient()
        self.internal_headers = {
            "HTTP_X_INTERNAL_SERVICE": "order_service",
            "HTTP_X_INTERNAL_TOKEN": "internal-service-token"
        }
    
    def test_internal_get_user_no_auth(self):
        """Test that internal endpoint requires auth headers."""
        response = self.client.get(
            reverse("identity:internal-get-user") + f"?user_id={self.user.id}"
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_internal_get_user_with_auth(self):
        """Test internal endpoint to get user."""
        response = self.client.get(
            reverse("identity:internal-get-user") + f"?user_id={self.user.id}",
            **self.internal_headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email"], "user@example.com")
    
    def test_internal_get_user_status(self):
        """Test internal endpoint to check user status."""
        response = self.client.get(
            reverse("identity:internal-user-status") + f"?user_id={self.user.id}",
            **self.internal_headers
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["data"]["is_active"])
        self.assertTrue(response.data["data"]["is_verified"])
