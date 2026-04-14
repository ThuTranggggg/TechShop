"""
Domain enums for Catalog/Product context.

Defines immutable business concepts like ProductStatus, Currency, etc.
"""
from enum import Enum


class ProductStatus(str, Enum):
    """Product publication status."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

    def choices(self):
        """Return Django choices format."""
        return [(member.value, member.label) for member in self.__class__]


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    VND = "VND"
    EUR = "EUR"
    JPY = "JPY"

    def choices(self):
        """Return Django choices format."""
        return [(member.value, member.name) for member in self.__class__]


class AttributeType(str, Enum):
    """Attribute value types for flexible product attributes."""
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    ENUM = "enum"
    MULTISELECT = "multiselect"
    JSON = "json"

    def choices(self):
        """Return Django choices format."""
        return [(member.value, member.name) for member in self.__class__]


class MediaType(str, Enum):
    """Type of media/image."""
    THUMBNAIL = "thumbnail"
    MAIN = "main"
    GALLERY = "gallery"
    SPECIFICATIONS = "specifications"

    def choices(self):
        """Return Django choices format."""
        return [(member.value, member.name) for member in self.__class__]
