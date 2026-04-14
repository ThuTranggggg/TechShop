"""
URL configuration for Identity module.

Routes for auth, profile, admin, and internal endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .presentation import views_auth, views_profile, views_admin, views_internal

# Create routers for viewsets
router = DefaultRouter()

app_name = "identity"

urlpatterns = [
    # Auth endpoints
    path("auth/register/", views_auth.RegisterView.as_view({"post": "register"}), name="register"),
    path("auth/login/", views_auth.CustomTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", views_auth.CustomTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", views_auth.LogoutView.as_view({"post": "logout"}), name="logout"),
    path("auth/me/", views_auth.MeView.as_view({"get": "me"}), name="me"),
    
    # Profile endpoints
    path("profile/", views_profile.ProfileViewSet.as_view({"get": "profile"}), name="profile"),
    path("profile/update/", views_profile.ProfileViewSet.as_view({"patch": "update_profile"}), name="update-profile"),
    path("profile/addresses/", views_profile.AddressViewSet.as_view({"get": "list", "post": "create"}), name="addresses"),
    path("profile/addresses/<uuid:pk>/", views_profile.AddressViewSet.as_view({"get": "retrieve", "patch": "update", "delete": "destroy"}), name="address-detail"),
    path("profile/addresses/<uuid:pk>/set-default/", views_profile.AddressViewSet.as_view({"post": "set_default"}), name="set-default-address"),
    
    # Admin endpoints
    path("admin/users/", views_admin.AdminUserViewSet.as_view({"get": "list_users"}), name="admin-users"),
    path("admin/users/detail/", views_admin.AdminUserViewSet.as_view({"get": "user_detail"}), name="admin-user-detail"),
    path("admin/users/update/", views_admin.AdminUserViewSet.as_view({"patch": "update_user"}), name="admin-user-update"),
    path("admin/users/deactivate/", views_admin.AdminUserViewSet.as_view({"post": "deactivate_user"}), name="admin-deactivate-user"),
    path("admin/users/activate/", views_admin.AdminUserViewSet.as_view({"post": "activate_user"}), name="admin-activate-user"),
    path("admin/users/change-role/", views_admin.AdminUserViewSet.as_view({"post": "change_role"}), name="admin-change-role"),
    path("admin/users/addresses/", views_admin.AdminUserViewSet.as_view({"get": "user_addresses"}), name="admin-user-addresses"),
    
    # Internal endpoints
    path("internal/users/get/", views_internal.InternalUserViewSet.as_view({"get": "get_user_by_id"}), name="internal-get-user"),
    path("internal/users/bulk/", views_internal.InternalUserViewSet.as_view({"post": "get_bulk_users"}), name="internal-bulk-users"),
    path("internal/users/status/", views_internal.InternalUserViewSet.as_view({"get": "get_user_status"}), name="internal-user-status"),
    path("internal/users/validate-active/", views_internal.InternalUserViewSet.as_view({"get": "validate_user_active"}), name="internal-validate-active"),
]
