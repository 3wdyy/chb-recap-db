"""
Pydantic models for configuration schema.

These models define the complete configuration structure for:
- Global settings (conversion rates, tax divisors, country codes)
- Brand-specific processing pipelines
- Field transformations and mappings
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# ENUMS
# =============================================================================


class FilterOperator(str, Enum):
    """Supported filter operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class AggregateFunction(str, Enum):
    """Supported aggregation functions."""

    SUM = "sum"
    MAX = "max"
    MIN = "min"
    MEAN = "mean"
    FIRST = "first"
    LAST = "last"
    FIRST_NON_NULL = "first_non_null"
    COUNT = "count"
    CONCAT = "concat"


class TransformType(str, Enum):
    """Types of field transformations."""

    STATIC = "static"
    DIRECT = "direct"
    LOOKUP = "lookup"
    DATE = "date"
    PHONE = "phone"
    FORMULA = "formula"
    CURRENCY_CONVERT = "currency_convert"
    TAX_EXCLUDE = "tax_exclude"
    CLEAN = "clean"
    CONDITIONAL = "conditional"


class LookupStrategy(str, Enum):
    """Strategies for lookup-based transformations."""

    DIRECT_MAP = "direct_map"
    COUNTRY_MAP = "country_map"
    CURRENCY_MAP = "currency_map"
    ORDER_PREFIX = "order_prefix"


class TaxStrategy(str, Enum):
    """Strategies for tax calculation."""

    SUBTRACT = "subtract"
    DIVIDE = "divide"
    PRE_CALCULATED = "pre_calculated"


class DataTransform(str, Enum):
    """Simple data transformations."""

    TO_STRING = "to_string"
    TO_NUMERIC = "to_numeric"
    TO_UPPER = "to_upper"
    TO_LOWER = "to_lower"
    STRIP = "strip"


# =============================================================================
# GLOBAL CONFIG MODELS
# =============================================================================


class PhoneCodeConfig(BaseModel):
    """Configuration for phone country code mapping."""

    patterns: list[str] = Field(
        ..., description="Country name/code patterns that match this code"
    )
    code: str = Field(..., description="Phone country code (e.g., +971)")
    digits_to_keep: int = Field(
        default=9, description="Number of digits to keep from phone number"
    )


class OutputConfig(BaseModel):
    """Output file configuration."""

    delimiter: str = Field(default="|", description="Field delimiter")
    include_header: bool = Field(default=False, description="Include header row")
    include_index: bool = Field(default=False, description="Include row index")
    date_format: str = Field(
        default="%Y-%m-%dT%H:%M", description="Output date format"
    )
    encoding: str = Field(default="utf-8", description="File encoding")
    filename_template: str = Field(
        default="{brand} - {period}.csv",
        description="Output filename template",
    )


class GlobalConfig(BaseModel):
    """
    Global configuration shared across all brands.

    Contains conversion rates, tax divisors, country codes, and output settings.
    """

    version: str = Field(default="1.0", description="Config schema version")

    conversion_rates: dict[str, float] = Field(
        default_factory=lambda: {
            "United Arab Emirates": 3.67,
            "Saudi Arabia": 3.75,
            "Kuwait": 0.3058,
        },
        description="USD to local currency conversion rates",
    )

    tax_divisors: dict[str, float] = Field(
        default_factory=lambda: {
            "United Arab Emirates": 1.05,
            "Saudi Arabia": 1.15,
            "Kuwait": 1.00,
        },
        description="Tax divisors for back-calculating pre-tax amounts",
    )

    country_phone_codes: list[PhoneCodeConfig] = Field(
        default_factory=lambda: [
            PhoneCodeConfig(
                patterns=["AE", "United Arab Emirates", "UAE"],
                code="+971",
                digits_to_keep=9,
            ),
            PhoneCodeConfig(
                patterns=["SA", "Saudi Arabia", "KSA"],
                code="+966",
                digits_to_keep=9,
            ),
            PhoneCodeConfig(
                patterns=["KW", "Kuwait"],
                code="+965",
                digits_to_keep=9,
            ),
            PhoneCodeConfig(
                patterns=["BH", "Bahrain"],
                code="+973",
                digits_to_keep=9,
            ),
        ],
        description="Phone country code mappings",
    )

    supported_countries: list[str] = Field(
        default_factory=lambda: [
            "United Arab Emirates",
            "Saudi Arabia",
            "Kuwait",
        ],
        description="Countries supported for processing",
    )

    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output file settings",
    )

    def get_phone_code(self, country: str) -> tuple[str, int] | None:
        """Get phone code and digits to keep for a country."""
        country_upper = str(country).upper().strip()
        for config in self.country_phone_codes:
            for pattern in config.patterns:
                if pattern.upper() == country_upper:
                    return config.code, config.digits_to_keep
        return None

    def get_conversion_rate(self, country: str) -> float | None:
        """Get conversion rate for a country."""
        return self.conversion_rates.get(country)

    def get_tax_divisor(self, country: str) -> float | None:
        """Get tax divisor for a country."""
        return self.tax_divisors.get(country)


