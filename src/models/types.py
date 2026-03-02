"""Cross-database compatibility types for SQLAlchemy.

This module provides database-agnostic column types that work with both
PostgreSQL (production) and SQLite (testing).
"""

import json
from typing import Any

from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY as PGARRAY
from sqlalchemy.dialects.postgresql import JSONB as PGJSONB
from sqlalchemy.dialects.postgresql import UUID as PGUIID


class JSONB(TypeDecorator):
    """Cross-platform JSONB type.
    
    Uses PostgreSQL JSONB in production, falls back to Text/JSON in SQLite.
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGJSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect) -> Any:
        if dialect.name != 'postgresql' and value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value: Any, dialect) -> Any:
        if dialect.name != 'postgresql' and value is not None:
            if isinstance(value, str):
                return json.loads(value)
        return value


class UUID(TypeDecorator):
    """Cross-platform UUID type.
    
    Uses PostgreSQL UUID in production, falls back to String(36) in SQLite.
    """
    impl = String(36)
    cache_ok = True

    def __init__(self, as_uuid: bool = True, *args, **kwargs):
        self.as_uuid = as_uuid
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUIID(as_uuid=self.as_uuid))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect) -> Any:
        if value is None:
            return None
        if dialect.name != 'postgresql':
            # Convert UUID to string for SQLite
            if hasattr(value, 'hex'):
                return str(value)
        return value

    def process_result_value(self, value: Any, dialect) -> Any:
        if value is None:
            return None
        if dialect.name != 'postgresql' and self.as_uuid:
            # Convert string back to UUID for SQLite
            import uuid
            if isinstance(value, str):
                return uuid.UUID(value)
        return value


class ARRAY(TypeDecorator):
    """Cross-platform ARRAY type.
    
    Uses PostgreSQL ARRAY in production, falls back to Text/JSON in SQLite.
    """
    impl = Text
    cache_ok = True

    def __init__(self, item_type: type = String, dimensions: int = 1, *args, **kwargs):
        self.item_type = item_type
        self.dimensions = dimensions
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGARRAY(self.item_type, dimensions=self.dimensions))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect) -> Any:
        if dialect.name != 'postgresql' and value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value: Any, dialect) -> Any:
        if dialect.name != 'postgresql' and value is not None:
            if isinstance(value, str):
                return json.loads(value)
        return value
