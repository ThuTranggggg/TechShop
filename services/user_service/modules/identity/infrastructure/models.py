"""
Infrastructure layer - Django models for Identity context.

These models map domain entities to database persistence.
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

from ..domain.enums import UserRole, AddressType, VerificationStatus


class CustomUserManager(BaseUserManager):
    """Custom manager for User model."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError("Email is required")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_verified", True)
        
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True")
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as primary identifier.
    
    This model extends Django's AbstractBaseUser to provide a production-ready
    user model that uses email for authentication instead of username.
    
    Fields:
        id: UUID primary key
        email: Unique email identifier
        full_name: User's full name
        phone_number: Optional phone number
        date_of_birth: Optional date of birth
        avatar_url: Optional avatar URL
        role: User role (customer, staff, admin)
        is_active: Whether account is active
        is_verified: Whether email is verified
        is_staff: Django staff flag (for admin access)
        is_superuser: Django superuser flag
        last_login: Last login timestamp
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices(),
        default=UserRole.CUSTOMER,
        db_index=True
    )
    
    is_active = models.BooleanField(default=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    
    class Meta:
        db_table = "identity_user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    @property
    def is_admin(self):
        """Check if user is admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_staff_member(self):
        """Check if user is staff."""
        return self.role == UserRole.STAFF
    
    @property
    def is_customer(self):
        """Check if user is customer."""
        return self.role == UserRole.CUSTOMER


class Address(models.Model):
    """
    User address model.
    
    Represents a user's address for shipping or billing purposes.
    Each user can have multiple addresses with one marked as default.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        db_index=True
    )
    
    receiver_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    
    line1 = models.CharField(max_length=255, help_text="Street address (required)")
    line2 = models.CharField(max_length=255, blank=True, null=True, help_text="Apartment, suite, etc.")
    ward = models.CharField(max_length=100, blank=True, null=True, help_text="Ward/Commune")
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Vietnam")
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices(),
        default=AddressType.HOME
    )
    
    is_default = models.BooleanField(default=False, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "identity_address"
        ordering = ["-is_default", "-created_at"]
        indexes = [
            models.Index(fields=["user", "is_default"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "is_default"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_user"
            )
        ]
    
    def __str__(self):
        return f"{self.receiver_name} - {self.city}, {self.country}"
    
    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [self.line1]
        if self.line2:
            parts.append(self.line2)
        if self.ward:
            parts.append(self.ward)
        parts.extend([self.district, self.city, self.country])
        if self.postal_code:
            parts.append(self.postal_code)
        return ", ".join(filter(None, parts))
    
    def save(self, *args, **kwargs):
        """Override save to enforce single default address per user."""
        if self.is_default:
            # Remove default from other addresses of this user
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
