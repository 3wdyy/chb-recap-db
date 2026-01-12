"""Filter step implementation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..core.config_models import FilterCondition, FilterConfig, FilterOperator
from ..core.processing_context import ErrorSeverity
from .base_step import BaseStep


class FilterStep(BaseStep):
    """
    Filters DataFrame rows based on configured conditions.

    Supports multiple conditions with AND/OR logic,
    various operators, and optional column skipping.
    """

    def execute(self, df: pd.DataFrame, config: FilterConfig) -> pd.DataFrame:
        """Execute the filter step."""
        if not config.conditions:
            return df

        masks = []
        for condition in config.conditions:
            mask = self._evaluate_condition(df, condition)
            if mask is not None:
                masks.append(mask)

        if not masks:
            return df

        # Combine masks based on mode
        if config.mode == "all_of":
            combined_mask = masks[0]
            for mask in masks[1:]:
                combined_mask = combined_mask & mask
        else:  # any_of
            combined_mask = masks[0]
            for mask in masks[1:]:
                combined_mask = combined_mask | mask

        return df[combined_mask].copy()

    def _evaluate_condition(
        self, df: pd.DataFrame, condition: FilterCondition
    ) -> pd.Series | None:
        """
        Evaluate a single filter condition.

        Returns a boolean Series mask, or None if condition should be skipped.
        """
        column = condition.column

        # Check if column exists
        if column not in df.columns:
            if condition.skip_if_column_missing:
                self.context.add_warning(
                    f"Filter column '{column}' not found, skipping condition"
                )
                return None
            else:
                self.context.add_error(
                    f"Filter column '{column}' not found",
                    severity=ErrorSeverity.ERROR,
                )
                # Return all True to not filter anything
                return pd.Series([True] * len(df), index=df.index)

        # Get column values
        col_values = df[column]

        # Resolve value references
        value = self.resolve_ref(condition.value)

        # Handle case sensitivity for string operations
        if not condition.case_sensitive and col_values.dtype == object:
            col_values = col_values.astype(str).str.upper()
            if isinstance(value, str):
                value = value.upper()
            elif isinstance(value, list):
                value = [v.upper() if isinstance(v, str) else v for v in value]

        # Apply operator
        return self._apply_operator(col_values, condition.operator, value)

    def _apply_operator(
        self, col_values: pd.Series, operator: FilterOperator, value: Any
    ) -> pd.Series:
        """Apply the filter operator to get a boolean mask."""
        if operator == FilterOperator.EQUALS:
            return col_values == value

        elif operator == FilterOperator.NOT_EQUALS:
            return col_values != value

        elif operator == FilterOperator.CONTAINS:
            return col_values.astype(str).str.contains(str(value), na=False)

        elif operator == FilterOperator.NOT_CONTAINS:
            return ~col_values.astype(str).str.contains(str(value), na=False)

        elif operator == FilterOperator.IN:
            if isinstance(value, str):
                # Handle comma-separated string
                value = [v.strip() for v in value.split(",")]
            return col_values.isin(value)

        elif operator == FilterOperator.NOT_IN:
            if isinstance(value, str):
                value = [v.strip() for v in value.split(",")]
            return ~col_values.isin(value)

        elif operator == FilterOperator.GREATER_THAN:
            return pd.to_numeric(col_values, errors="coerce") > float(value)

        elif operator == FilterOperator.LESS_THAN:
            return pd.to_numeric(col_values, errors="coerce") < float(value)

        elif operator == FilterOperator.GREATER_EQUAL:
            return pd.to_numeric(col_values, errors="coerce") >= float(value)

        elif operator == FilterOperator.LESS_EQUAL:
            return pd.to_numeric(col_values, errors="coerce") <= float(value)

        elif operator == FilterOperator.IS_NULL:
            return col_values.isna() | (col_values == "") | (col_values.astype(str).str.strip() == "")

        elif operator == FilterOperator.IS_NOT_NULL:
            return col_values.notna() & (col_values != "") & (col_values.astype(str).str.strip() != "")

        elif operator == FilterOperator.STARTS_WITH:
            return col_values.astype(str).str.startswith(str(value), na=False)

        elif operator == FilterOperator.ENDS_WITH:
            return col_values.astype(str).str.endswith(str(value), na=False)

        else:
            self.context.add_warning(f"Unknown operator: {operator}")
            return pd.Series([True] * len(col_values), index=col_values.index)
