# Inventory Service - Verification Checklist

Complete this checklist to verify that the inventory service is fully functional.

## ✅ Pre-Setup Requirements

- [ ] Python 3.11+ installed
- [ ] PostgreSQL 14+ installed and running
- [ ] Redis installed (optional but recommended)
- [ ] Git repository initialized

## ✅ Step 1: Environment Setup

```bash
# 1. Navigate to service
cd services/inventory_service

# 2. Create environment file
cp .env.example .env

# 3. Edit .env with your settings (especially DB credentials)
# Verify these settings match your local setup:
# - DB_HOST (usually localhost or docker hostname)
# - DB_USER / DB_PASSWORD
# - DB_NAME

# 4. Install dependencies
pip install -r requirements.txt
```

- [ ] .env file created
- [ ] Dependencies installed (check with: pip list | grep -E "Django|djangorestframework|psycopg")

## ✅ Step 2: Database Setup

```bash
# 1. Create migrations
python manage.py makemigrations modules.inventory

# 2. Run migrations
python manage.py migrate

# 3. Verify database tables
python dbshell
# Run: \dt  (show tables)
# Should see: stock_items, stock_reservations, stock_movements, warehouses

# 4. Seed sample data
python manage.py seed_inventory
```

- [ ] Migrations created successfully
- [ ] No migration errors
- [ ] Database tables created
- [ ] Sample data seeded

## ✅ Step 3: Create Admin User

```bash
python manage.py createsuperuser
# Follow prompts to create admin account
```

- [ ] Admin user created with username and password

## ✅ Step 4: Start Development Server

```bash
python manage.py runserver 0.0.0.0:8007
```

Server should start without errors. Watch for:
- No import errors
- No database connection errors  
- App lists include "modules.inventory"

- [ ] Server starts successfully on port 8007

## ✅ Step 5: Health Check APIs

```bash
# Test basic health endpoints
curl http://localhost:8007/health/
curl http://localhost:8007/ready/
curl http://localhost:8007/api/v1/health/
```

Expected response: `{"success": true, ...}`

- [ ] Health endpoint responds
- [ ] Ready endpoint responds
- [ ] No 404 or 500 errors

## ✅ Step 6: Admin Interface

