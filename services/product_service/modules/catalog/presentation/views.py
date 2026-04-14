"""
Presentation layer views for Catalog API.

API endpoints for public catalog, admin management, and internal services.
"""
from typing import List, Dict, Any
from django.shortcuts import get_object_or_404
from django.db.models import Q, Prefetch
from django.utils import timezone
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from common.responses import success_response, error_response
from ..application.services import (
    CategoryService,
    BrandService,
    ProductTypeService,
    ProductService,
    ProductVariantService,
    ProductMediaService,
)
from ..domain.enums import ProductStatus
from ..infrastructure.models import (
    CategoryModel,
    BrandModel,
    ProductTypeModel,
    ProductModel,
    ProductVariantModel,
    ProductMediaModel,
)
from .serializers import (
    CategorySerializer,
    CategoryCreateUpdateSerializer,
    BrandSerializer,
    BrandCreateUpdateSerializer,
    ProductTypeSerializer,
    ProductTypeCreateUpdateSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductVariantSerializer,
    ProductVariantCreateUpdateSerializer,
    ProductMediaSerializer,
    ProductMediaCreateUpdateSerializer,
    ProductSnapshotSerializer,
    InternalProductBulkSerializer,
    InternalVariantBulkSerializer,
)
from .permissions import IsStaffOrAdmin, InternalServicePermission, IsPublicRead


class StandardPagination(PageNumberPagination):
    """Standard pagination for catalog APIs."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ============================================================================
# PUBLIC CATALOG APIs
# ============================================================================

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Public category browsing - read-only."""
    queryset = CategoryModel.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    lookup_field = 'id'
    pagination_class = StandardPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'slug', 'description']
    ordering_fields = ['name', 'sort_order', 'created_at']
    ordering = ['sort_order', 'name']
    permission_classes = [IsPublicRead]

    def get_queryset(self):
        """Filter active categories only."""
        return self.queryset.filter(is_active=True).select_related('parent')


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    """Public brand browsing - read-only."""
    queryset = BrandModel.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    lookup_field = 'id'
    pagination_class = StandardPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'slug', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    permission_classes = [IsPublicRead]


class ProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Public product type browsing - read-only."""
    queryset = ProductTypeModel.objects.filter(is_active=True)
    serializer_class = ProductTypeSerializer
    lookup_field = 'id'
    pagination_class = StandardPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'code', 'description']
    permission_classes = [IsPublicRead]


class PublicProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Public product catalog - browse, search, filter."""
    queryset = ProductModel.objects.filter(
        status=ProductStatus.ACTIVE.value,
        is_active=True,
        published_at__isnull=False
    )
    lookup_field = 'id'
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        'name',
        'slug',
        'short_description',
        'description',
        'category__name',
        'brand__name',
    ]
    ordering_fields = ['name', 'base_price', 'created_at', 'published_at']
    ordering = ['-published_at', 'name']
    permission_classes = [IsPublicRead]
    filterset_fields = {
        'category': ['exact'],
        'brand': ['exact'],
        'product_type': ['exact'],
        'is_featured': ['exact'],
        'base_price': ['gte', 'lte'],
    }

    def get_serializer_class(self):
        """Use detail serializer for retrieve, list for list."""
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        """Optimize with select_related and prefetch."""
        qs = self.queryset.select_related(
            'category', 'brand', 'product_type'
        ).prefetch_related('variants', 'media')
        return qs

    @action(detail=False, methods=['get'], permission_classes=[IsPublicRead])
    def search(self, request):
        """Search products with advanced filtering."""
        query = request.query_params.get('q', '').strip()
        category_slug = request.query_params.get('category_slug')
        brand_slug = request.query_params.get('brand_slug')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        is_featured = request.query_params.get('is_featured')
        
        qs = self.get_queryset()
        
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(short_description__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(brand__name__icontains=query)
            )
        
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        
        if brand_slug:
            qs = qs.filter(brand__slug=brand_slug)
        
        if min_price:
            qs = qs.filter(base_price__gte=min_price)
        
        if max_price:
            qs = qs.filter(base_price__lte=max_price)
        
        if is_featured and is_featured.lower() == 'true':
            qs = qs.filter(is_featured=True)
        
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsPublicRead])
    def variants(self, request, id=None):
        """Get product variants."""
        product = self.get_object()
        variants = product.variants.filter(is_active=True)
        serializer = ProductVariantSerializer(variants, many=True)
        return Response(serializer.data)


