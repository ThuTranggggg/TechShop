# User Service - Complete Implementation

## ��� Service Purpose & Overview

The **user_service** is the **Identity & User Management** bounded context for the TechShop microservices e-commerce platform. It handles all user-related operations and provides user information to other services.

### Core Responsibilities

- **User Account Management**: Registration, profile management, account lifecycle
- **Authentication & Authorization**: JWT-based auth with role-based access control (RBAC)
- **User Roles**: Customer, Staff, and Admin with appropriate permissions
- **User Profiles**: Comprehensive user information with verification status
- **Address Book**: Multi-address management with default address enforcement
- **Admin Operations**: User management, role assignment, account status control  
- **Internal Service API**: Provides user data to other microservices

### Domain Scope

This service manages the Identity bounded context:
- Email-based user identification (unique)
- Role hierarchy: customer < staff < admin
- Account lifecycle: registration → active/inactive → verified/unverified
- Address management: users can have multiple addresses, one as default
- Permission enforcement at API & business logic levels

---

## ���️ Architecture

### Design Principles

- **DDD (Domain-Driven Design)**: Separated into domain, application, infrastructure, presentation layers
- **JWT Authentication**: Stateless auth using `djangorestframework-simplejwt`
- **Custom User Model**: Email-based primary identifier with UUID primary key
- **RBAC**: Simple but extensible role-based permission system
- **Clean Code**: Separation of concerns, testable design, documented

### Directory Structure

```
services/user_service/
├── config/                                    # Django core
│   ├── settings.py                           # DRF, JWT, database config
│   ├── urls.py                               # Root URL routing
│   ├── wsgi.py & asgi.py                     # App servers
├── modules/identity/                         # Domain module (DDD structure)
│   ├── domain/                               # Business logic
│   │   ├── enums.py                          # UserRole, AddressType, etc.
│   │   └── entities.py                       # Domain entities
│   ├── infrastructure/                       # Persistence layer
│   │   ├── models.py                         # Django models (User, Address)
│   │   └── migrations/                       # Database migrations
│   ├── application/                          # Use cases (future)
│   ├── presentation/                         # API layer
│   │   ├── serializers.py                    # Request/response formatters
│   │   ├── permissions.py                    # DRF permission classes
│   │   ├── views_auth.py                     # Login, register, tokens
│   │   ├── views_profile.py                  # Profile & addresses
│   │   ├── views_admin.py                    # Admin user management
│   │   └── views_internal.py                 # Inter-service API
│   ├── admin.py                              # Django admin config
│   ├── apps.py                               # App configuration
│   ├── urls.py                               # Module URL routing
│   └── management/commands/seed_users.py     # Sample data generator
├── common/                                   # Shared utilities
│   ├── responses.py                          # Standard response format
│   ├── exceptions.py                         # Exception handling
│   ├── health.py                             # Health/readiness checks
│   └── logging.py                            # Structured logging
├── tests/test_identity.py                    # Comprehensive test suite
├── requirements.txt                          # Python dependencies
├── .env.example                              # Environment template
├── Dockerfile                                # Container image
└── README.md                                 # This file
```

### Key Design Decisions

