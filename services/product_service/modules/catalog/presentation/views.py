"""Presentation layer views for Catalog API."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..application.dtos import ProductQueryDTO
from ..application.services import (
    BrandService,
    CategoryCommandService,
    CategoryQueryService,
    ProductCommandService,
    ProductMediaService,
    ProductQueryService,
    ProductTypeService,
    ProductVariantService,
)
from ..domain.enums import ProductStatus
from ..infrastructure.models import (
    BrandModel,
    CategoryModel,
    ProductMediaModel,
    ProductModel,
    ProductTypeModel,
    ProductVariantModel,
)
from .permissions import InternalServicePermission, IsPublicRead, IsStaffOrAdmin
from .serializers import (
    BrandCreateUpdateSerializer,
    BrandSerializer,
    CategorySerializer,
    CategoryWriteSerializer,
    InternalProductBulkSerializer,
    InternalVariantBulkSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductMediaCreateUpdateSerializer,
    ProductMediaSerializer,
    ProductSnapshotSerializer,
    ProductTypeCreateUpdateSerializer,
    ProductTypeSerializer,
    ProductVariantCreateUpdateSerializer,
    ProductVariantSerializer,
    ProductWriteSerializer,
)


class StandardPagination(PageNumberPagination):
    """Standard pagination for catalog APIs."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LookupByIdOrSlugMixin:
    """Resolve detail resources by UUID or slug from the same route."""

    lookup_field = "lookup"
    lookup_url_kwarg = "lookup"

    def get_lookup_value(self) -> str:
        return self.kwargs.get(self.lookup_url_kwarg)