# ============================================================================
# ADMIN/STAFF CATALOG MANAGEMENT APIs
# ============================================================================

class AdminCategoryViewSet(viewsets.ModelViewSet):
    """Admin category management."""
    queryset = CategoryModel.objects.all()
    lookup_field = 'id'
    pagination_class = StandardPagination
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        """Use different serializer for create/update."""
        if self.action in ['create', 'update', 'partial_update']:
            return CategoryCreateUpdateSerializer
        return CategorySerializer

    def create(self, request, *args, **kwargs):
        """Create new category."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            response_serializer = CategorySerializer(instance)
            return StandardResponse(
                data=response_serializer.data,
                message="Category created successfully",
                status_code=status.HTTP_201_CREATED
            ).to_response()
        except Exception as e:
            return ErrorResponse(
                error="Failed to create category",
                details=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_response()


class AdminBrandViewSet(viewsets.ModelViewSet):
    """Admin brand management."""
    queryset = BrandModel.objects.all()
    lookup_field = 'id'
    pagination_class = StandardPagination
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BrandCreateUpdateSerializer
        return BrandSerializer


class AdminProductTypeViewSet(viewsets.ModelViewSet):
    """Admin product type management."""
    queryset = ProductTypeModel.objects.all()
    lookup_field = 'id'
    pagination_class = StandardPagination
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductTypeCreateUpdateSerializer
        return ProductTypeSerializer


class AdminProductViewSet(viewsets.ModelViewSet):
    """Admin product management."""
    queryset = ProductModel.objects.all()
    lookup_field = 'id'
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'slug', 'short_description']
    ordering_fields = ['name', 'base_price', 'created_at', 'published_at']
    ordering = ['-created_at']
    permission_classes = [IsStaffOrAdmin]
    filterset_fields = {
        'status': ['exact'],
        'is_active': ['exact'],
        'is_featured': ['exact'],
        'category': ['exact'],
        'brand': ['exact'],
    }

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        """Optimize queries."""
        return self.queryset.select_related(
            'category', 'brand', 'product_type'
        ).prefetch_related('variants', 'media')

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def publish(self, request, id=None):
        """Publish product."""
        product = self.get_object()
        try:
            ProductService.publish_product(product.id)
            product.refresh_from_db()
            serializer = ProductDetailSerializer(product)
            return StandardResponse(
                data=serializer.data,
                message="Product published successfully",
                status_code=status.HTTP_200_OK
            ).to_response()
        except Exception as e:
            return ErrorResponse(
                error="Failed to publish product",
                details=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_response()

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def unpublish(self, request, id=None):
        """Unpublish product."""
        product = self.get_object()
        try:
            ProductService.unpublish_product(product.id)
            product.refresh_from_db()
            serializer = ProductDetailSerializer(product)
            return StandardResponse(
                data=serializer.data,
                message="Product unpublished successfully",
                status_code=status.HTTP_200_OK
            ).to_response()
        except Exception as e:
            return ErrorResponse(
                error="Failed to unpublish product",
                details=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            ).to_response()

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def activate(self, request, id=None):
        """Activate product."""
        product = self.get_object()
        ProductService.activate_product(product.id)
        product.refresh_from_db()
        serializer = ProductDetailSerializer(product)
        return StandardResponse(
            data=serializer.data,
            message="Product activated",
            status_code=status.HTTP_200_OK
        ).to_response()

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def deactivate(self, request, id=None):
        """Deactivate product."""
        product = self.get_object()
        ProductService.deactivate_product(product.id)
        product.refresh_from_db()
        serializer = ProductDetailSerializer(product)
        return StandardResponse(
            data=serializer.data,
            message="Product deactivated",
            status_code=status.HTTP_200_OK
        ).to_response()

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsStaffOrAdmin])
    def variants(self, request, id=None):
        """Manage product variants."""
        product = self.get_object()
        if request.method == 'GET':
            variants = product.variants.all()
            serializer = ProductVariantSerializer(variants, many=True)
            return Response(serializer.data)
        else:
            # POST - create variant
            serializer = ProductVariantCreateUpdateSerializer(
                data=request.data,
                context={'product_id': product.id}
            )
            serializer.is_valid(raise_exception=True)
            variant = ProductVariantService.create_variant(
                product_id=product.id,
                **serializer.validated_data
            )
            result_serializer = ProductVariantSerializer(variant)
            return StandardResponse(
                data=result_serializer.data,
                message="Variant created",
                status_code=status.HTTP_201_CREATED
            ).to_response()

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsStaffOrAdmin])
    def media(self, request, id=None):
        """Manage product media."""
        product = self.get_object()
        if request.method == 'GET':
            media = product.media.all()
            serializer = ProductMediaSerializer(media, many=True)
            return Response(serializer.data)
        else:
            # POST - create media
            serializer = ProductMediaCreateUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            media = ProductMediaService.create_media(
                product_id=product.id,
                **serializer.validated_data
            )
            result_serializer = ProductMediaSerializer(media)
            return StandardResponse(
                data=result_serializer.data,
                message="Media created",
                status_code=status.HTTP_201_CREATED
            ).to_response()


class AdminVariantViewSet(viewsets.ModelViewSet):
    """Admin variant management."""
    queryset = ProductVariantModel.objects.all()
    lookup_field = 'id'
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductVariantCreateUpdateSerializer
        return ProductVariantSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def set_default(self, request, id=None):
        """Set as default variant."""
        variant = self.get_object()
        ProductVariantService.set_default_variant(variant.id)
        variant.refresh_from_db()
        serializer = ProductVariantSerializer(variant)
        return StandardResponse(
            data=serializer.data,
            message="Variant set as default",
            status_code=status.HTTP_200_OK
        ).to_response()


class AdminMediaViewSet(viewsets.ModelViewSet):
    """Admin media management."""
    queryset = ProductMediaModel.objects.all()
    lookup_field = 'id'
    permission_classes = [IsStaffOrAdmin]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductMediaCreateUpdateSerializer
        return ProductMediaSerializer


# ============================================================================
# INTERNAL SERVICE APIs
# ============================================================================

class InternalProductViewSet(viewsets.ViewSet):
    """Internal APIs for service-to-service communication."""
    permission_classes = [InternalServicePermission]

    @action(detail=False, methods=['post'], permission_classes=[InternalServicePermission])
    def bulk(self, request):
        """Get multiple products by IDs."""
        serializer = InternalProductBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_ids = serializer.validated_data['product_ids']
        include_variants = serializer.validated_data.get('include_variants', False)
        include_media = serializer.validated_data.get('include_media', False)

        products = ProductModel.objects.filter(id__in=product_ids).select_related(
            'category', 'brand', 'product_type'
        )
        if include_variants:
            products = products.prefetch_related('variants')
        if include_media:
            products = products.prefetch_related('media')

        result = []
        for product in products:
            snapshot = ProductService.get_product_snapshot(product.id)
            result.append(snapshot)

        return StandardResponse(
            data=result,
            message="Products retrieved",
            status_code=status.HTTP_200_OK
        ).to_response()

    @action(detail=True, methods=['get'], url_path='snapshot',
            permission_classes=[InternalServicePermission])
    def snapshot(self, request, pk=None):
        """Get product snapshot for order/cart."""
        try:
            product = ProductModel.objects.get(id=pk)
            snapshot = ProductService.get_product_snapshot(product.id)
            serializer = ProductSnapshotSerializer(snapshot)
            return StandardResponse(
                data=serializer.data,
                message="Product snapshot retrieved",
                status_code=status.HTTP_200_OK
            ).to_response()
        except ProductModel.DoesNotExist:
            return ErrorResponse(
                error="Product not found",
                status_code=status.HTTP_404_NOT_FOUND
            ).to_response()


class InternalVariantViewSet(viewsets.ViewSet):
    """Internal variant APIs."""
    permission_classes = [InternalServicePermission]

    @action(detail=False, methods=['post'], permission_classes=[InternalServicePermission])
    def bulk(self, request):
        """Get multiple variants by IDs."""
        serializer = InternalVariantBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variant_ids = serializer.validated_data['variant_ids']
        variants = ProductVariantModel.objects.filter(id__in=variant_ids).select_related('product')

        result_serializer = ProductVariantSerializer(variants, many=True)
        return StandardResponse(
            data=result_serializer.data,
            message="Variants retrieved",
            status_code=status.HTTP_200_OK
        ).to_response()
