"""
Payment Service Clients

HTTP clients for inter-service communication.
"""

from .order_client import OrderServiceClient

__all__ = ['OrderServiceClient']