def _parse_decimal(value: str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise DjangoValidationError("Invalid decimal value") from exc


def _parse_bool(value: str | None) -> bool | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise DjangoValidationError("Invalid boolean value")


def _apply_ordering(queryset, ordering_param: str | None, allowed: list[str], default: list[str]):
    ordering_values = [item.strip() for item in (ordering_param or "").split(",") if item.strip()]
    if not ordering_values:
        return queryset.order_by(*default)

    invalid = [item for item in ordering_values if item.lstrip("-") not in allowed]
    if invalid:
        raise DjangoValidationError(f"Unsupported ordering fields: {', '.join(invalid)}")
    return queryset.order_by(*ordering_values)


def _build_product_filters(request, *, include_status: bool = False) -> ProductQueryDTO:
    query_params = request.query_params
    status_value = query_params.get("status") if include_status else None
    return ProductQueryDTO(
        category_id=query_params.get("category") or query_params.get("category_id"),
        category_slug=query_params.get("category_slug"),
        brand_id=query_params.get("brand"),
        product_type_id=query_params.get("product_type"),
        status=status_value,
        is_active=_parse_bool(query_params.get("is_active")) if include_status else None,
        is_featured=_parse_bool(query_params.get("is_featured")),
        min_price=_parse_decimal(query_params.get("min_price") or query_params.get("base_price__gte")),
        max_price=_parse_decimal(query_params.get("max_price") or query_params.get("base_price__lte")),
        search=query_params.get("search") or query_params.get("q", ""),
    )


def _product_payload_response(product, detail: bool = False):
    serializer_class = ProductDetailSerializer if detail else ProductListSerializer
    return serializer_class(product).data


@extend_schema_view(
    retrieve=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    products=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
)
class CategoryViewSet(LookupByIdOrSlugMixin, viewsets.ReadOnlyModelViewSet):
    """Public category browsing APIs."""

    queryset = CategoryModel.objects.none()
    permission_classes = [IsPublicRead]
    pagination_class = StandardPagination
    serializer_class = CategorySerializer
    ordering_fields = ["name", "sort_order", "created_at", "updated_at"]
    default_ordering = ["sort_order", "name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_service = CategoryQueryService()
        self.product_query_service = ProductQueryService()

    def get_queryset(self):
        queryset = self.query_service.list_categories(include_inactive=False)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(slug__icontains=search)
                | Q(description__icontains=search)
            )
        return _apply_ordering(
            queryset,
            self.request.query_params.get("ordering"),
            self.ordering_fields,
            self.default_ordering,
        )

    def get_object(self):
        lookup = self.get_lookup_value()
        try:
            return self.query_service.get_category(lookup, include_inactive=False)
        except DjangoValidationError as exc:
            raise Http404(str(exc)) from exc

    @action(detail=True, methods=["get"], permission_classes=[IsPublicRead])
    def products(self, request, lookup=None):
        category = self.get_object()
        filters = _build_product_filters(request, include_status=False)
        filters = ProductQueryDTO(
            category_id=str(category.id),
            category_slug=filters.category_slug,
            brand_id=filters.brand_id,
            product_type_id=filters.product_type_id,
            is_featured=filters.is_featured,
            min_price=filters.min_price,
            max_price=filters.max_price,
            search=filters.search,
        )
        queryset = self.product_query_service.list_public_products(filters)
        queryset = _apply_ordering(
            queryset,
            request.query_params.get("ordering"),
            ["name", "base_price", "created_at", "published_at"],
            ["-published_at", "name"],
        )
        page = self.paginate_queryset(queryset)
        serializer = ProductListSerializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    """Public brand browsing - read-only."""

    queryset = BrandModel.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    lookup_field = "id"
    pagination_class = StandardPagination
    permission_classes = [IsPublicRead]


class ProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Public product type browsing - read-only."""

    queryset = ProductTypeModel.objects.filter(is_active=True)
    serializer_class = ProductTypeSerializer
    lookup_field = "id"
    pagination_class = StandardPagination
    permission_classes = [IsPublicRead]


@extend_schema_view(
    retrieve=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    variants=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
)
class PublicProductViewSet(LookupByIdOrSlugMixin, viewsets.ReadOnlyModelViewSet):
    """Public product catalog APIs."""

    queryset = ProductModel.objects.none()
    permission_classes = [IsPublicRead]
    pagination_class = StandardPagination
    ordering_fields = ["name", "base_price", "created_at", "published_at"]
    default_ordering = ["-published_at", "name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_service = ProductQueryService()

    def get_serializer_class(self):
        return ProductDetailSerializer if self.action == "retrieve" else ProductListSerializer

    def get_queryset(self):
        filters = _build_product_filters(self.request, include_status=False)
        queryset = self.query_service.list_public_products(filters)
        return _apply_ordering(
            queryset,
            self.request.query_params.get("ordering"),
            self.ordering_fields,
            self.default_ordering,
        )

    def get_object(self):
        lookup = self.get_lookup_value()
        try:
            return self.query_service.get_product(lookup, public_only=True)
        except DjangoValidationError as exc:
            raise Http404(str(exc)) from exc

    @action(detail=False, methods=["get"], permission_classes=[IsPublicRead])
    def search(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = ProductListSerializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[IsPublicRead])
    def variants(self, request, lookup=None):
        product = self.get_object()
        variants = product.variants.filter(is_active=True)
        serializer = ProductVariantSerializer(variants, many=True)
        return Response(serializer.data)


@extend_schema_view(
    retrieve=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    update=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    partial_update=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    destroy=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    products=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
)
class AdminCategoryViewSet(LookupByIdOrSlugMixin, viewsets.ModelViewSet):
    """Admin category management."""

    queryset = CategoryModel.objects.none()
    permission_classes = [IsStaffOrAdmin]
    pagination_class = StandardPagination
    serializer_class = CategorySerializer
    ordering_fields = ["name", "sort_order", "created_at", "updated_at"]
    default_ordering = ["sort_order", "name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_service = CategoryQueryService()
        self.command_service = CategoryCommandService()
        self.product_query_service = ProductQueryService()

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return CategoryWriteSerializer
        return CategorySerializer

    def get_queryset(self):
        queryset = self.query_service.list_categories(include_inactive=True)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(slug__icontains=search)
                | Q(description__icontains=search)
            )
        return _apply_ordering(
            queryset,
            self.request.query_params.get("ordering"),
            self.ordering_fields,
            self.default_ordering,
        )

    def get_object(self):
        lookup = self.get_lookup_value()
        try:
            return self.query_service.get_category(lookup, include_inactive=True)
        except DjangoValidationError as exc:
            raise Http404(str(exc)) from exc

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = self.command_service.create_category(serializer.to_dto())
        return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        category = self.command_service.update_category(self.get_lookup_value(), serializer.to_dto())
        return Response(CategorySerializer(category).data)

    def destroy(self, request, *args, **kwargs):
        self.command_service.delete_category(self.get_lookup_value())
        return Response({"message": "Category deleted successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], permission_classes=[IsStaffOrAdmin])
    def products(self, request, lookup=None):
        category = self.get_object()
        filters = _build_product_filters(request, include_status=True)
        filters = ProductQueryDTO(
            category_id=str(category.id),
            category_slug=filters.category_slug,
            brand_id=filters.brand_id,
            product_type_id=filters.product_type_id,
            status=filters.status,
            is_active=filters.is_active,
            is_featured=filters.is_featured,
            min_price=filters.min_price,
            max_price=filters.max_price,
            search=filters.search,
        )
        queryset = self.product_query_service.list_admin_products(filters)
        queryset = _apply_ordering(
            queryset,
            request.query_params.get("ordering"),
            ["name", "base_price", "created_at", "published_at"],
            ["-created_at"],
        )
        page = self.paginate_queryset(queryset)
        serializer = ProductListSerializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class AdminBrandViewSet(viewsets.ModelViewSet):
    """Admin brand management."""

    queryset = BrandModel.objects.all()
    lookup_field = "id"
    pagination_class = StandardPagination
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return BrandCreateUpdateSerializer
        return BrandSerializer


class AdminProductTypeViewSet(viewsets.ModelViewSet):
    """Admin product type management."""

    queryset = ProductTypeModel.objects.all()
    lookup_field = "id"
    pagination_class = StandardPagination
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ProductTypeCreateUpdateSerializer
        return ProductTypeSerializer


@extend_schema_view(
    retrieve=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    update=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    partial_update=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    destroy=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    publish=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    unpublish=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    activate=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    deactivate=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    variants=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
    media=extend_schema(parameters=[OpenApiParameter("lookup", str, OpenApiParameter.PATH)]),
)
class AdminProductViewSet(LookupByIdOrSlugMixin, viewsets.ModelViewSet):
    """Admin product management."""

    queryset = ProductModel.objects.none()
    permission_classes = [IsStaffOrAdmin]
    pagination_class = StandardPagination
    ordering_fields = ["name", "base_price", "created_at", "published_at"]
    default_ordering = ["-created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_service = ProductQueryService()
        self.command_service = ProductCommandService()

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ProductWriteSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        filters = _build_product_filters(self.request, include_status=True)
        queryset = self.query_service.list_admin_products(filters)
        return _apply_ordering(
            queryset,
            self.request.query_params.get("ordering"),
            self.ordering_fields,
            self.default_ordering,
        )

    def get_object(self):
        lookup = self.get_lookup_value()
        try:
            return self.query_service.get_product(lookup, public_only=False)
        except DjangoValidationError as exc:
            raise Http404(str(exc)) from exc

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = self.command_service.create_product(serializer.to_dto())
        return Response(ProductDetailSerializer(product).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        product = self.command_service.update_product(self.get_lookup_value(), serializer.to_dto())
        return Response(ProductDetailSerializer(product).data)

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        product.delete()
        return Response({"message": "Product deleted successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffOrAdmin])
    def publish(self, request, lookup=None):
        product = self.get_object()
        ProductCommandService.publish_product(product.id)
        product.refresh_from_db()
        return Response(ProductDetailSerializer(product).data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffOrAdmin])
    def unpublish(self, request, lookup=None):
        product = self.get_object()
        ProductCommandService.unpublish_product(product.id)
        product.refresh_from_db()
        return Response(ProductDetailSerializer(product).data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffOrAdmin])
    def activate(self, request, lookup=None):
        product = self.get_object()
        ProductCommandService.activate_product(product.id)
        product.refresh_from_db()
        return Response(ProductDetailSerializer(product).data)

    @action(detail=True, methods=["post"], permission_classes=[IsStaffOrAdmin])
    def deactivate(self, request, lookup=None):
        product = self.get_object()
        ProductCommandService.deactivate_product(product.id)
        product.refresh_from_db()
        return Response(ProductDetailSerializer(product).data)

    @action(detail=True, methods=["get", "post"], permission_classes=[IsStaffOrAdmin])
    def variants(self, request, lookup=None):
        product = self.get_object()
        if request.method == "GET":
            serializer = ProductVariantSerializer(product.variants.all(), many=True)
            return Response(serializer.data)

        serializer = ProductVariantCreateUpdateSerializer(data=request.data, context={"product_id": product.id})
        serializer.is_valid(raise_exception=True)
        variant = ProductVariantService.create_variant(product_id=product.id, **serializer.validated_data)
        return Response(ProductVariantSerializer(variant).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], permission_classes=[IsStaffOrAdmin])
    def media(self, request, lookup=None):
        product = self.get_object()
        if request.method == "GET":
            serializer = ProductMediaSerializer(product.media.all(), many=True)
            return Response(serializer.data)

        serializer = ProductMediaCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        media = ProductMediaService.create_media(product_id=product.id, **serializer.validated_data)
        return Response(ProductMediaSerializer(media).data, status=status.HTTP_201_CREATED)


class AdminVariantViewSet(viewsets.ModelViewSet):
    """Admin variant management."""

    queryset = ProductVariantModel.objects.all()
    lookup_field = "id"
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ProductVariantCreateUpdateSerializer
        return ProductVariantSerializer

    @action(detail=True, methods=["post"], permission_classes=[IsStaffOrAdmin])
    def set_default(self, request, id=None):
        variant = self.get_object()
        ProductVariantService.set_default_variant(variant.id)
        variant.refresh_from_db()
        return Response(ProductVariantSerializer(variant).data)


class AdminMediaViewSet(viewsets.ModelViewSet):
    """Admin media management."""

    queryset = ProductMediaModel.objects.all()
    lookup_field = "id"
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ProductMediaCreateUpdateSerializer
        return ProductMediaSerializer


@extend_schema_view(
    snapshot=extend_schema(parameters=[OpenApiParameter("id", str, OpenApiParameter.PATH)]),
)
class InternalProductViewSet(viewsets.ViewSet):
    """Internal APIs for service-to-service communication."""

    serializer_class = ProductSnapshotSerializer
    permission_classes = [InternalServicePermission]

    @action(detail=False, methods=["post"], permission_classes=[InternalServicePermission])
    def bulk(self, request):
        serializer = InternalProductBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = [
            ProductCommandService.get_product_snapshot(product_id)
            for product_id in serializer.validated_data["product_ids"]
        ]
        return Response(result)

    @action(detail=True, methods=["get"], url_path="snapshot", permission_classes=[InternalServicePermission])
    def snapshot(self, request, pk=None):
        snapshot = ProductCommandService.get_product_snapshot(pk)
        serializer = ProductSnapshotSerializer(snapshot)
        return Response(serializer.data)


class InternalVariantViewSet(viewsets.ViewSet):
    """Internal variant APIs."""

    serializer_class = ProductVariantSerializer
    permission_classes = [InternalServicePermission]

    @action(detail=False, methods=["post"], permission_classes=[InternalServicePermission])
    def bulk(self, request):
        serializer = InternalVariantBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variants = ProductVariantModel.objects.filter(id__in=serializer.validated_data["variant_ids"]).select_related("product")
        return Response(ProductVariantSerializer(variants, many=True).data)
