"""Validate step implementation."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..core.processing_context import ErrorSeverity
from .base_step import BaseStep


class ValidateStep(BaseStep):
    """
    Validates output DataFrame before export.

    Checks for required fields, data types, and value constraints.
    Can quarantine invalid rows instead of failing entirely.
    """

    def execute(self, df: pd.DataFrame, config: dict) -> pd.DataFrame:
        """Execute the validate step."""
        # Get validation config with defaults
        required_fields = config.get("required_fields", [])
        quarantine_invalid = config.get("quarantine_invalid", True)
        validate_types = config.get("validate_types", {})

        rows_to_keep = []

        for idx, row in df.iterrows():
            row_index = idx if isinstance(idx, int) else 0
            is_valid = True

            # Check required fields
            for field in required_fields:
                if field not in row.index:
                    self.context.add_error(
                        f"Required field '{field}' missing",
                        column=field,
                        row_index=row_index,
                        severity=ErrorSeverity.ERROR,
                    )
                    is_valid = False
                elif self._is_empty(row[field]):
                    self.context.add_warning(
                        f"Required field '{field}' is empty",
                        column=field,
                        row_index=row_index,
                        original_value=row[field],
                    )
                    # Don't mark as invalid for empty - just warn

            # Validate data types
            for field, expected_type in validate_types.items():
                if field in row.index:
                    if not self._validate_type(row[field], expected_type):
                        self.context.add_warning(
                            f"Field '{field}' has invalid type (expected {expected_type})",
                            column=field,
                            row_index=row_index,
                            original_value=row[field],
                        )

            if is_valid or not quarantine_invalid:
                rows_to_keep.append(idx)
            else:
                self.context.quarantine_row(row_index, "Failed validation")

        # Return filtered DataFrame
        return df.loc[rows_to_keep].copy()

    def _is_empty(self, value: Any) -> bool:
        """Check if a value is empty/null."""
        if value is None:
            return True
        if isinstance(value, float) and pd.isna(value):
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate that a value matches expected type."""
        if self._is_empty(value):
            return True  # Empty values pass type check

        if expected_type == "numeric":
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False

        elif expected_type == "string":
            return isinstance(value, str)

        elif expected_type == "date":
            # Check if it looks like a date string
            if isinstance(value, str):
                return "T" in value or "-" in value
            return True

        return True
