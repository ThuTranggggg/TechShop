"""
Shipping Service Module

Complete shipment and delivery lifecycle management.

Architecture: Domain-Driven Design (DDD)
- Domain Layer: Business logic, entities, repositories, value objects
- Infrastructure Layer: ORM models, external clients, provider abstraction
- Application Layer: Use cases, DTOs, orchestration
- Presentation Layer: REST API views, serializers
"""

default_app_config = "modules.shipping.apps.ShippingConfig"
