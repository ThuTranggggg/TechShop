"""
Payment Module Tests

Comprehensive test suite for payment services.
"""

import pytest
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, patch

from ..application.services import (
    CreatePaymentService,
    GetPaymentDetailService,
    GetPaymentByReferenceService,
    GetPaymentStatusService,
    HandlePaymentCallbackService,
    CancelPaymentService,
    ExpirePaymentService,
)
from ..application.dtos import CreatePaymentRequestDTO
from ..domain import (
    PaymentStatus,
    PaymentProvider,
    PaymentMethod,
)


@pytest.fixture
def payment_id():
    return str(uuid4())


@pytest.fixture
def order_id():
    return str(uuid4())


@pytest.fixture
def user_id():
    return str(uuid4())


@pytest.fixture
def create_payment_request(order_id, user_id):
    return CreatePaymentRequestDTO(
        order_id=order_id,
        order_number="ORD-001",
        user_id=user_id,
        amount=Decimal("100.50"),
        currency="USD",
        provider="stripe",
        method="card",
        description="Test payment",
        return_url="https://example.com/return",
        cancel_url="https://example.com/cancel",
        success_url="https://example.com/success",
    )


class TestCreatePaymentService:
    """Test create payment use case"""

    def test_create_payment_success(self, create_payment_request):
        """Test successful payment creation"""
        service = CreatePaymentService()

        # Mock the dependencies
        with patch.object(
            service.payment_repo, "get_by_order", return_value=None
        ), patch.object(
            service.payment_repo, "save"
        ) as mock_save, patch.object(
            service.provider_factory.get_provider, return_value=Mock()
        ) as mock_provider:

            # Setup provider mock
            provider_instance = Mock()
            mock_provider.return_value = provider_instance
            
            provider_response_mock = Mock()
            provider_response_mock.success = True
            provider_response_mock.provider_id = "ch_1234567890"
            provider_response_mock.checkout_url = "https://stripe.com/checkout"
            provider_response_mock.client_secret = None
            provider_response_mock.raw_response = {}
            provider_instance.create_payment.return_value = provider_response_mock

            # Setup payment repo mock
            payment_mock = Mock()
            payment_mock.id = uuid4()
            mock_save.return_value = payment_mock

            # Execute
            success, error, payment_dto = service.execute(create_payment_request)

            # Assert
            assert success
            assert error is None
            assert payment_dto is not None
            mock_save.assert_called_once()

    def test_create_payment_validation_error(self, create_payment_request):
        """Test payment creation with validation error"""
        # Create invalid request
        invalid_request = CreatePaymentRequestDTO(
            order_id="",  # Empty order_id
            order_number="ORD-001",
            user_id=str(uuid4()),
            amount=Decimal("100.50"),
            currency="USD",
            provider="stripe",
            method="card",
        )

        service = CreatePaymentService()
        success, error, payment_dto = service.execute(invalid_request)

        # Assert
        assert not success
        assert error is not None
        assert payment_dto is None

    def test_create_payment_existing_active(self, create_payment_request):
        """Test payment creation when active payment exists"""
        service = CreatePaymentService()

        # Mock existing payment
        existing_payment_mock = Mock()
        existing_payment_mock.is_active.return_value = True

        with patch.object(
            service.payment_repo,
            "get_by_order",
            return_value=existing_payment_mock,
        ):
            success, error, payment_dto = service.execute(create_payment_request)

            # Assert
            assert not success
            assert "already has an active payment" in error


class TestGetPaymentDetailService:
    """Test get payment detail use case"""

    def test_get_payment_detail_success(self, payment_id):
        """Test successful payment retrieval"""
        service = GetPaymentDetailService()

        payment_mock = Mock()
        payment_mock.id = uuid4()

        with patch.object(
            service.payment_repo, "get_by_id", return_value=payment_mock
        ):
            result = service.execute(payment_id)

            # Assert
            assert result is not None
            service.payment_repo.get_by_id.assert_called_once()

    def test_get_payment_detail_not_found(self):
        """Test payment not found"""
        service = GetPaymentDetailService()

        with patch.object(
            service.payment_repo, "get_by_id", return_value=None
        ):
            result = service.execute(str(uuid4()))

            # Assert
            assert result is None


