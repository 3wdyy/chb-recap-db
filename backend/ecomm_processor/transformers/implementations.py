"""
Field transformer implementations.

Each transformer handles a specific type of field transformation
as defined in the FieldMapping configuration.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from dateutil import parser as date_parser

from ..core.config_models import (
    DataTransform,
    FieldMapping,
    LookupStrategy,
    TaxStrategy,
)
from ..core.processing_context import ErrorSeverity
from .base_transformer import BaseTransformer


class StaticTransformer(BaseTransformer):
    """Returns a static value for all rows."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        return mapping.value


class DirectTransformer(BaseTransformer):
    """Copies value directly from source column with optional transform."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.source_column:
            return None

        value = self.get_column_value(row, mapping.source_column)

        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None

        # Apply optional transformation
        if mapping.transform:
            value = self._apply_transform(value, mapping.transform, row_index)

        return value

    def _apply_transform(
        self, value: Any, transform: DataTransform, row_index: int
    ) -> Any:
        """Apply a simple transformation to the value."""
        try:
            if transform == DataTransform.TO_STRING:
                return str(value)
            elif transform == DataTransform.TO_NUMERIC:
                return pd.to_numeric(value, errors="coerce")
            elif transform == DataTransform.TO_UPPER:
                return str(value).upper()
            elif transform == DataTransform.TO_LOWER:
                return str(value).lower()
            elif transform == DataTransform.STRIP:
                return str(value).strip()
        except Exception as e:
            self.context.add_warning(
                f"Transform {transform} failed: {e}",
                row_index=row_index,
                original_value=value,
            )
        return value


class LookupTransformer(BaseTransformer):
    """Looks up values based on configured strategy."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.lookup:
            return None

        config = mapping.lookup
        source_value = self.get_column_value(row, config.source_column)

        if source_value is None:
            return config.default

        # Apply strategy
        if config.strategy == LookupStrategy.ORDER_PREFIX:
            return self._lookup_by_prefix(source_value, config)
        else:
            return self._lookup_direct(source_value, config)

    def _lookup_direct(self, value: Any, config) -> Any:
        """Direct lookup in mapping dictionary."""
        # Handle country name normalization for country_map strategy
        if config.strategy == LookupStrategy.COUNTRY_MAP:
            value = self._normalize_country(value)

        str_value = str(value).strip()
        result = config.mapping.get(str_value)

        if result is None:
            # Try case-insensitive lookup
            for key, val in config.mapping.items():
                if str(key).upper() == str_value.upper():
                    return val

        return result if result is not None else config.default

    def _lookup_by_prefix(self, value: Any, config) -> Any:
        """Lookup by extracting prefix from value."""
        str_value = str(value).upper()
        prefix_len = config.prefix_length or 4
        prefix = str_value[:prefix_len]

        result = config.mapping.get(prefix)
        return result if result is not None else config.default

    def _normalize_country(self, value: Any) -> str:
        """Normalize country name/code to full name."""
        value_str = str(value).upper().strip()

        # Common country code mappings
        country_map = {
            "AE": "United Arab Emirates",
            "UAE": "United Arab Emirates",
            "SA": "Saudi Arabia",
            "KSA": "Saudi Arabia",
            "KW": "Kuwait",
            "BH": "Bahrain",
        }

        return country_map.get(value_str, str(value))


