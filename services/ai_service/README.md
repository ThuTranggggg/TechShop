# AI Service

AI Service provides behavioral tracking, personalized recommendations, knowledge retrieval, Neo4j graph sync, and chat endpoints for TechShop.

## Capabilities

- Track behavioral events such as `search`, `product_view`, `product_click`, `add_to_cart`, and `chat_query`
- Build user preference profiles from event history
- Score products with a hybrid recommendation flow
- Retrieve knowledge documents for RAG answers
- Sync behavior and products into Neo4j for KB_Graph usage
- Expose a dedicated chat UI and chat API for the storefront

## Architecture

- `domain/` owns entities, value objects, repository contracts, and service contracts
- `application/` owns use cases such as tracking, recommendation, chat, and data ingestion
- `infrastructure/` owns ORM models, repositories, provider clients, graph sync, and import helpers
- `presentation/` owns serializers, views, and URLs

## Configuration

Important environment variables from `services/ai_service/config/settings.py`:

- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `AI_PROVIDER`, `AI_API_KEY`
- `AI_CHAT_COMPLETIONS_URL`, `AI_EMBEDDINGS_URL`
- `AI_CHAT_MODEL`, `AI_EMBEDDING_MODEL`

## Useful Commands

- `python manage.py seed_ai_data`
- `python manage.py load_ai_dataset`
- `python manage.py build_rag_index`
- `python manage.py rebuild_knowledge_graph`
- `python manage.py train_lstm_recommender`

## Assignment Artefacts

The weekly assignment pipeline is available at:

```bash
python shared/scripts/ai_assignment_pipeline.py all
```

Generated artefacts are written to `shared/generated/ai_assignment/` and documented in `shared/docs/AI_ASSIGNMENT_WORKFLOW.md`.

## API Entry Points

- Behavioral tracking: `/api/v1/ai/events/track/`
- Recommendations: `/api/v1/ai/recommendations/`
- Chat sessions: `/api/v1/ai/chat/sessions/`
- Chat ask endpoint: `/api/v1/ai/chat/ask/`
- Preference summary: `/api/v1/ai/users/<user_id>/preferences/`

## Notes

- Neo4j is used for graph sync and KB_Graph imports.
- The storefront has a dedicated AI chat page and widget; it does not use the default ChatGPT UI.
- For report generation, use the generated files in `shared/generated/ai_assignment/` as the source of truth.
