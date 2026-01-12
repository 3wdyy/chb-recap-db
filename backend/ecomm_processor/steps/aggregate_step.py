"""Aggregate step implementation."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from ..core.config_models import AggregateConfig, AggregateFunction, AggregationRule
from ..core.processing_context import ErrorSeverity
from .base_step import BaseStep


class AggregateStep(BaseStep):
    """
    Aggregates DataFrame rows by grouping column.

    Supports various aggregation functions including
    first_non_null for handling sparse data.
    """

    def execute(self, df: pd.DataFrame, config: AggregateConfig) -> pd.DataFrame:
        """Execute the aggregate step."""
        group_by = config.group_by

        # Validate group_by column exists
        if group_by not in df.columns:
            self.context.add_error(
                f"Group by column '{group_by}' not found",
                severity=ErrorSeverity.ERROR,
            )
            return df

        # Build aggregation specification
        agg_spec = {}
        rename_map = {}

        for output_name, rule in config.aggregations.items():
            if rule.source not in df.columns:
                self.context.add_warning(
                    f"Aggregation source column '{rule.source}' not found"
                )
                continue

            # Coerce to numeric if requested
            if rule.coerce_numeric:
                df[rule.source] = pd.to_numeric(df[rule.source], errors="coerce")

            # Get aggregation function
            agg_func = self._get_agg_function(rule)
            if agg_func is None:
                continue

            # pandas agg needs (column, func) pairs or named aggs
            agg_spec[output_name] = pd.NamedAgg(column=rule.source, aggfunc=agg_func)

        if not agg_spec:
            self.context.add_error(
                "No valid aggregations to perform",
                severity=ErrorSeverity.ERROR,
            )
            return df

        # Perform aggregation
        try:
            result = df.groupby(group_by, as_index=False).agg(**agg_spec)
        except Exception as e:
            self.context.add_error(
                f"Aggregation failed: {str(e)}",
                severity=ErrorSeverity.ERROR,
            )
            return df

        return result

    def _get_agg_function(
        self, rule: AggregationRule
    ) -> str | Callable | None:
        """Get the pandas aggregation function for a rule."""
        func = rule.function

        if func == AggregateFunction.SUM:
            return "sum"
        elif func == AggregateFunction.MAX:
            return "max"
        elif func == AggregateFunction.MIN:
            return "min"
        elif func == AggregateFunction.MEAN:
            return "mean"
        elif func == AggregateFunction.FIRST:
            return "first"
        elif func == AggregateFunction.LAST:
            return "last"
        elif func == AggregateFunction.COUNT:
            return "count"
        elif func == AggregateFunction.FIRST_NON_NULL:
            return self._first_non_null
        elif func == AggregateFunction.CONCAT:
            return lambda x: rule.separator.join(x.dropna().astype(str).unique())
        else:
            self.context.add_warning(f"Unknown aggregation function: {func}")
            return None

    @staticmethod
    def _first_non_null(series: pd.Series) -> Any:
        """Return first non-null value in series."""
        non_null = series.dropna()
        if len(non_null) > 0:
            return non_null.iloc[0]
        return np.nan