1. Open browser: http://localhost:8007/admin/
2. Log in with created admin credentials
3. You should see:
   - Inventory section in sidebar
   - Stock Items (# items from seed)
   - Stock Reservations  
   - Stock Movements
   - Warehouses

- [ ] Admin interface loads
- [ ] Can log in with credentials
- [ ] Inventory models visible
- [ ] Sample data present

## ✅ Step 7: API Documentation

1. Open: http://localhost:8007/api/docs/
2. Should see Swagger UI with endpoints:
   - Admin Stock Items endpoints
   - Internal Inventory endpoints

- [ ] API docs load
- [ ] Can see endpoint schemas
- [ ] Try button works

## ✅ Step 8: Test Admin API

Set admin header in requests.

```bash
# List stock items
curl -X GET http://localhost:8007/api/v1/admin/inventory/stock-items/ \
  -H "X-Admin: true"
```

Expected response:
```json
{
  "success": true,
  "message": "Stock items retrieved",
  "data": {
    "total": 10,  // Should have seeded items
    "page": 1,
    "limit": 20,
    "items": [...]
  }
}
```

- [ ] List endpoint returns items
- [ ] Response format correct
- [ ] Seeded data present
- [ ] Pagination working

## ✅ Step 9: Test Create Stock Item

```bash
curl -X POST http://localhost:8007/api/v1/admin/inventory/stock-items/ \
  -H "Content-Type: application/json" \
  -H "X-Admin: true" \
  -d '{
    "product_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "warehouse_code": "MAIN",
    "on_hand_quantity": 50,
    "safety_stock": 5
  }'
```

Expected: 201 Created with stock item details

- [ ] Stock item created
- [ ] Returns 201 status
- [ ] Can see new item in GET list

## ✅ Step 10: Test Internal API

Set internal service key (from .env)

```bash
# Check availability
curl -X POST http://localhost:8007/api/v1/internal/inventory/check-availability/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: your-internal-service-key-here" \
  -d '{
    "items": [
      {
        "product_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "quantity": 10
      }
    ]
  }'
```

Expected:
```json
{
  "success": true,
  "message": "Availability checked",
  "data": {
    "items": [
      {
        "product_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "available_quantity": 50,
        "can_reserve": true,
        "is_in_stock": true
      }
    ]
  }
}
```

- [ ] Availability check works
- [ ] Returns correct quantities
- [ ] Can reserve status accurate

## ✅ Step 11: Test Stock Operations

### Stock In

```bash
# Get a stock item ID from the list
STOCK_ID="xxxx-xxxx-xxxx-xxxx"  # Replace with real ID

curl -X POST http://localhost:8007/api/v1/admin/inventory/stock-items/${STOCK_ID}/stock-in/ \
  -H "Content-Type: application/json" \
  -H "X-Admin: true" \
  -d '{
    "quantity": 20,
    "reference_id": "PO-001",
    "note": "Test stock in"
  }'
```

Expected: 200 OK with updated on_hand_quantity

- [ ] Stock in processes successfully
- [ ] on_hand_quantity increases
- [ ] Movement record created

### Stock Out

```bash
curl -X POST http://localhost:8007/api/v1/admin/inventory/stock-items/${STOCK_ID}/stock-out/ \
  -H "Content-Type: application/json" \
  -H "X-Admin: true" \
  -d '{
    "quantity": 5,
    "note": "Test stock out"
  }'
```

Expected: 200 OK with updated on_hand_quantity

- [ ] Stock out processes successfully
- [ ] on_hand_quantity decreases
- [ ] Available quantity reflects change

## ✅ Step 12: Test Reservations

```bash
# Create reservation
curl -X POST http://localhost:8007/api/v1/internal/inventory/reservations/ \
  -H "Content-Type: application/json" \
  -H "X-Internal-Service-Key: your-internal-service-key-here" \
  -d '{
    "product_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "quantity": 3,
    "order_id": "order-123",
    "expires_in_minutes": 30
  }'
```

Expected:
```json
{
  "success": true,
  "message": "Reservation created",
  "data": {
    "id": "reservation-uuid",
    "status": "active",
    "quantity": 3,
    "expires_at": "..."
  }
}
```

- [ ] Reservation created
- [ ] Status is "active"
- [ ] Expires_at set correctly
- [ ] reserved_quantity in stock item increased

## ✅ Step 13: Test Movements

```bash
curl -X GET http://localhost:8007/api/v1/admin/inventory/stock-items/${STOCK_ID}/movements/ \
  -H "X-Admin: true"
```

Should see array of movements with types: stock_in, stock_out, reservation_created, etc.

- [ ] Movements endpoint works
- [ ] Multiple movements recorded
- [ ] Movement types correct
- [ ] Timestamps accurate

## ✅ Step 14: Run Tests

```bash
# Run all tests
python manage.py test tests/

# Should pass with no failures
```

- [ ] All tests pass
- [ ] No test errors
- [ ] Coverage looks good

## ✅ Step 15: Database Verification

```bash
# Check database using Django shell
python manage.py dbshell

# Run these queries:
SELECT COUNT(*) FROM stock_items;
SELECT COUNT(*) FROM stock_reservations;
SELECT COUNT(*) FROM stock_movements;
SELECT COUNT(*) FROM warehouses;

# Should show seeded data counts
```

- [ ] Tables contain expected data
- [ ] Counts match seed output
- [ ] No database integrity issues

## ✅ Step 16: Permission Tests

Test that non-admin user cannot access admin endpoints:

```bash
# Without X-Admin header (should fail or return different response)
curl -X GET http://localhost:8007/api/v1/admin/inventory/stock-items/
```

- [ ] Returns error or empty
- [ ] Admin auth properly enforced

## ✅ Step 17: Error Handling

Test error cases:

```bash
# Try to create duplicate stock item
curl -X POST http://localhost:8007/api/v1/admin/inventory/stock-items/ \
  -H "Content-Type: application/json" \
  -H "X-Admin: true" \
  -d '{
    "product_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "warehouse_code": "MAIN",
    "on_hand_quantity": 100
  }'
```

Should return 400 error about duplicate

- [ ] Error response formatted correctly
- [ ] Error message is helpful
- [ ] HTTP status code appropriate

## ✅ Step 18: Cross-Service Compatibility

Verify it can be called from docker-compose:

```bash
# Start only database and inventory
docker-compose up -d inventory_service_db inventory_service

# Then hit the service
curl http://localhost:8007/health/
```

- [ ] Service starts in Docker
- [ ] Can communicate on network
- [ ] Database connection works

## ✅ Final Integration Check

1. **Check logs** - No errors or warnings during operation
2. **Monitor performance** - API responses < 200ms
3. **Admin interface** - Responsive and functional
4. **Documentation** - README and INVENTORY_SERVICE.md complete

- [ ] Logs are clean
- [ ] Performance acceptable
- [ ] All features documented

## 🎉 Success!

If all checkboxes are marked, your inventory_service is:
- ✅ Properly structured following DDD
- ✅ Database schema correct with constraints
- ✅ All APIs functional
- ✅ Admin interface working
- ✅ Tests passing
- ✅ Documentation complete
- ✅ Ready for integration with other services

## 🔧 Troubleshooting

### Database Connection Error
- Check DB_HOST, DB_USER, DB_PASSWORD in .env
- Verify PostgreSQL is running
- Check firewall rules

### Import Errors
- Ensure all required packages installed: `pip install -r requirements.txt`
- Python path includes service directory

### API Returns 404
- Server must be running on correct port (8007)
- Check URLs match exactly (case-sensitive)
- Verify modules.inventory is in INSTALLED_APPS

### Admin Interface shows no Inventory items
- Run: `python manage.py migrate`
- Run: `python manage.py seed_inventory`
- Check user has superuser permissions

### Tests fail
- Make sure test database can be created
- Check for conflicting processes on port
- Verify all models migrated: `python manage.py migrate`

### Permissions denied
- Check admin header: `X-Admin: true`
- Check internal key header: `X-Internal-Service-Key`
- Verify .env INTERNAL_SERVICE_KEY matches request

## 📞 Next Steps

1. **Integrate with Cart Service**
   - Cart calls check-availability endpoint
   - Cart calls reservations endpoint

2. **Integrate with Order Service**
   - Order confirms reservation on placement
   - Order releases reservation on cancellation

3. **Integrate with Payment Service**
   - Payment calls confirm-reservation on success
   - Payment calls release-reservation on failure

4. **Setup Background Jobs**
   - Expire old reservations periodically
   - Reconcile inventory at intervals

5. **Add Monitoring**
   - Log all inventory changes
   - Track reservation success rates
   - Monitor low stock alerts

---

**Verification Date**: _______________
**Verified By**: _______________
**Status**: ✅ READY FOR PRODUCTION
