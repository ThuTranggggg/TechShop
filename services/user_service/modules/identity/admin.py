"""
Admin configuration is disabled.

User management is handled exclusively through the REST API.
See URLs in modules/identity/urls.py for admin operations:
  - GET /api/v1/admin/users/ - List all users
  - GET /api/v1/admin/users/{id}/detail/ - Get user details
  - PATCH /api/v1/admin/users/{id}/update/ - Update user
  - POST /api/v1/admin/users/{id}/deactivate/ - Deactivate user
  - POST /api/v1/admin/users/{id}/activate/ - Activate user
  - PUT /api/v1/admin/users/{id}/change-role/ - Change user role

To create a superuser, use the management command:
    python manage.py seed_users
"""
