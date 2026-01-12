"""
Processing context and result models.

The ProcessingContext holds shared state during pipeline execution,
including the global config, current brand, and error tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config_models import BrandConfig, GlobalConfig


class ErrorSeverity(str, Enum):
    """Severity level for processing errors."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RowError:
    """Error or warning for a specific row."""

    row_index: int
    column: str | None
    message: str
    severity: ErrorSeverity
    original_value: Any = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "row_index": self.row_index,
            "column": self.column,
            "message": self.message,
            "severity": self.severity.value,
            "original_value": str(self.original_value) if self.original_value else None,
            "details": self.details,
        }


@dataclass
class StepResult:
    """Result from a single pipeline step."""

    step_name: str
    input_rows: int
    output_rows: int
    filtered_rows: int = 0
    errors: list[RowError] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "step_name": self.step_name,
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "filtered_rows": self.filtered_rows,
            "error_count": len([e for e in self.errors if e.severity == ErrorSeverity.ERROR]),
            "warning_count": len([e for e in self.errors if e.severity == ErrorSeverity.WARNING]),
            "duration_ms": self.duration_ms,
        }


@dataclass
class ProcessingResult:
    """Complete result from processing a file/brand."""

    brand_name: str
    source_file: str | None
    success: bool
    input_rows: int
    output_rows: int
    step_results: list[StepResult] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    warnings: list[RowError] = field(default_factory=list)
    quarantined_rows: list[int] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_file: str | None = None

    @property
    def duration_ms(self) -> float:
        """Total processing duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return 0.0

    @property
    def error_count(self) -> int:
        """Total error count."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Total warning count."""
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "brand_name": self.brand_name,
            "source_file": self.source_file,
            "success": self.success,
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "quarantined_count": len(self.quarantined_rows),
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output_file": self.output_file,
            "step_results": [s.to_dict() for s in self.step_results],
            "errors": [e.to_dict() for e in self.errors[:100]],  # Limit for response size
            "warnings": [w.to_dict() for w in self.warnings[:100]],
        }


class ProcessingContext:
    """
    Shared context during pipeline execution.

    Holds global config, brand config, and accumulates errors/warnings.
    Passed to all pipeline steps and transformers.
    """

    def __init__(
        self,
        global_config: GlobalConfig,
        brand_config: BrandConfig,
        source_file: str | None = None,
    ):
        self.global_config = global_config
        self.brand_config = brand_config
        self.source_file = source_file
        self.current_step: str = ""
        self.current_row: int = 0

        # Error tracking
        self._errors: list[RowError] = []
        self._warnings: list[RowError] = []
        self._quarantined_rows: set[int] = set()

        # Step results
        self._step_results: list[StepResult] = []

        # Cache for resolved references
        self._ref_cache: dict[str, Any] = {}

    def add_error(
        self,
        message: str,
        column: str | None = None,
        original_value: Any = None,
        row_index: int | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add an error or warning."""
        error = RowError(
            row_index=row_index if row_index is not None else self.current_row,
            column=column,
            message=message,
            severity=severity,
            original_value=original_value,
            details=details,
        )

        if severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL):
            self._errors.append(error)
        else:
            self._warnings.append(error)

    def add_warning(
        self,
        message: str,
        column: str | None = None,
        original_value: Any = None,
        row_index: int | None = None,
    ) -> None:
        """Convenience method to add a warning."""
        self.add_error(
            message=message,
            column=column,
            original_value=original_value,
            row_index=row_index,
            severity=ErrorSeverity.WARNING,
        )

    def quarantine_row(self, row_index: int, reason: str) -> None:
        """Mark a row as quarantined (excluded from output)."""
        self._quarantined_rows.add(row_index)
        self.add_error(
            message=f"Row quarantined: {reason}",
            row_index=row_index,
            severity=ErrorSeverity.WARNING,
        )

    def is_quarantined(self, row_index: int) -> bool:
        """Check if a row is quarantined."""
        return row_index in self._quarantined_rows

    def add_step_result(self, result: StepResult) -> None:
        """Add a step result."""
        self._step_results.append(result)

    def resolve_reference(self, ref: str) -> Any:
        """
        Resolve a $ref: reference to a value.

        Supports:
        - $ref:global.conversion_rates
        - $ref:global.tax_divisors
        - $ref:global.supported_countries
        """
        if ref in self._ref_cache:
            return self._ref_cache[ref]

        if not ref.startswith("$ref:"):
            return ref

        path = ref[5:]  # Remove "$ref:" prefix
        parts = path.split(".")

        if parts[0] == "global":
            obj: Any = self.global_config
            for part in parts[1:]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict):
                    obj = obj.get(part)
                else:
                    raise ValueError(f"Cannot resolve reference: {ref}")
            self._ref_cache[ref] = obj
            return obj

        raise ValueError(f"Unknown reference type: {ref}")

    def get_result(
        self,
        input_rows: int,
        output_rows: int,
        success: bool = True,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        output_file: str | None = None,
    ) -> ProcessingResult:
        """Build the final processing result."""
        return ProcessingResult(
            brand_name=self.brand_config.brand.name,
            source_file=self.source_file,
            success=success and len(self._errors) == 0,
            input_rows=input_rows,
            output_rows=output_rows,
            step_results=self._step_results,
            errors=self._errors,
            warnings=self._warnings,
            quarantined_rows=list(self._quarantined_rows),
            started_at=started_at,
            completed_at=completed_at,
            output_file=output_file,
        )
