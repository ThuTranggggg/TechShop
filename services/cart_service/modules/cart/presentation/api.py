"""
API Views for Cart service.

REST API endpoints for cart operations.
"""
import logging
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common.responses import success_response, error_response
from ..application.services import get_cart_application_service
from ..application.dtos import (
    AddItemToCartDTO,
    UpdateCartItemQuantityDTO,
    RemoveCartItemDTO,
    ClearCartDTO,
    ValidateCartDTO,
    RefreshCartDTO,
)
from .serializers import (
    CartSerializer,
    AddItemToCartSerializer,
    UpdateCartItemSerializer,
    IncreaseDecreaseQuantitySerializer,
    CartValidationResultSerializer,
    CheckoutPreviewSerializer,
    CartSummarySerializer,
)
from .permissions import IsCartOwner, IsInternal, IsAdminOrStaff, IsAuthenticatedCustomer

logger = logging.getLogger(__name__)


class CustomerCartViewSet(viewsets.ViewSet):
    """
    ViewSet for customer-facing cart APIs.
    
    Endpoints for users to manage their shopping carts.
    """
    
    permission_classes = [IsAuthenticatedCustomer]
    authentication_classes = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.application_service = get_cart_application_service()
    
    def _get_user_id(self, request):
        """Extract user ID from request."""
        return request.META.get("HTTP_X_USER_ID")
    
    @action(detail=False, methods=["get"], url_path="current", url_name="get-current-cart")
    def get_current_cart(self, request):
        """
        GET /api/v1/cart/current/
        
        Get current active cart for user.
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            cart_dto = self.application_service.get_current_cart(user_id)
            serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Current cart retrieved",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error getting current cart: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=["post"], url_path="items", url_name="add-item")
    def add_item(self, request):
        """
        POST /api/v1/cart/items/
        
        Add item to cart.
        
        Request body:
        {
            "product_id": "...",
            "variant_id": "...",  # optional
            "quantity": 2
        }
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            serializer = AddItemToCartSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("Validation failed", errors=serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)
            
            dto = AddItemToCartDTO(
                user_id=user_id,
                product_id=serializer.validated_data["product_id"],
                variant_id=serializer.validated_data.get("variant_id"),
                quantity=serializer.validated_data["quantity"],
            )
            
            cart_dto = self.application_service.add_item_to_cart(dto)
            response_serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Item added to cart",
                data=response_serializer.data,
                http_status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error adding item to cart: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["patch"], url_path="items/(?P<item_id>[^/.]+)/quantity", url_name="update-item-quantity")
    def update_item_quantity(self, request, item_id=None):
        """
        PATCH /api/v1/cart/items/{item_id}/quantity/
        
        Update quantity of a cart item.
        
        Request body:
        {
            "new_quantity": 5
        }
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            serializer = UpdateCartItemSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("Validation failed", errors=serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)
            
            dto = UpdateCartItemQuantityDTO(
                user_id=user_id,
                item_id=item_id,
                new_quantity=serializer.validated_data["new_quantity"],
            )
            
            cart_dto = self.application_service.update_item_quantity(dto)
            response_serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Item quantity updated",
                data=response_serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating item quantity: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["delete"], url_path="items/(?P<item_id>[^/.]+)", url_name="remove-item")
    def remove_item(self, request, item_id=None):
        """
        DELETE /api/v1/cart/items/{item_id}/
        
        Remove item from cart.
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            dto = RemoveCartItemDTO(user_id=user_id, item_id=item_id)
            cart_dto = self.application_service.remove_cart_item(dto)
            response_serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Item removed from cart",
                data=response_serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error removing item: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="items/(?P<item_id>[^/.]+)/increase", url_name="increase-quantity")
    def increase_quantity(self, request, item_id=None):
        """
        POST /api/v1/cart/items/{item_id}/increase/
        
        Increase item quantity.
        
        Request body (optional):
        {
            "amount": 1
        }
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            serializer = IncreaseDecreaseQuantitySerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("Validation failed", errors=serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)
            
            amount = serializer.validated_data.get("amount", 1)
            
            # Get current item and increase
            item = self.application_service.item_repository.get_by_id(item_id)
            if not item:
                return error_response("Item not found", http_status=status.HTTP_404_NOT_FOUND)
            
            new_quantity = item.quantity.value + amount
            dto = UpdateCartItemQuantityDTO(
                user_id=user_id,
                item_id=item_id,
                new_quantity=new_quantity,
            )
            
            cart_dto = self.application_service.update_item_quantity(dto)
            response_serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Item quantity increased",
                data=response_serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error increasing quantity: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="items/(?P<item_id>[^/.]+)/decrease", url_name="decrease-quantity")
    def decrease_quantity(self, request, item_id=None):
        """
        POST /api/v1/cart/items/{item_id}/decrease/
        
        Decrease item quantity.
        
        Request body (optional):
        {
            "amount": 1
        }
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            serializer = IncreaseDecreaseQuantitySerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("Validation failed", errors=serializer.errors, http_status=status.HTTP_400_BAD_REQUEST)
            
            amount = serializer.validated_data.get("amount", 1)
            
            # Get current item and decrease
            item = self.application_service.item_repository.get_by_id(item_id)
            if not item:
                return error_response("Item not found", http_status=status.HTTP_404_NOT_FOUND)
            
            new_quantity = item.quantity.value - amount
            if new_quantity <= 0:
                return error_response("Quantity cannot be less than 1", http_status=status.HTTP_400_BAD_REQUEST)
            
            dto = UpdateCartItemQuantityDTO(
                user_id=user_id,
                item_id=item_id,
                new_quantity=new_quantity,
            )
            
            cart_dto = self.application_service.update_item_quantity(dto)
            response_serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Item quantity decreased",
                data=response_serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error decreasing quantity: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="refresh", url_name="refresh-cart")
    def refresh_cart(self, request):
        """
        POST /api/v1/cart/refresh/
        
        Refresh cart snapshots and availability.
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            dto = RefreshCartDTO(user_id=user_id)
            cart_dto = self.application_service.refresh_cart(dto)
            serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Cart refreshed",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error refreshing cart: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="validate", url_name="validate-cart")
    def validate_cart(self, request):
        """
        POST /api/v1/cart/validate/
        
        Validate cart and check all items are available.
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            dto = ValidateCartDTO(user_id=user_id)
            validation_result = self.application_service.validate_cart(dto)
            serializer = CartValidationResultSerializer(validation_result.to_dict())
            
            return success_response(
                message="Cart validation completed",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error validating cart: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="clear", url_name="clear-cart")
    def clear_cart(self, request):
        """
        POST /api/v1/cart/clear/
        
        Remove all items from cart.
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            dto = ClearCartDTO(user_id=user_id)
            cart_dto = self.application_service.clear_cart(dto)
            serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Cart cleared",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["get"], url_path="summary", url_name="cart-summary")
    def get_summary(self, request):
        """
        GET /api/v1/cart/summary/
        
        Get cart summary (counts and totals only).
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            cart_dto = self.application_service.get_current_cart(user_id)
            
            summary = {
                "item_count": cart_dto.item_count,
                "total_quantity": cart_dto.total_quantity,
                "subtotal_amount": cart_dto.subtotal_amount,
                "currency": cart_dto.currency,
            }
            
            serializer = CartSummarySerializer(summary)
            
            return success_response(
                message="Cart summary retrieved",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error getting cart summary: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="checkout-preview", url_name="checkout-preview")
    def checkout_preview(self, request):
        """
        POST /api/v1/cart/checkout-preview/
        
        Build checkout preview with validation.
        """
        try:
            user_id = self._get_user_id(request)
            if not user_id:
                return error_response("User ID not found", http_status=status.HTTP_401_UNAUTHORIZED)
            
            dto = ValidateCartDTO(user_id=user_id)
            preview = self.application_service.checkout_preview(dto)
            serializer = CheckoutPreviewSerializer(preview)
            
            return success_response(
                message="Checkout preview prepared",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error preparing checkout preview: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InternalCartViewSet(viewsets.ViewSet):
    """
    ViewSet for internal (service-to-service) cart APIs.
    
    Used by order_service and other internal services.
    """
    
    permission_classes = [IsInternal]
    authentication_classes = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.application_service = get_cart_application_service()
    
    @action(detail=False, methods=["get"], url_path="users/(?P<user_id>[^/.]+)/active", url_name="get-active-cart")
    def get_active_cart(self, request, user_id=None):
        """
        GET /api/v1/internal/carts/users/{user_id}/active/
        
        Get active cart for user (internal).
        """
        try:
            cart_dto = self.application_service.get_or_create_active_cart(user_id)
            serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Active cart retrieved",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error getting active cart: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["get"], url_path="(?P<cart_id>[^/.]+)", url_name="get-cart")
    def get_cart(self, request, cart_id=None):
        """
        GET /api/v1/internal/carts/{cart_id}/
        
        Get cart by ID (internal).
        """
        try:
            cart = self.application_service.cart_repository.get_by_id(cart_id)
            if not cart:
                return error_response("Cart not found", http_status=status.HTTP_404_NOT_FOUND)
            
            cart_dto = self.application_service._cart_to_response_dto(cart)
            serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Cart retrieved",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error getting cart: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="(?P<cart_id>[^/.]+)/mark-checked-out", url_name="mark-checked-out")
    def mark_checked_out(self, request, cart_id=None):
        """
        POST /api/v1/internal/carts/{cart_id}/mark-checked-out/
        
        Mark cart as checked out (internal, called by order_service).
        """
        try:
            cart_dto = self.application_service.mark_checked_out(cart_id)
            serializer = CartSerializer(cart_dto.to_dict())
            
            return success_response(
                message="Cart marked as checked out",
                data=serializer.data,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error marking cart as checked out: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="(?P<cart_id>[^/.]+)/checkout-payload", url_name="checkout-payload")
    def get_checkout_payload(self, request, cart_id=None):
        """
        POST /api/v1/internal/carts/{cart_id}/checkout-payload/
        
        Get checkout payload for cart (internal).
        """
        try:
            cart = self.application_service.cart_repository.get_by_id(cart_id)
            if not cart:
                return error_response("Cart not found", http_status=status.HTTP_404_NOT_FOUND)
            
            # Validate cart first
            validation = self.application_service.validate_cart(ValidateCartDTO(user_id=str(cart.user_id)))
            
            if not validation.is_valid:
                return error_response(
                    "Cart has validation issues",
                    errors=validation.to_dict()["issues"],
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            
            # Build payload
            checkout_payload = {
                "cart_id": str(cart.id),
                "user_id": str(cart.user_id),
                "currency": cart.currency,
                "subtotal_amount": str(cart.subtotal_amount),
                "items": [
                    {
                        "cart_item_id": str(item.id),
                        "product_id": item.product_reference.product_id,
                        "variant_id": item.product_reference.variant_id,
                        "quantity": item.quantity.value,
                        "unit_price": str(item.price_snapshot.amount),
                        "line_total": str(float(item.calculate_line_total().amount)),
                    }
                    for item in cart.items
                ],
            }
            
            return success_response(
                message="Checkout payload prepared",
                data=checkout_payload,
                http_status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return error_response(str(e), http_status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error getting checkout payload: {e}")
            return error_response(f"Error: {str(e)}", http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
