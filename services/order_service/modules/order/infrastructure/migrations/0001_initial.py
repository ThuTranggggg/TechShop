"""
Initial migration for Order service models.
"""

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OrderModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order_number', models.CharField(db_index=True, help_text='Human-readable order number (ORD-YYYYMMDD-XXXXXX)', max_length=32, unique=True)),
                ('user_id', models.UUIDField(db_index=True, help_text='Customer user ID (from user_service)')),
                ('cart_id', models.UUIDField(blank=True, db_index=True, help_text='Source cart ID (reference only)', null=True)),
                ('status', models.CharField(choices=[('pending', 'pending'), ('awaiting_payment', 'awaiting_payment'), ('paid', 'paid'), ('processing', 'processing'), ('shipping', 'shipping'), ('delivered', 'delivered'), ('completed', 'completed'), ('cancelled', 'cancelled'), ('payment_failed', 'payment_failed')], db_index=True, default='pending', max_length=32)),
                ('payment_status', models.CharField(choices=[('unpaid', 'unpaid'), ('pending', 'pending'), ('authorized', 'authorized'), ('paid', 'paid'), ('failed', 'failed'), ('refunded', 'refunded'), ('partially_refunded', 'partially_refunded')], db_index=True, default='unpaid', max_length=32)),
                ('fulfillment_status', models.CharField(choices=[('unfulfilled', 'unfulfilled'), ('preparing', 'preparing'), ('shipped', 'shipped'), ('delivered', 'delivered'), ('returned', 'returned'), ('cancelled', 'cancelled')], db_index=True, default='unfulfilled', max_length=32)),
                ('currency', models.CharField(choices=[('USD', 'USD'), ('VND', 'VND'), ('EUR', 'EUR')], default='VND', max_length=3)),
                ('subtotal_amount', models.DecimalField(decimal_places=2, default='0', max_digits=19)),
                ('shipping_fee_amount', models.DecimalField(decimal_places=2, default='0', max_digits=19)),
                ('discount_amount', models.DecimalField(decimal_places=2, default='0', max_digits=19)),
                ('tax_amount', models.DecimalField(decimal_places=2, default='0', max_digits=19)),
                ('grand_total_amount', models.DecimalField(decimal_places=2, default='0', max_digits=19)),
                ('total_quantity', models.IntegerField(default=0, help_text='Total quantity of all items')),
                ('item_count', models.IntegerField(default=0, help_text='Number of unique order items')),
                ('customer_name_snapshot', models.CharField(max_length=255)),
                ('customer_email_snapshot', models.EmailField(max_length=254)),
                ('customer_phone_snapshot', models.CharField(blank=True, default='', max_length=20)),
                ('receiver_name', models.CharField(max_length=255)),
                ('receiver_phone', models.CharField(max_length=20)),
                ('shipping_line1', models.CharField(max_length=255)),
                ('shipping_line2', models.CharField(blank=True, default='', max_length=255)),
                ('shipping_ward', models.CharField(blank=True, default='', max_length=100)),
                ('shipping_district', models.CharField(max_length=100)),
                ('shipping_city', models.CharField(max_length=100)),
                ('shipping_country', models.CharField(default='Vietnam', max_length=100)),
                ('shipping_postal_code', models.CharField(blank=True, default='', max_length=20)),
                ('payment_id', models.UUIDField(blank=True, help_text='Payment service order ID', null=True)),
                ('payment_reference', models.CharField(blank=True, default='', max_length=255)),
                ('shipment_id', models.UUIDField(blank=True, help_text='Shipping service shipment ID', null=True)),
                ('shipment_reference', models.CharField(blank=True, default='', max_length=255)),
                ('stock_reservation_refs', models.JSONField(default=list, help_text='Array of stock reservation references from inventory_service')),
                ('notes', models.TextField(blank=True, default='')),
                ('placed_at', models.DateTimeField(blank=True, help_text='When order was successfully placed', null=True)),
                ('paid_at', models.DateTimeField(blank=True, help_text='When payment was confirmed', null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, help_text='When order was cancelled', null=True)),
                ('completed_at', models.DateTimeField(blank=True, help_text='When order was completed', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Order',
                'verbose_name_plural': 'Orders',
                'db_table': 'order_ordermodel',
            },
        ),
        migrations.CreateModel(
            name='OrderStatusHistoryModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('from_status', models.CharField(blank=True, help_text='Previous status (null for initial)', max_length=32, null=True)),
                ('to_status', models.CharField(help_text='New status', max_length=32)),
                ('note', models.TextField(blank=True, default='')),
                ('changed_by', models.UUIDField(blank=True, help_text='User who made the change (null if system)', null=True)),
                ('metadata', models.JSONField(default=dict, help_text='Additional metadata about the transition')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='status_history', to='order.ordermodel')),
            ],
            options={
                'verbose_name': 'Order Status History',
                'verbose_name_plural': 'Order Status Histories',
                'db_table': 'order_orderstatushistorymodel',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItemModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('product_id', models.UUIDField(db_index=True, help_text='Product ID from product_service')),
                ('variant_id', models.UUIDField(blank=True, help_text='Product variant ID if applicable', null=True)),
                ('sku', models.CharField(blank=True, default='', max_length=100)),
                ('quantity', models.IntegerField(help_text='Quantity ordered')),
                ('unit_price', models.DecimalField(decimal_places=2, help_text='Price per unit at time of purchase', max_digits=19)),
                ('line_total', models.DecimalField(decimal_places=2, help_text='Quantity * unit_price', max_digits=19)),
                ('currency', models.CharField(choices=[('USD', 'USD'), ('VND', 'VND'), ('EUR', 'EUR')], default='VND', max_length=3)),
                ('product_name_snapshot', models.CharField(help_text='Product name at purchase time', max_length=255)),
                ('product_slug_snapshot', models.CharField(help_text='Product slug at purchase time', max_length=255)),
                ('variant_name_snapshot', models.CharField(blank=True, default='', help_text='Variant name if applicable', max_length=255)),
                ('brand_name_snapshot', models.CharField(blank=True, default='', max_length=255)),
                ('category_name_snapshot', models.CharField(blank=True, default='', max_length=255)),
                ('thumbnail_url_snapshot', models.URLField(blank=True, default='')),
                ('attributes_snapshot', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='order.ordermodel')),
            ],
            options={
                'verbose_name': 'Order Item',
                'verbose_name_plural': 'Order Items',
                'db_table': 'order_orderitemmodel',
            },
        ),
        migrations.AddIndex(
            model_name='orderstatushistorymodel',
            index=models.Index(fields=['order_id'], name='order_order_order_i_idx'),
        ),
        migrations.AddIndex(
            model_name='orderstatushistorymodel',
            index=models.Index(fields=['created_at'], name='order_order_created_idx'),
        ),
        migrations.AddIndex(
            model_name='orderstatushistorymodel',
            index=models.Index(fields=['to_status'], name='order_order_to_status_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitemmodel',
            index=models.Index(fields=['order_id'], name='order_order_order_i_idx2'),
        ),
        migrations.AddIndex(
            model_name='orderitemmodel',
            index=models.Index(fields=['product_id'], name='order_order_product_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitemmodel',
            index=models.Index(fields=['variant_id'], name='order_order_variant_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitemmodel',
            index=models.Index(fields=['sku'], name='order_order_sku_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['order_number'], name='order_order_order_num_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['user_id'], name='order_order_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['status'], name='order_order_status_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['payment_status'], name='order_order_payment_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['fulfillment_status'], name='order_order_fulfill_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['created_at'], name='order_order_created_2_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['placed_at'], name='order_order_placed_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['user_id', 'created_at'], name='order_order_user_cr_idx'),
        ),
        migrations.AddIndex(
            model_name='ordermodel',
            index=models.Index(fields=['status', 'created_at'], name='order_order_stat_cr_idx'),
        ),
    ]
