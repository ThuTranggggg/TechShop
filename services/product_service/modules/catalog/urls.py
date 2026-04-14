"""Route catalog endpoints through presentation URL module."""
from django.urls import include, path

app_name = "catalog"

urlpatterns = [
    path("", include("modules.catalog.presentation.urls")),
]