# =============================================================================
# FILTER CONFIG
# =============================================================================


class FilterCondition(BaseModel):
    """Single filter condition."""

    column: str = Field(..., description="Column to filter on")
    operator: FilterOperator = Field(
        default=FilterOperator.EQUALS, description="Filter operator"
    )
    value: Any = Field(default=None, description="Value to compare against")
    case_sensitive: bool = Field(default=False, description="Case-sensitive comparison")
    skip_if_column_missing: bool = Field(
        default=False, description="Skip filter if column doesn't exist"
    )

    @field_validator("value", mode="before")
    @classmethod
    def parse_value(cls, v: Any) -> Any:
        """Parse special value references."""
        if isinstance(v, str) and v.startswith("$ref:"):
            # Reference to global config - handled at runtime
            return v
        return v


class FilterConfig(BaseModel):
    """Configuration for filter pipeline step."""

    mode: Literal["all_of", "any_of"] = Field(
        default="all_of", description="How to combine multiple conditions"
    )
    conditions: list[FilterCondition] = Field(
        default_factory=list, description="Filter conditions"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_single_condition(cls, data: Any) -> Any:
        """Allow shorthand for single condition."""
        if isinstance(data, dict) and "column" in data and "conditions" not in data:
            # Single condition shorthand
            return {"conditions": [data]}
        return data


# =============================================================================
# AGGREGATE CONFIG
# =============================================================================


class AggregationRule(BaseModel):
    """Rule for aggregating a single field."""

    source: str = Field(..., description="Source column name")
    function: AggregateFunction = Field(..., description="Aggregation function")
    coerce_numeric: bool = Field(
        default=False, description="Coerce to numeric before aggregating"
    )
    separator: str = Field(
        default=", ", description="Separator for concat function"
    )


class AggregateConfig(BaseModel):
    """Configuration for aggregate pipeline step."""

    group_by: str = Field(..., description="Column to group by")
    aggregations: dict[str, AggregationRule] = Field(
        ..., description="Output field name -> aggregation rule"
    )


# =============================================================================
# TRANSFORM CONFIG
# =============================================================================


class LookupConfig(BaseModel):
    """Configuration for lookup-based transformation."""

    strategy: LookupStrategy = Field(..., description="Lookup strategy")
    source_column: str = Field(..., description="Column to use for lookup")
    mapping: dict[str, Any] = Field(..., description="Lookup mapping")
    default: Any = Field(default=None, description="Default value if no match")
    prefix_length: int | None = Field(
        default=None, description="For order_prefix strategy"
    )


class DateConfig(BaseModel):
    """Configuration for date transformation."""

    source_column: str = Field(..., description="Source date column")
    input_format: str = Field(
        default="auto", description="Input date format (or 'auto')"
    )
    output_format: str = Field(
        default="%Y-%m-%dT%H:%M", description="Output date format"
    )


class PhoneConfig(BaseModel):
    """Configuration for phone formatting."""

    country_column: str = Field(..., description="Column containing country")
    phone_column: str = Field(..., description="Column containing phone number")


class FormulaConfig(BaseModel):
    """Configuration for formula-based transformation."""

    expression: str = Field(
        ..., description="Formula expression with {column} placeholders"
    )
    coerce_numeric: bool = Field(
        default=True, description="Coerce referenced columns to numeric"
    )


class CurrencyConvertConfig(BaseModel):
    """Configuration for currency conversion."""

    source_column: str = Field(..., description="Source amount column")
    source_currency: str = Field(default="USD", description="Source currency")
    target_currency_column: str = Field(
        ..., description="Column to determine target currency"
    )
    rates_ref: str = Field(
        default="$ref:global.conversion_rates",
        description="Reference to conversion rates",
    )


class TaxExcludeConfig(BaseModel):
    """Configuration for tax exclusion calculation."""

    strategy: TaxStrategy = Field(..., description="Tax calculation strategy")
    amount_column: str = Field(
        ..., description="Column containing amount (with tax)"
    )
    tax_column: str | None = Field(
        default=None, description="Column containing tax amount (for subtract)"
    )
    pre_tax_column: str | None = Field(
        default=None, description="Column containing pre-tax amount (for pre_calculated)"
    )
    divisor_lookup_column: str | None = Field(
        default=None, description="Column for divisor lookup (for divide)"
    )
    divisors_ref: str = Field(
        default="$ref:global.tax_divisors",
        description="Reference to tax divisors",
    )


class CleanConfig(BaseModel):
    """Configuration for regex-based cleaning."""

    source_column: str = Field(..., description="Source column to clean")
    pattern: str = Field(..., description="Regex pattern to match")
    replacement: str = Field(default="", description="Replacement string")


class ConditionalBranch(BaseModel):
    """Single branch in conditional transformation."""

    when: str = Field(..., description="Condition expression")
    then: Any = Field(..., description="Value if condition is true")


class ConditionalConfig(BaseModel):
    """Configuration for conditional transformation."""

    source_column: str = Field(..., description="Primary source column")
    conditions: list[ConditionalBranch] = Field(..., description="Condition branches")
    else_value: Any = Field(default=None, description="Default value if no match")


class FieldMapping(BaseModel):
    """
    Configuration for a single output field mapping.

    This is the core unit of transformation - defines how to derive
    an output field from input data.
    """

    type: TransformType = Field(..., description="Transformation type")

    # Static
    value: Any = Field(default=None, description="Static value")

    # Direct
    source_column: str | None = Field(default=None, description="Source column")
    transform: DataTransform | None = Field(
        default=None, description="Simple transformation to apply"
    )

    # Lookup
    lookup: LookupConfig | None = Field(default=None, description="Lookup config")

    # Date
    date: DateConfig | None = Field(default=None, description="Date config")

    # Phone
    phone: PhoneConfig | None = Field(default=None, description="Phone config")

    # Formula
    formula: FormulaConfig | None = Field(default=None, description="Formula config")

    # Currency conversion
    currency: CurrencyConvertConfig | None = Field(
        default=None, description="Currency conversion config"
    )

    # Tax exclusion
    tax: TaxExcludeConfig | None = Field(default=None, description="Tax config")

    # Clean
    clean: CleanConfig | None = Field(default=None, description="Clean config")

    # Conditional
    conditional: ConditionalConfig | None = Field(
        default=None, description="Conditional config"
    )

    @model_validator(mode="after")
    def validate_type_config(self) -> "FieldMapping":
        """Ensure the correct config is provided for the type."""
        type_config_map = {
            TransformType.STATIC: "value",
            TransformType.DIRECT: "source_column",
            TransformType.LOOKUP: "lookup",
            TransformType.DATE: "date",
            TransformType.PHONE: "phone",
            TransformType.FORMULA: "formula",
            TransformType.CURRENCY_CONVERT: "currency",
            TransformType.TAX_EXCLUDE: "tax",
            TransformType.CLEAN: "clean",
            TransformType.CONDITIONAL: "conditional",
        }

        required_field = type_config_map.get(self.type)
        if required_field:
            val = getattr(self, required_field, None)
            if val is None and self.type != TransformType.STATIC:
                # Static can have None value
                if self.type == TransformType.DIRECT and self.source_column is None:
                    raise ValueError(
                        f"Transform type '{self.type}' requires '{required_field}'"
                    )
        return self


class TransformConfig(BaseModel):
    """Configuration for transform pipeline step."""

    mappings: dict[str, FieldMapping] = Field(
        ..., description="Output field name -> mapping config"
    )


# =============================================================================
# BRAND CONFIG
# =============================================================================


class InputSchema(BaseModel):
    """Expected input schema for a brand."""

    platform: str = Field(
        default="custom", description="Platform type (shopify, salesforce, custom)"
    )
    required_columns: list[str] = Field(
        default_factory=list, description="Required column names"
    )
    optional_columns: list[str] = Field(
        default_factory=list, description="Optional column names"
    )


class PipelineStep(BaseModel):
    """A single step in the processing pipeline."""

    step: Literal["filter", "aggregate", "transform", "validate"] = Field(
        ..., description="Step type"
    )
    config: FilterConfig | AggregateConfig | TransformConfig | dict = Field(
        ..., description="Step configuration"
    )

    @model_validator(mode="after")
    def parse_config(self) -> "PipelineStep":
        """Parse config into correct type based on step."""
        if isinstance(self.config, dict):
            if self.step == "filter":
                self.config = FilterConfig(**self.config)
            elif self.step == "aggregate":
                self.config = AggregateConfig(**self.config)
            elif self.step == "transform":
                self.config = TransformConfig(**self.config)
        return self


class BrandInfo(BaseModel):
    """Basic brand information."""

    name: str = Field(..., description="Brand name")
    enabled: bool = Field(default=True, description="Whether brand is enabled")
    description: str = Field(default="", description="Brand description")


class BrandConfig(BaseModel):
    """
    Complete configuration for a single brand.

    Defines input schema, processing pipeline, and output settings.
    """

    brand: BrandInfo = Field(..., description="Brand information")
    input_schema: InputSchema = Field(
        default_factory=InputSchema, description="Expected input schema"
    )
    pipeline: list[PipelineStep] = Field(
        default_factory=list, description="Processing pipeline steps"
    )
    output_columns: list[str] = Field(
        default_factory=lambda: [
            "Brand",
            "h_location",
            "h_bit_date",
            "h_bit_currency",
            "h_bit_source_generated_id",
            "h_mobile_number",
            "h_original_bit_amount",
            "h_bit_amount",
            "h_bit_source",
        ],
        description="Output column order",
    )

    # Filename matching patterns
    filename_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns to match filenames to this brand",
    )

    @model_validator(mode="after")
    def set_default_filename_patterns(self) -> "BrandConfig":
        """Set default filename patterns based on brand name."""
        if not self.filename_patterns:
            name = self.brand.name
            self.filename_patterns = [
                name.upper(),
                name.upper().replace(" ", "_"),
                name.upper().replace(" ", ""),
            ]
        return self
