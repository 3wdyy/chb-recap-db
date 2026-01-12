"""
Transformer factory for creating field transformers.

Maps transformation types to their implementations and
provides a unified interface for the transform step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from ..core.config_models import FieldMapping, TransformType
from .base_transformer import BaseTransformer
from .implementations import (
    CleanTransformer,
    ConditionalTransformer,
    CurrencyConvertTransformer,
    DateTransformer,
    DirectTransformer,
    FormulaTransformer,
    LookupTransformer,
    PhoneTransformer,
    StaticTransformer,
    TaxExcludeTransformer,
)

if TYPE_CHECKING:
    from ..core.processing_context import ProcessingContext


class TransformerFactory:
    """
    Factory for creating field transformer instances.

    Maps TransformType enums to their implementation classes
    and provides a unified interface for creating transformers.
    """

    # Default transformer registry
    _registry: dict[TransformType, Type[BaseTransformer]] = {
        TransformType.STATIC: StaticTransformer,
        TransformType.DIRECT: DirectTransformer,
        TransformType.LOOKUP: LookupTransformer,
        TransformType.DATE: DateTransformer,
        TransformType.PHONE: PhoneTransformer,
        TransformType.FORMULA: FormulaTransformer,
        TransformType.CURRENCY_CONVERT: CurrencyConvertTransformer,
        TransformType.TAX_EXCLUDE: TaxExcludeTransformer,
        TransformType.CLEAN: CleanTransformer,
        TransformType.CONDITIONAL: ConditionalTransformer,
    }

    def __init__(self, context: ProcessingContext):
        """
        Initialize the factory.

        Args:
            context: Processing context to pass to transformers
        """
        self.context = context
        self._instances: dict[TransformType, BaseTransformer] = {}

    def get_transformer(self, transform_type: TransformType) -> BaseTransformer:
        """
        Get a transformer instance for the given type.

        Instances are cached for reuse within a processing run.

        Args:
            transform_type: The type of transformation

        Returns:
            Transformer instance

        Raises:
            ValueError: If transform type is not registered
        """
        if transform_type not in self._instances:
            transformer_class = self._registry.get(transform_type)
            if transformer_class is None:
                raise ValueError(f"Unknown transform type: {transform_type}")
            self._instances[transform_type] = transformer_class(self.context)

        return self._instances[transform_type]

    @classmethod
    def register(
        cls, transform_type: TransformType, transformer_class: Type[BaseTransformer]
    ) -> None:
        """
        Register a custom transformer class.

        Args:
            transform_type: The transform type to register
            transformer_class: The transformer class to use
        """
        cls._registry[transform_type] = transformer_class

    @classmethod
    def get_registered_types(cls) -> list[TransformType]:
        """Get list of registered transform types."""
        return list(cls._registry.keys())
