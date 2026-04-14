"""
URL routing for Catalog API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    BrandViewSet,
    ProductTypeViewSet,
    PublicProductViewSet,
    AdminCategoryViewSet,
    AdminBrandViewSet,
    AdminProductTypeViewSet,
    AdminProductViewSet,
    AdminVariantViewSet,
    AdminMediaViewSet,
    InternalProductViewSet,
    InternalVariantViewSet,
)

# Public catalog router
public_router = DefaultRouter()
public_router.register(r'categories', CategoryViewSet, basename='public-category')
public_router.register(r'brands', BrandViewSet, basename='public-brand')
public_router.register(r'product-types', ProductTypeViewSet, basename='public-product-type')
public_router.register(r'products', PublicProductViewSet, basename='public-product')

# Admin management router
admin_router = DefaultRouter()
admin_router.register(r'categories', AdminCategoryViewSet, basename='admin-category')
admin_router.register(r'brands', AdminBrandViewSet, basename='admin-brand')
admin_router.register(r'product-types', AdminProductTypeViewSet, basename='admin-product-type')
admin_router.register(r'products', AdminProductViewSet, basename='admin-product')
admin_router.register(r'variants', AdminVariantViewSet, basename='admin-variant')
admin_router.register(r'media', AdminMediaViewSet, basename='admin-media')

# Internal service router
internal_router = DefaultRouter()
internal_router.register(r'products', InternalProductViewSet, basename='internal-product')
internal_router.register(r'variants', InternalVariantViewSet, basename='internal-variant')

urlpatterns = [
    # Public catalog APIs
    path('', include(public_router.urls), name='public-catalog'),
    
    # Admin management APIs
    path('admin/', include(admin_router.urls), name='admin-catalog'),
    
    # Internal service APIs
    path('internal/', include(internal_router.urls), name='internal-catalog'),
]
