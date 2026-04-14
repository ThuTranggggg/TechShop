"""
Order module - Main bounded context for order management.

This module implements the Order service responsible for:
- Order creation and management
- Order lifecycle and state machine
- Stock reservation orchestration
- Payment coordination
- Order history and reporting
"""

default_app_config = "modules.order.apps.OrderConfig"
