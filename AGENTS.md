# TechShop Agent Instructions

## First Read
- Read this file first for every task in this repository.
- Treat the root [README.md](/home/WORK/lamnh/others/TechShop/README.md) as the primary project overview.
- When working inside a specific service, read that service's local `README.md` before editing code.

## Repo Context
- This repository is a microservices e-commerce platform.
- `frontend/`: Next.js storefront and demo UI
- `gateway/`: Nginx routing layer
- `services/`: Django-based backend services
- `shared/`: shared scripts and project documentation

## Working Rules
- Prefer the current codebase over optimistic claims in old docs when there is a conflict.
- Keep documentation accurate to the actual repository state.
- Do not describe placeholder or mock logic as production-complete.
- Preserve the microservice boundaries; avoid introducing cross-service coupling through shared databases or direct model imports across services.
- Prefer small, local changes over broad refactors unless explicitly requested.

## Documentation Rules
- Update docs when code changes alter architecture, setup, ports, APIs, or service responsibilities.
- Keep the root README overview-oriented around project purpose, architecture, service map, setup flow, and where to read next.
- Put service-specific implementation detail in each service README, not in the root README unless it is essential for onboarding.

## Implementation Expectations
- For backend changes, verify the owning service boundary and environment variables before editing.
- For frontend changes, route API traffic through the gateway conventions already used by the project.
- For AI-related work, distinguish clearly between real model inference, mock providers, retrieval over stored documents, and true vector or embedding-based retrieval.

## Safety
- Never overwrite user changes without understanding them first.
- Avoid destructive git commands unless explicitly requested.