class TestHandlePaymentCallbackService:
    """Test handle payment callback use case"""

    def test_handle_callback_success(self, payment_id):
        """Test successful callback processing"""
        service = HandlePaymentCallbackService()

        # Mock payment
        payment_mock = Mock()
        payment_mock.id = uuid4()
        payment_mock.is_terminal.return_value = False
        payment_mock.is_cancelled.return_value = False
        payment_mock.provider_reference = None
        payment_mock.order = Mock()
        payment_mock.order.order_id = uuid4()

        # Mock callback
        callback_mock = Mock()
        callback_mock.payment_reference = "ref_123"
        callback_mock.status = "succeeded"

        with patch.object(
            service.payment_repo,
            "get_by_reference",
            return_value=payment_mock,
        ), patch.object(
            service.payment_repo, "save", return_value=payment_mock
        ), patch.object(
            service.provider_factory.get_provider, return_value=Mock()
        ) as mock_provider, patch.object(
            service.order_client, "notify_payment_success", return_value=True
        ):
            provider_instance = Mock()
            mock_provider.return_value = provider_instance
            provider_instance.parse_callback.return_value = callback_mock

            success, error = service.execute("stripe", {"raw": "payload"})

            assert success

    def test_handle_callback_payment_not_found(self):
        """Test callback with unknown payment"""
        service = HandlePaymentCallbackService()

        callback_mock = Mock()
        callback_mock.payment_reference = "ref_unknown"

        with patch.object(
            service.payment_repo, "get_by_reference", return_value=None
        ), patch.object(
            service.provider_factory.get_provider, return_value=Mock()
        ) as mock_provider:
            provider_instance = Mock()
            mock_provider.return_value = provider_instance
            provider_instance.parse_callback.return_value = callback_mock

            success, error = service.execute("stripe", {"raw": "payload"})

            assert not success
            assert "Payment not found" in error


class TestCancelPaymentService:
    """Test cancel payment use case"""

    def test_cancel_payment_success(self):
        """Test successful payment cancellation"""
        service = CancelPaymentService()

        payment_mock = Mock()
        payment_mock.id = uuid4()
        payment_mock.can_retry.return_value = True
        payment_mock.is_terminal.return_value = False
        payment_mock.is_cancelled.return_value = False
        ref_mock = Mock()
        ref_mock.provider_id = "ch_1234567890"
        payment_mock.provider_reference = ref_mock
        payment_mock.provider = Mock()
        payment_mock.provider.value = "stripe"

        with patch.object(
            service.payment_repo,
            "get_by_reference",
            return_value=payment_mock,
        ), patch.object(
            service.payment_repo, "save", return_value=payment_mock
        ), patch.object(
            service.provider_factory.get_provider, return_value=Mock()
        ) as mock_provider:
            provider_instance = Mock()
            mock_provider.return_value = provider_instance
            provider_response_mock = Mock()
            provider_response_mock.success = True
            provider_instance.cancel_payment.return_value = provider_response_mock

            success, error, payment_dto = service.execute("ref_123", "User requested")

            assert success
            assert error is None

    def test_cancel_payment_already_cancelled(self):
        """Test cancelling already cancelled payment"""
        service = CancelPaymentService()

        payment_mock = Mock()
        payment_mock.is_cancelled.return_value = True

        with patch.object(
            service.payment_repo, "get_by_reference", return_value=payment_mock
        ):
            success, error, payment_dto = service.execute("ref_123")

            assert success  # Idempotent


class TestExpirePaymentService:
    """Test expire payment use case"""

    def test_expire_payment_success(self):
        """Test successful payment expiration"""
        service = ExpirePaymentService()

        payment_mock = Mock()
        payment_mock.id = uuid4()
        payment_mock.is_terminal.return_value = False

        with patch.object(
            service.payment_repo,
            "get_by_reference",
            return_value=payment_mock,
        ), patch.object(
            service.payment_repo, "save", return_value=payment_mock
        ):
            success, error = service.execute("ref_123")

            assert success
            assert error is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