class DateTransformer(BaseTransformer):
    """Parses and formats date values."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.date:
            return None

        config = mapping.date
        value = self.get_column_value(row, config.source_column)

        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None

        try:
            # Parse date
            if config.input_format and config.input_format != "auto":
                dt = pd.to_datetime(value, format=config.input_format)
            else:
                # Auto-detect format
                if isinstance(value, (pd.Timestamp, np.datetime64)):
                    dt = pd.to_datetime(value)
                else:
                    dt = date_parser.parse(str(value))

            # Format output
            if pd.isna(dt):
                return None

            return dt.strftime(config.output_format)

        except Exception as e:
            self.context.add_warning(
                f"Date parsing failed: {e}",
                column=config.source_column,
                row_index=row_index,
                original_value=value,
            )
            return None


class PhoneTransformer(BaseTransformer):
    """Formats phone numbers with country codes."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.phone:
            return None

        config = mapping.phone
        country = self.get_column_value(row, config.country_column)
        phone = self.get_column_value(row, config.phone_column)

        if phone is None:
            return None

        # Clean phone number
        phone_str = str(phone).replace(" ", "").replace(".0", "").replace("-", "")

        # Remove any existing country code prefix
        if phone_str.startswith("+"):
            phone_str = phone_str[1:]
        if phone_str.startswith("00"):
            phone_str = phone_str[2:]

        # Get country code config
        phone_config = self.context.global_config.get_phone_code(country)

        if phone_config:
            country_code, digits_to_keep = phone_config
            # Take last N digits
            local_number = phone_str[-digits_to_keep:] if len(phone_str) >= digits_to_keep else phone_str
            return f"{country_code}{local_number}"

        # Return cleaned number if no country code found
        return phone_str


class FormulaTransformer(BaseTransformer):
    """Evaluates formula expressions."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.formula:
            return None

        config = mapping.formula
        expression = config.expression

        # Handle COALESCE FIRST (before general column replacement)
        eval_expr = self._handle_coalesce(expression, row, config.coerce_numeric)

        # Extract remaining column references {column_name}
        column_refs = re.findall(r"\{([^}]+)\}", eval_expr)

        # Replace column references with values
        for col_name in column_refs:
            value = self.get_column_value(row, col_name, 0)

            if config.coerce_numeric:
                value = pd.to_numeric(value, errors="coerce")
                if pd.isna(value):
                    value = 0

            # Replace in expression
            eval_expr = eval_expr.replace(f"{{{col_name}}}", str(float(value)))

        try:
            # Safe evaluation (only allow basic math)
            result = eval(eval_expr, {"__builtins__": {}}, {})
            return result
        except Exception as e:
            self.context.add_warning(
                f"Formula evaluation failed: {e}",
                row_index=row_index,
                original_value=expression,
            )
            return None

    def _handle_coalesce(self, expr: str, row: pd.Series, coerce_numeric: bool = True) -> str:
        """Handle COALESCE({column}, default) in expressions."""
        # Pattern matches: COALESCE({column_name}, default_value)
        coalesce_pattern = r"COALESCE\(\{([^}]+)\},\s*(\d+(?:\.\d+)?)\)"

        def replace_coalesce(match):
            col_name = match.group(1)
            default = match.group(2)
            value = self.get_column_value(row, col_name)

            if value is None or (isinstance(value, float) and np.isnan(value)):
                return default

            if coerce_numeric:
                numeric = pd.to_numeric(value, errors="coerce")
                if pd.isna(numeric):
                    return default
                return str(float(numeric))

            return str(value)

        return re.sub(coalesce_pattern, replace_coalesce, expr)


class CurrencyConvertTransformer(BaseTransformer):
    """Converts currency amounts using configured rates."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.currency:
            return None

        config = mapping.currency
        source_value = self.get_column_value(row, config.source_column)

        if source_value is None:
            return None

        # Clean and convert to numeric
        if isinstance(source_value, str):
            source_value = re.sub(r"[\$,\s]", "", source_value)

        amount = pd.to_numeric(source_value, errors="coerce")
        if pd.isna(amount):
            self.context.add_warning(
                f"Could not convert amount to numeric",
                column=config.source_column,
                row_index=row_index,
                original_value=source_value,
            )
            return None

        # Get target country for rate lookup
        target_country = self.get_column_value(row, config.target_currency_column)
        if not target_country:
            return amount  # No conversion if no target country

        # Normalize country name
        target_country = self._normalize_country(target_country)

        # Get conversion rate
        rates = self.resolve_ref(config.rates_ref)
        if isinstance(rates, dict):
            rate = rates.get(target_country)
            if rate:
                return amount * rate

        return amount

    def _normalize_country(self, value: Any) -> str:
        """Normalize country name/code."""
        value_str = str(value).upper().strip()
        country_map = {
            "AE": "United Arab Emirates",
            "UAE": "United Arab Emirates",
            "SA": "Saudi Arabia",
            "KSA": "Saudi Arabia",
            "KW": "Kuwait",
            "BH": "Bahrain",
        }
        return country_map.get(value_str, str(value))


