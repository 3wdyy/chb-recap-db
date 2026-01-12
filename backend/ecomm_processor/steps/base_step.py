"""Base class for pipeline steps."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from ..core.processing_context import ProcessingContext


class BaseStep(ABC):
    """
    Abstract base class for pipeline steps.

    Each step receives a DataFrame and configuration,
    and returns a transformed DataFrame.
    """

    def __init__(self, context: ProcessingContext):
        """
        Initialize the step.

        Args:
            context: Processing context with global/brand config and error tracking
        """
        self.context = context

    @abstractmethod
    def execute(self, df: pd.DataFrame, config: Any) -> pd.DataFrame:
        """
        Execute the step on the DataFrame.

        Args:
            df: Input DataFrame
            config: Step-specific configuration

        Returns:
            Transformed DataFrame
        """
        pass

    def resolve_ref(self, value: Any) -> Any:
        """Resolve $ref: references in configuration values."""
        if isinstance(value, str) and value.startswith("$ref:"):
            return self.context.resolve_reference(value)
        return value