1. **Custom User Model (not Django's default)**
   - Email as username (not separate username field)
   - UUID primary key for distributed systems
   - Direct support for roles (customer/staff/admin)
   - Extends AbstractBaseUser + PermissionsMixin

2. **Database Constraints**
   - Unique email address (indexed)
   - Unique default address per user
   - Foreign key from Address to User (CASCADE delete)

3. **JWT Authentication**
   - Access token: 5 minutes TTL
   - Refresh token: 24 hours TTL
   - Custom claims in token (email, role, full_name)
   - Stateless (no session storage needed)

4. **Permission Model**
   - DRF permission classes for each role
   - Ownership checks (users can only modify own profile)
   - Internal service auth via headers (placeholder)

5. **API Design**
   - Standard response format (success/data/errors)
   - Namespace separation (public/admin/internal)
   - Pagination support for list endpoints
   - Comprehensive error messages

---

## ��� Data Models

### User Model

```
id (UUID)                           # Primary key
email (string, unique, indexed)     # Login identifier
full_name (string)                  # User's full name
phone_number (string, optional)     # Contact number
date_of_birth (date, optional)      # Birthday
avatar_url (URL, optional)          # Profile picture
role (enum)                         # customer|staff|admin
is_active (bool)                    # Account active/inactive
is_verified (bool)                  # Email verified
is_staff (bool)                     # Django admin access
is_superuser (bool)                 # Admin superuser
created_at, updated_at (datetime)   # Timestamps
last_login (datetime)               # Last login timestamp
```

**Business Rules:**
- Email is unique identifier for login
- Only admins can create staff/admin users
- Role cannot be self-assigned by users
- Inactive users cannot login
- Default role for registration is "customer"

### Address Model

```
id (UUID)                           # Primary key
user (FK to User)                   # Owner of address
receiver_name (string)              # Who receives packages
phone_number (string)               # Contact for delivery
line1 (string)                      # Street address (required)
line2 (string, optional)            # Apartment/suite
ward (string, optional)             # Ward/commune
district (string)                   # District
city (string)                       # City/province
country (string)                    # Country (default: Vietnam)
postal_code (string, optional)      # Zip/postal code
address_type (enum)                 # home|office|other
is_default (bool)                   # Mark as default (unique per user)
created_at, updated_at (datetime)   # Timestamps
```

**Business Rules:**
- User can have multiple addresses
- Only one address can be default per user
- Setting an address as default automatically removes default from others
- User can only modify own addresses (via public API)
- Admin can view/modify any user's addresses

### Enums

**UserRole**
- `CUSTOMER` - Regular user (can purchase)
- `STAFF` - Staff member (can help customers)
- `ADMIN` - Administrator (full system access)

**AddressType**
- `HOME` - Residential address
- `OFFICE` - Work/office address
- `OTHER` - Other address types

**VerificationStatus**
- `UNVERIFIED` - Email not confirmed
- `VERIFIED` - Email confirmed
- `PENDING` - Verification in progress

---

## ��� API Endpoints

### 1. Authentication Endpoints (`/api/v1/auth/`)

#### Register
- **POST** `/auth/register/` - Public
- Creates new user with customer role only
- Validation: unique email, strong password
- Response: user info with JWT tokens

#### Login
- **POST** `/auth/login/` - Public
- Email + password authentication
- Returns: access token, refresh token, user info

#### Refresh Token
- **POST** `/auth/refresh/` - Public
- Exchanges refresh token for new access token
- Updates tokens if token rotation enabled

#### Get Current User
- **GET** `/auth/me/` - Requires auth
- Returns authenticated user's profile

#### Logout
- **POST** `/auth/logout/` - Requires auth
- Currently client-side focused (JWT has no session)
- Can implement token blacklist in future

### 2. Profile Endpoints (`/api/v1/profile/`)

#### Get Profile
- **GET** `/profile/` - Requires auth
- Returns current user's full profile

#### Update Profile
- **PATCH** `/profile/update/` - Requires auth
- Allowed fields: full_name, phone_number, date_of_birth, avatar_url
- Protected fields (read-only): email, role, is_active, is_verified

### 3. Address Endpoints (`/api/v1/profile/addresses/`)

#### Create Address
- **POST** `/addresses/` - Requires auth
- User creation creates address for themselves
- Returns: address object with ID

#### List Addresses  
- **GET** `/addresses/` - Requires auth
- Filters: address_type, is_default
- Returns: array of user's addresses

#### Get Address
- **GET** `/addresses/{id}/` - Requires auth & ownership

#### Update Address
- **PATCH** `/addresses/{id}/` - Requires auth & ownership

#### Delete Address
- **DELETE** `/addresses/{id}/` - Requires auth & ownership

#### Set as Default
- **POST** `/addresses/{id}/set-default/` - Requires auth & ownership
- Automatically removes default from other addresses

### 4. Admin Endpoints (`/api/v1/admin/users/`)

**Requires**: Authentication  + staff/admin role

#### List Users
- **GET** `/users/` - List all users
- Filters: role, is_active, search (email/name/phone)
- Ordering: created_at, email, updated_at
- Pagination: page, page_size (default 20)

#### Get User
- **GET** `/users/detail/?user_id={id}` - User details

#### Update User
- **PATCH** `/users/update/` - Update user fields

#### Deactivate User
- **POST** `/users/deactivate/` - Set is_active=false

#### Activate User
- **POST** `/users/activate/` - Set is_active=true

#### Change Role
- **POST** `/users/change-role/` - Assign new role
- Restrictions: only admin can promote to admin

#### Get User Addresses
- **GET** `/users/addresses/?user_id={id}` - All addresses for user

### 5. Internal Service API (`/api/v1/internal/users/`)

**Requires**: `X-Internal-Service` & `X-Internal-Token` headers

#### Get User
- **GET** `/get/?user_id={id}` - Basic user info

#### Bulk Get Users
- **POST** `/bulk/` - Multiple users by IDs
- Payload: `{"user_ids": ["uuid1", "uuid2"]}`

#### Get User Status
- **GET** `/status/?user_id={id}` - Active/verified status

#### Validate User Active
- **GET** `/validate-active/?user_id={id}` - Check if active

---

## ��� Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Docker & Docker Compose

### Local Development

#### 1. Setup

```bash
cd services/user_service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

#### 3. Database Setup

```bash
# Ensure PostgreSQL is running
# Then run migrations
python manage.py migrate
```

#### 4. Create Superuser

```bash
python manage.py createsuperuser
# Email: admin@techshop.com
# Password: AdminPassword123
```

#### 5. Seed Sample Data

```bash
python manage.py seed_users
```

Creates:
- admin@techshop.com (Admin role)
- staff@techshop.com (Staff role)
- john@example.com, jane@example.com, bob@example.com (Customer)
- Sample addresses for each user
- All use password: Demo@123456

#### 6. Run Server

```bash
python manage.py runserver 0.0.0.0:8001
```

#### 7. Access Services

- **API Docs**: http://localhost:8001/api/docs/
- **Admin Panel**: http://localhost:8001/admin/
- **Health Check**: http://localhost:8001/health/

### Docker Setup

#### Quick Start

```bash
# From repo root
docker-compose up --build user_service

# First time setup
docker-compose exec user_service python manage.py migrate
docker-compose exec user_service python manage.py seed_users
```

#### Verify

```bash
curl http://localhost:8001/health/
curl http://localhost:8001/api/docs/
```

---

## ��� Testing

### Run All Tests

```bash
python manage.py test tests/
```

### Run Specific Test Class

```bash
python manage.py test tests.test_identity.AuthenticationAPITest
python manage.py test tests.test_identity.AddressAPITest
python manage.py test tests.test_identity.AdminAPITest
```

### Run Specific Test

```bash
python manage.py test tests.test_identity.AuthenticationAPITest.test_register_success
```

### Coverage

Tests cover:

✅ **Model Tests** - User creation, uniqueness, constraints
✅ **Authentication** - Register, login, JWT tokens
✅ **Profile** - Get/update profile, field protection
✅ **Addresses** - CRUD, default address logic
✅ **Admin** - User listing, role changes, status updates
✅ **Internal API** - Service auth, bulk retrieval
✅ **Permissions** - RBAC enforcement, ownership checks

---

## ��� Security

### Authentication

- JWT with HS256 algorithm
- Access token: 5 min TTL
- Refresh token: 24 hour TTL
- Token rotation: enabled

### Password Security

- Uses Django's password validators
- Minimum length: 8 characters
- Must include mixed case
- Cannot be entirely numeric
- Hashed with PBKDF2

### Authorization

- Role-based access control (RBAC)
- Ownership validation for personal data
- Admin-only endpoints protected
- Internal service auth via headers

### Other Security Measures

- CORS configuration (adjust for production)
- No sensitive data in logs
- SQL injection prevention (ORM)
- CSRF protection on state-changing operations
- Input validation on all serializers

### Future Security Enhancements

- [ ] Email verification flow
- [ ] Token blacklist (Redis)
- [ ] Rate limiting per user/IP
- [ ] Audit logging
- [ ] 2FA/MFA support
- [ ] mTLS for service-to-service communication
- [ ] WAF (Web Application Firewall)

---

## ��� Usage Examples

### Register

```bash
curl -X POST http://localhost:8001/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "John Doe",
    "password": "SecurePass12345",
    "confirm_password": "SecurePass12345",
    "phone_number": "+84912345678"
  }'