class TaxExcludeTransformer(BaseTransformer):
    """Calculates amount excluding tax."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.tax:
            return None

        config = mapping.tax
        strategy = config.strategy

        if strategy == TaxStrategy.SUBTRACT:
            return self._subtract_tax(row, config, row_index)
        elif strategy == TaxStrategy.DIVIDE:
            return self._divide_by_divisor(row, config, row_index)
        elif strategy == TaxStrategy.PRE_CALCULATED:
            return self._get_pre_calculated(row, config, row_index)

        return None

    def _subtract_tax(self, row: pd.Series, config, row_index: int) -> Any:
        """Calculate: total - tax."""
        total = self.get_column_value(row, config.amount_column)
        tax = self.get_column_value(row, config.tax_column, 0)

        total = pd.to_numeric(total, errors="coerce")
        tax = pd.to_numeric(tax, errors="coerce")

        if pd.isna(total):
            return None

        if pd.isna(tax):
            tax = 0

        return total - tax

    def _divide_by_divisor(self, row: pd.Series, config, row_index: int) -> Any:
        """Calculate: total / divisor."""
        total = self.get_column_value(row, config.amount_column)
        total = pd.to_numeric(total, errors="coerce")

        if pd.isna(total):
            return None

        # Get divisor based on country
        country = self.get_column_value(row, config.divisor_lookup_column)
        if not country:
            return total

        # Normalize country
        country = self._normalize_country(country)

        # Get divisor
        divisors = self.resolve_ref(config.divisors_ref)
        if isinstance(divisors, dict):
            divisor = divisors.get(country, 1.0)
            if divisor and divisor != 0:
                return total / divisor

        return total

    def _get_pre_calculated(self, row: pd.Series, config, row_index: int) -> Any:
        """Get pre-calculated value from column."""
        value = self.get_column_value(row, config.pre_tax_column)
        return pd.to_numeric(value, errors="coerce")

    def _normalize_country(self, value: Any) -> str:
        """Normalize country name/code."""
        value_str = str(value).upper().strip()
        country_map = {
            "AE": "United Arab Emirates",
            "UAE": "United Arab Emirates",
            "SA": "Saudi Arabia",
            "KSA": "Saudi Arabia",
            "KW": "Kuwait",
            "BH": "Bahrain",
        }
        return country_map.get(value_str, str(value))


class CleanTransformer(BaseTransformer):
    """Cleans values using regex pattern."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.clean:
            return None

        config = mapping.clean
        value = self.get_column_value(row, config.source_column)

        if value is None:
            return None

        try:
            cleaned = re.sub(config.pattern, config.replacement, str(value))
            return cleaned
        except Exception as e:
            self.context.add_warning(
                f"Clean operation failed: {e}",
                column=config.source_column,
                row_index=row_index,
                original_value=value,
            )
            return value


class ConditionalTransformer(BaseTransformer):
    """Returns value based on conditions."""

    def transform(self, row: pd.Series, mapping: FieldMapping, row_index: int) -> Any:
        if not mapping.conditional:
            return None

        config = mapping.conditional
        source_value = self.get_column_value(row, config.source_column)

        for branch in config.conditions:
            if self._evaluate_condition(branch.when, source_value, row):
                return branch.then

        return config.else_value

    def _evaluate_condition(self, condition: str, source_value: Any, row: pd.Series) -> bool:
        """Evaluate a condition expression."""
        # Simple condition parsing: "column == 'value'" or "column.startswith('prefix')"
        try:
            # Handle startswith
            if ".startswith(" in condition:
                match = re.match(r"(\w+)\.startswith\(['\"](.+)['\"]\)", condition)
                if match:
                    col = match.group(1)
                    prefix = match.group(2)
                    value = self.get_column_value(row, col, "")
                    return str(value).upper().startswith(prefix.upper())

            # Handle equals
            if "==" in condition:
                parts = condition.split("==")
                if len(parts) == 2:
                    col = parts[0].strip()
                    expected = parts[1].strip().strip("'\"")
                    value = self.get_column_value(row, col, "")
                    return str(value).upper() == expected.upper()

        except Exception:
            pass

        return False
