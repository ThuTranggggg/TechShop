"""
Authentication views for Identity context.

Handles user registration, login, token refresh, and logout.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from common.responses import success_response, error_response
from ..infrastructure.models import User
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
)


class RegisterView(viewsets.ViewSet):
    """User registration endpoint."""
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        """Register a new user (customer role only)."""
        serializer = RegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            return success_response(
                message="User registered successfully",
                data=UserProfileSerializer(user).data,
                http_status=status.HTTP_201_CREATED
            )
        
        return error_response(
            message="Registration failed",
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login endpoint that returns user info with tokens."""
    
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Handle login request."""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Update last login - get user from request email
            email = request.data.get("email")
            user = User.objects.get(email=email)
            user.last_login = None  # Let Django set it automatically
            user.save(update_fields=["last_login"])
            
            return success_response(
                message="Login successful",
                data={
                    "access": str(serializer.validated_data["access"]),
                    "refresh": str(serializer.validated_data["refresh"]),
                    "user": UserProfileSerializer(user).data,
                },
                http_status=status.HTTP_200_OK
            )
        
        return error_response(
            message="Login failed",
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CustomTokenRefreshView(TokenRefreshView):
    """Custom token refresh endpoint."""
    
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Handle token refresh request."""
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            return success_response(
                message="Token refreshed successfully",
                data=response.data,
                http_status=status.HTTP_200_OK
            )
        
        return error_response(
            message="Token refresh failed",
            errors=response.data,
            http_status=response.status_code
        )


class MeView(viewsets.ViewSet):
    """Get current user info endpoint."""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current authenticated user's profile."""
        serializer = UserProfileSerializer(request.user)
        
        return success_response(
            message="Current user info",
            data=serializer.data,
            http_status=status.HTTP_200_OK
        )


class LogoutView(viewsets.ViewSet):
    """Logout endpoint."""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout user.
        
        Note: With JWT, logout is typically handled on the client side by removing tokens.
        This endpoint can be used for:
        - Token blacklisting (if implemented)
        - Audit logging
        - Invalidating refresh tokens (future feature)
        """
        return success_response(
            message="Logged out successfully",
            http_status=status.HTTP_200_OK
        )