```

### Login

```bash
curl -X POST http://localhost:8001/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass12345"
  }'
```

### Get CurrentUser

```bash
curl -X GET http://localhost:8001/api/v1/auth/me/ \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

### Create Address

```bash
curl -X POST http://localhost:8001/api/v1/profile/addresses/ \
  -H "Authorization: Bearer {ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "receiver_name": "John Doe",
    "phone_number": "+84912345678",
    "line1": "123 Main St",
    "district": "District 1",
    "city": "Ho Chi Minh",
    "country": "Vietnam",
    "address_type": "home"
  }'
```

### List Admin Users

```bash
curl -X GET "http://localhost:8001/api/v1/admin/users/?role=customer&is_active=true" \
  -H "Authorization: Bearer {ADMIN_TOKEN}"
```

---

## ��� Development Checklist

- [x] Custom user model with email auth
- [x] Address model with constraints
- [x] JWT authentication setup
- [x] DRF serializers & validation
- [x] Auth views (register, login, refresh, me)
- [x] Profile views (get, update)
- [x] Address CRUD views
- [x] Admin user management
- [x] Internal service API
- [x] Permission classes & RBAC
- [x] Django admin configuration
- [x] Migrations
- [x] Comprehensive tests
- [x] Sample data/seed command
- [x] Documentation
- [ ] Email verification (future)
- [ ] Token blacklist (future)
- [ ] Rate limiting (future)
- [ ] Audit logging (future)

