"""
Initial migration for AI service models.
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
            name='BehavioralEventModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(choices=[('search', 'search'), ('product_view', 'product_view'), ('product_click', 'product_click'), ('add_to_cart', 'add_to_cart'), ('remove_from_cart', 'remove_from_cart'), ('checkout_started', 'checkout_started'), ('order_created', 'order_created'), ('payment_success', 'payment_success'), ('chat_query', 'chat_query')], db_index=True, max_length=30)),
                ('user_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('session_id', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('product_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('variant_id', models.UUIDField(blank=True, null=True)),
                ('brand_name', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('category_name', models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ('price_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('price_range', models.CharField(blank=True, choices=[('under_1m', 'under_1m'), ('from_1m_to_3m', 'from_1m_to_3m'), ('from_3m_to_5m', 'from_3m_to_5m'), ('from_5m_to_10m', 'from_5m_to_10m'), ('from_10m_to_20m', 'from_10m_to_20m'), ('above_20m', 'above_20m')], db_index=True, max_length=20, null=True)),
                ('keyword', models.CharField(blank=True, max_length=255, null=True)),
                ('source_service', models.CharField(blank=True, max_length=50, null=True)),
                ('occurred_at', models.DateTimeField(db_index=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'verbose_name': 'Behavioral Event',
                'verbose_name_plural': 'Behavioral Events',
                'db_table': 'behavioral_event',
                'ordering': ['-occurred_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatSessionModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('session_title', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                'verbose_name': 'Chat Session',
                'verbose_name_plural': 'Chat Sessions',
                'db_table': 'chat_session',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='KnowledgeDocumentModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('document_type', models.CharField(choices=[('faq', 'faq'), ('return_policy', 'return_policy'), ('payment_policy', 'payment_policy'), ('shipping_policy', 'shipping_policy'), ('product_guide', 'product_guide'), ('support_article', 'support_article')], db_index=True, max_length=30)),
                ('title', models.CharField(max_length=255)),
                ('slug', models.SlugField(blank=True, max_length=255, null=True, unique=True)),
                ('source', models.CharField(default='internal', max_length=100)),
                ('content', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Knowledge Document',
                'verbose_name_plural': 'Knowledge Documents',
                'db_table': 'knowledge_document',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserPreferenceProfileModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.UUIDField(db_index=True, unique=True)),
                ('preferred_brands', models.JSONField(blank=True, default=list, help_text='List of brand preferences with scores')),
                ('preferred_categories', models.JSONField(blank=True, default=list, help_text='List of category preferences with scores')),
                ('preferred_price_ranges', models.JSONField(blank=True, default=list, help_text='List of price range preferences with scores')),
                ('recent_keywords', models.JSONField(blank=True, default=list, help_text='Recent search keywords')),
                ('preference_score_summary', models.JSONField(blank=True, default=dict, help_text='Summary of various preference scores')),
                ('purchase_intent_score', models.FloatField(db_index=True, default=0.0, help_text='Score indicating purchase likelihood (0-100)')),
                ('last_interaction_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                'verbose_name': 'User Preference Profile',
                'verbose_name_plural': 'User Preference Profiles',
                'db_table': 'user_preference_profile',
            },
        ),
        migrations.CreateModel(
            name='RecommendationCacheModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user_id', models.UUIDField(blank=True, db_index=True, null=True)),
                ('recommendation_type', models.CharField(db_index=True, help_text='personalized, fallback, related, trending', max_length=50)),
                ('result_payload', models.JSONField()),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, db_index=True, null=True)),
            ],
            options={
                'verbose_name': 'Recommendation Cache',
                'verbose_name_plural': 'Recommendation Caches',
                'db_table': 'recommendation_cache',
                'ordering': ['-generated_at'],
            },
        ),
        migrations.CreateModel(
            name='KnowledgeChunkModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('chunk_index', models.IntegerField()),
                ('content', models.TextField()),
                ('embedding_ref', models.CharField(blank=True, help_text='Reference to external embedding or vector store', max_length=255, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='ai.knowledgedocumentmodel')),
            ],
            options={
                'verbose_name': 'Knowledge Chunk',
                'verbose_name_plural': 'Knowledge Chunks',
                'db_table': 'knowledge_chunk',
                'unique_together': {('document', 'chunk_index')},
            },
        ),
        migrations.CreateModel(
            name='ChatMessageModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('user', 'user'), ('assistant', 'assistant'), ('system', 'system')], db_index=True, max_length=20)),
                ('content', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='ai.chatsessionmodel')),
            ],
            options={
                'verbose_name': 'Chat Message',
                'verbose_name_plural': 'Chat Messages',
                'db_table': 'chat_message',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='knowledgechunkmodel',
            index=models.Index(fields=['document_id', 'chunk_index'], name='knowledge_chunk_document_index'),
        ),
        migrations.AddIndex(
            model_name='knowledgedocumentmodel',
            index=models.Index(fields=['document_type', 'is_active'], name='knowledge_document_type_index'),
        ),
        migrations.AddIndex(
            model_name='chatmessagemodel',
            index=models.Index(fields=['session_id', 'role', 'created_at'], name='chat_message_session_role_index'),
        ),
        migrations.AddIndex(
            model_name='chatsessionmodel',
            index=models.Index(fields=['user_id', 'updated_at'], name='chat_session_user_index'),
        ),
        migrations.AddIndex(
            model_name='behavioraleventmodel',
            index=models.Index(fields=['event_type', 'created_at'], name='behavioral_event_type_index'),
        ),
        migrations.AddIndex(
            model_name='behavioraleventmodel',
            index=models.Index(fields=['user_id', 'created_at'], name='behavioral_event_user_index'),
        ),
        migrations.AddIndex(
            model_name='behavioraleventmodel',
            index=models.Index(fields=['product_id'], name='behavioral_event_product_index'),
        ),
        migrations.AddIndex(
            model_name='behavioraleventmodel',
            index=models.Index(fields=['brand_name', 'category_name'], name='behavioral_event_brand_category_index'),
        ),
        migrations.AddIndex(
            model_name='behavioraleventmodel',
            index=models.Index(fields=['price_range'], name='behavioral_event_price_range_index'),
        ),
        migrations.AddIndex(
            model_name='recommendationcachemodel',
            index=models.Index(fields=['user_id', 'recommendation_type'], name='recommendation_cache_user_type_index'),
        ),
        migrations.AddIndex(
            model_name='recommendationcachemodel',
            index=models.Index(fields=['expires_at'], name='recommendation_cache_expires_index'),
        ),
    ]
