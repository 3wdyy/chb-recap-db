"""Transform step implementation."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..core.config_models import TransformConfig
from ..core.processing_context import ErrorSeverity
from ..transformers.transformer_factory import TransformerFactory
from .base_step import BaseStep


class TransformStep(BaseStep):
    """
    Transforms DataFrame columns based on field mappings.

    Uses the TransformerFactory to delegate to specific
    transformer implementations for each field.

    Processes fields in order so that later fields can reference
    values calculated by earlier fields in the same row.
    """

    def execute(self, df: pd.DataFrame, config: TransformConfig) -> pd.DataFrame:
        """Execute the transform step."""
        if not config.mappings:
            return df

        # Create transformer factory
        factory = TransformerFactory(self.context)

        # Process each output field
        result_data: dict[str, list[Any]] = {
            field_name: [] for field_name in config.mappings.keys()
        }

        # Process row by row
        for idx, row in df.iterrows():
            self.context.current_row = idx if isinstance(idx, int) else 0

            # Create an extended row that includes calculated values
            # This allows later fields to reference earlier calculated fields
            extended_row = row.copy()

            for field_name, mapping in config.mappings.items():
                try:
                    transformer = factory.get_transformer(mapping.type)
                    value = transformer.transform(extended_row, mapping, self.context.current_row)
                    result_data[field_name].append(value)

                    # Add calculated value to extended row for subsequent fields
                    extended_row[field_name] = value
                except Exception as e:
                    self.context.add_warning(
                        f"Transform failed for {field_name}: {str(e)}",
                        column=field_name,
                        row_index=self.context.current_row,
                    )
                    result_data[field_name].append(None)
                    extended_row[field_name] = None

        # Build result DataFrame
        result_df = pd.DataFrame(result_data)

        # Copy index from original
        result_df.index = df.index

        return result_df
