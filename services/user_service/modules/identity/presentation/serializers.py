"""
Serializers for Identity context API.

Handles validation and serialization of User, Address, and related data.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from ..infrastructure.models import User, Address
from ..domain.enums import UserRole, AddressType


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Must be at least 8 characters with mixed case and numbers"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"}
    )
    
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "password", "confirm_password", "phone_number")
        extra_kwargs = {
            "id": {"read_only": True},
            "email": {"required": True},
            "full_name": {"required": True},
        }
    
    def validate_email(self, value):
        """Ensure email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_password(self, value):
        """Validate password strength."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
    def validate(self, data):
        """Ensure passwords match."""
        if data["password"] != data.pop("confirm_password"):
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data
    
    def create(self, validated_data):
        """Create user with customer role by default."""
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            phone_number=validated_data.get("phone_number"),
            role=UserRole.CUSTOMER,  # Always customer for public registration
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        """Authenticate user."""
        email = data.get("email")
        password = data.get("password")
        
        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is deactivated")
        
        data["user"] = user
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user info."""
    
    def get_token(self, user):
        """Add custom claims to token."""
        token = super().get_token(user)
        
        # Add custom claims
        token["email"] = user.email
        token["full_name"] = user.full_name
        token["role"] = user.role
        
        return token


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile display."""
    
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone_number", "date_of_birth", 
                  "avatar_url", "role", "is_active", "is_verified", "created_at", 
                  "updated_at", "last_login")
        read_only_fields = ("id", "email", "role", "is_active", "is_verified", 
                           "created_at", "updated_at", "last_login")


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile (limited fields)."""
    
    class Meta:
        model = User
        fields = ("full_name", "phone_number", "date_of_birth", "avatar_url")
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and not value.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise serializers.ValidationError("Invalid phone number format")
        return value


class AddressSerializer(serializers.ModelSerializer):
    """Serializer for Address model."""
    
    full_address = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Address
        fields = ("id", "receiver_name", "phone_number", "line1", "line2", "ward",
                  "district", "city", "country", "postal_code", "address_type",
                  "is_default", "full_address", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at", "full_address")
    
    def get_full_address(self, obj):
        """Get formatted full address."""
        return obj.full_address


class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer for admin user listing."""
    
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone_number", "role", "is_active",
                  "is_verified", "created_at", "last_login")
        read_only_fields = fields


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Serializer for admin user detail view."""
    
    addresses = AddressSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone_number", "date_of_birth",
                  "avatar_url", "role", "is_active", "is_verified", "is_staff",
                  "addresses", "created_at", "updated_at", "last_login")
        read_only_fields = ("id", "created_at", "updated_at")


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin updating user (role, status)."""
    
    class Meta:
        model = User
        fields = ("full_name", "phone_number", "date_of_birth", "avatar_url")


class AdminUserRoleChangeSerializer(serializers.Serializer):
    """Serializer for changing user role."""
    
    role = serializers.ChoiceField(
        choices=[role[0] for role in UserRole.choices()],
        help_text="New role for the user"
    )
    
    def validate_role(self, value):
        """Validate role is valid."""
        valid_roles = [role.value for role in UserRole]
        if value not in valid_roles:
            raise serializers.ValidationError(f"Invalid role. Must be one of: {valid_roles}")
        return value


class InternalUserBasicSerializer(serializers.ModelSerializer):
    """Serializer for internal basic user info."""
    
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "role", "is_active", "is_verified")
        read_only_fields = fields


class InternalUserBulkSerializer(serializers.Serializer):
    """Serializer for internal bulk user info retrieval."""
    
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of user IDs to retrieve"
    )


class InternalUserStatusSerializer(serializers.Serializer):
    """Serializer for internal user status check."""
    
    is_active = serializers.BooleanField()
    is_verified = serializers.BooleanField()
    role = serializers.CharField()
