"""
Initial migration for payment_service

Creates Payment and PaymentTransaction models.
"""

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('payment_reference', models.CharField(db_index=True, help_text='Unique payment reference: PAY-YYYYMMDD-XXXXXX', max_length=50, unique=True)),
                ('order_id', models.UUIDField(db_index=True, help_text='Order ID from order_service')),
                ('order_number', models.CharField(blank=True, db_index=True, help_text='Order number snapshot', max_length=50, null=True)),
                ('user_id', models.UUIDField(blank=True, db_index=True, help_text='User ID from user_service', null=True)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Payment amount', max_digits=12)),
                ('currency', models.CharField(choices=[('VND', 'VND'), ('USD', 'USD'), ('EUR', 'EUR')], default='VND', max_length=3)),
                ('provider', models.CharField(choices=[('mock', 'MOCK'), ('vnpay', 'VNPAY'), ('momo', 'MOMO'), ('stripe', 'STRIPE'), ('paypal', 'PAYPAL')], db_index=True, default='mock', max_length=20)),
                ('method', models.CharField(choices=[('card', 'CARD'), ('bank_transfer', 'BANK_TRANSFER'), ('wallet', 'WALLET'), ('cod', 'CASH_ON_DELIVERY'), ('qr_code', 'QR_CODE'), ('mock', 'MOCK')], default='mock', max_length=50)),
                ('status', models.CharField(choices=[('created', 'CREATED'), ('pending', 'PENDING'), ('requires_action', 'REQUIRES_ACTION'), ('paid', 'PAID'), ('failed', 'FAILED'), ('cancelled', 'CANCELLED'), ('expired', 'EXPIRED'), ('refunded', 'REFUNDED')], db_index=True, default='created', max_length=20)),
                ('provider_payment_id', models.CharField(blank=True, db_index=True, help_text='ID from external payment provider', max_length=100, null=True, unique=True)),
                ('checkout_url', models.TextField(blank=True, help_text='URL for user to complete payment', null=True)),
                ('client_secret', models.TextField(blank=True, help_text='Client secret for frontend payment flow', null=True)),
                ('description', models.TextField(blank=True, help_text='Payment description', null=True)),
                ('failure_reason', models.TextField(blank=True, help_text='Reason for payment failure', null=True)),
                ('return_url', models.URLField(blank=True, help_text='URL to return after payment', null=True)),
                ('cancel_url', models.URLField(blank=True, help_text='URL if payment is cancelled', null=True)),
                ('success_url', models.URLField(blank=True, help_text='URL on payment success', null=True)),
                ('requested_at', models.DateTimeField(default=django.utils.timezone.now, help_text='When payment was initiated')),
                ('completed_at', models.DateTimeField(blank=True, help_text='When payment was completed', null=True)),
                ('failed_at', models.DateTimeField(blank=True, help_text='When payment failed', null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, help_text='When payment was cancelled', null=True)),
                ('expired_at', models.DateTimeField(blank=True, help_text='When payment expired', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata')),
            ],
            options={
                'verbose_name': 'Payment',
                'verbose_name_plural': 'Payments',
                'db_table': 'payment_paymentmodel',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentTransactionModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('transaction_reference', models.CharField(db_index=True, help_text='Unique transaction reference: TRANS-YYYYMMDD-XXXXXX', max_length=50, unique=True)),
                ('transaction_type', models.CharField(choices=[('create', 'CREATE'), ('authorize', 'AUTHORIZE'), ('capture', 'CAPTURE'), ('callback', 'CALLBACK'), ('success', 'SUCCESS'), ('fail', 'FAIL'), ('cancel', 'CANCEL'), ('expire', 'EXPIRE'), ('refund', 'REFUND')], db_index=True, max_length=20)),
                ('status', models.CharField(choices=[('pending', 'PENDING'), ('success', 'SUCCESS'), ('failed', 'FAILED'), ('cancelled', 'CANCELLED')], db_index=True, default='pending', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Transaction amount', max_digits=12)),
                ('currency', models.CharField(choices=[('VND', 'VND'), ('USD', 'USD'), ('EUR', 'EUR')], default='VND', max_length=3)),
                ('provider_transaction_id', models.CharField(blank=True, db_index=True, help_text='ID from payment provider', max_length=100, null=True)),
                ('request_payload', models.JSONField(blank=True, default=dict, help_text='Request payload sent to provider')),
                ('response_payload', models.JSONField(blank=True, default=dict, help_text='Response from provider')),
                ('callback_payload', models.JSONField(blank=True, default=dict, help_text='Callback payload from provider webhook')),
                ('error_message', models.TextField(blank=True, help_text='Error message if transaction failed', null=True)),
                ('error_code', models.CharField(blank=True, help_text='Error code from provider', max_length=50, null=True)),
                ('idempotency_key', models.CharField(blank=True, db_index=True, help_text='Idempotency key for deduplication', max_length=100, null=True)),
                ('raw_provider_status', models.CharField(blank=True, help_text='Raw status from provider', max_length=50, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('payment', models.ForeignKey(help_text='Related payment', on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='payment.paymentmodel')),
            ],
            options={
                'verbose_name': 'Payment Transaction',
                'verbose_name_plural': 'Payment Transactions',
                'db_table': 'payment_paymenttransactionmodel',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='paymentmodel',
            index=models.Index(fields=['payment_reference'], name='payment_ref_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentmodel',
            index=models.Index(fields=['order_id'], name='order_id_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentmodel',
            index=models.Index(fields=['user_id'], name='user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentmodel',
            index=models.Index(fields=['status'], name='status_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentmodel',
            index=models.Index(fields=['provider'], name='provider_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentmodel',
            index=models.Index(fields=['order_id', 'created_at'], name='order_created_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentmodel',
            index=models.Index(fields=['status', 'created_at'], name='status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentmodel',
            index=models.Index(fields=['provider_payment_id'], name='provider_payment_id_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransactionmodel',
            index=models.Index(fields=['transaction_reference'], name='trans_ref_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransactionmodel',
            index=models.Index(fields=['payment_id', 'created_at'], name='payment_created_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransactionmodel',
            index=models.Index(fields=['transaction_type'], name='trans_type_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransactionmodel',
            index=models.Index(fields=['status'], name='trans_status_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransactionmodel',
            index=models.Index(fields=['provider_transaction_id'], name='provider_trans_id_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransactionmodel',
            index=models.Index(fields=['idempotency_key'], name='idempotency_key_idx'),
        ),
    ]
