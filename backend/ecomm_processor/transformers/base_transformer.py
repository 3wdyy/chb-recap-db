"""Base class for field transformers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..core.config_models import FieldMapping
    from ..core.processing_context import ProcessingContext


class BaseTransformer(ABC):
    """
    Abstract base class for field transformers.

    Each transformer takes a row (Series) and field mapping config,
    and returns the transformed value.
    """

    def __init__(self, context: ProcessingContext):
        """
        Initialize the transformer.

        Args:
            context: Processing context with config and error tracking
        """
        self.context = context

    @abstractmethod
    def transform(
        self, row: pd.Series, mapping: FieldMapping, row_index: int
    ) -> Any:
        """
        Transform a single field value.

        Args:
            row: DataFrame row as Series
            mapping: Field mapping configuration
            row_index: Row index for error reporting

        Returns:
            Transformed value
        """
        pass

    def resolve_ref(self, value: Any) -> Any:
        """Resolve $ref: references."""
        if isinstance(value, str) and value.startswith("$ref:"):
            return self.context.resolve_reference(value)
        return value

    def get_column_value(self, row: pd.Series, column: str, default: Any = None) -> Any:
        """Safely get a column value from a row."""
        if column in row.index:
            return row[column]
        return default
