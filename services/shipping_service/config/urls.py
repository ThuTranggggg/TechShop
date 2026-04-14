from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from common.health import HealthView, ReadyView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthView.as_view(), name="health"),
    path("ready/", ReadyView.as_view(), name="ready"),
    path("api/v1/health/", HealthView.as_view(), name="api-health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Shipping service URLs
    path("api/v1/", include("modules.shipping.urls")),
]
