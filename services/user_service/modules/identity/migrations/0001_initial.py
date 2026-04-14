"""
Initial migration for Identity module models.
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
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(db_index=True, max_length=254, unique=True)),
                ('full_name', models.CharField(max_length=255)),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('avatar_url', models.URLField(blank=True, null=True)),
                ('role', models.CharField(choices=[('admin', 'ADMIN'), ('staff', 'STAFF'), ('customer', 'CUSTOMER')], db_index=True, default='customer', max_length=20)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_superuser', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'db_table': 'identity_user',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('receiver_name', models.CharField(max_length=255)),
                ('phone_number', models.CharField(max_length=20)),
                ('line1', models.CharField(help_text='Street address (required)', max_length=255)),
                ('line2', models.CharField(blank=True, help_text='Apartment, suite, etc.', max_length=255, null=True)),
                ('ward', models.CharField(blank=True, help_text='Ward/Commune', max_length=100, null=True)),
                ('district', models.CharField(max_length=100)),
                ('city', models.CharField(max_length=100)),
                ('country', models.CharField(default='Vietnam', max_length=100)),
                ('postal_code', models.CharField(blank=True, max_length=20, null=True)),
                ('address_type', models.CharField(choices=[('home', 'HOME'), ('office', 'OFFICE'), ('other', 'OTHER')], default='home', max_length=20)),
                ('is_default', models.BooleanField(db_index=True, default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to='identity.user')),
            ],
            options={
                'db_table': 'identity_address',
                'ordering': ['-is_default', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='identity_use_email_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['role'], name='identity_use_role_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['is_active'], name='identity_use_is_act_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['created_at'], name='identity_use_creat_idx'),
        ),
        migrations.AddIndex(
            model_name='address',
            index=models.Index(fields=['user', 'is_default'], name='identity_add_user_id_is_def_idx'),
        ),
        migrations.AddConstraint(
            model_name='address',
            constraint=models.UniqueConstraint(condition=models.Q(('is_default', True)), fields=('user', 'is_default'), name='unique_default_address_per_user'),
        ),
    ]