---

## ��� Support & Debugging

### Check Service Health

```bash
curl http://localhost:8001/health/
```

### View Logs

```bash
# Docker
docker-compose logs -f user_service

# Local
python manage.py runserver --verbosity=2
```

### Access Django Shell

```bash
python manage.py shell

# Example queries:
>>> from modules.identity.infrastructure.models import User, Address
>>> User.objects.all()
>>> User.objects.get(email="admin@techshop.com")
```

### Access Admin Panel

- URL: http://localhost:8001/admin/
- Use superuser credentials
- Rich UI for User & Address management

---

## ✅ Production Deployment

Before deploying to production:

- [ ] Change SECRET_KEY to random value
- [ ] Set DEBUG=false
- [ ] Configure ALLOWED_HOSTS for your domain
- [ ] Use production database (not SQLite)
- [ ] Setup Redis for caching
- [ ] Implement token blacklist
- [ ] Configure proper CORS
- [ ] Enable HTTPS/SSL
- [ ] Setup logging & monitoring
- [ ] Run `python manage.py check --deploy`
- [ ] Load test the API
- [ ] Setup database backups
- [ ] Configure health checks for load balancer

---

## ��� Related Services

This service integrates with:

- **order_service** - Creates orders for users
- **cart_service** - Manages user carts
- **product_service** - User browsing/reviewing
- **payment_service** - Processes user payments
- **shipping_service** - User addresses for shipping
- **ai_service** - User preferences for recommendations

---

## ��� License

TechShop Platform - All Rights Reserved

---

**Last Updated**: April 2026  
**Version**: 1.0.0 (Production Ready)
