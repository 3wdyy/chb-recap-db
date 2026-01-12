"""
Pipeline execution engine.

Orchestrates the execution of processing pipelines defined in brand configs.
Handles step execution, error recovery, and result aggregation.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Callable

import pandas as pd

from .config_models import (
    AggregateConfig,
    BrandConfig,
    FilterConfig,
    GlobalConfig,
    PipelineStep,
    TransformConfig,
)
from .processing_context import (
    ErrorSeverity,
    ProcessingContext,
    ProcessingResult,
    StepResult,
)

if TYPE_CHECKING:
    from ..steps.base_step import BaseStep


class PipelineEngine:
    """
    Executes processing pipelines for brand configurations.

    The engine:
    1. Creates a processing context
    2. Executes each pipeline step in order
    3. Tracks errors and warnings
    4. Returns a comprehensive result
    """

    def __init__(self, global_config: GlobalConfig):
        """
        Initialize the pipeline engine.

        Args:
            global_config: Global configuration
        """
        self.global_config = global_config
        self._step_executors: dict[str, type[BaseStep]] = {}
        self._register_default_steps()

    def _register_default_steps(self) -> None:
        """Register built-in step executors."""
        # Import here to avoid circular imports
        from ..steps.aggregate_step import AggregateStep
        from ..steps.filter_step import FilterStep
        from ..steps.transform_step import TransformStep
        from ..steps.validate_step import ValidateStep

        self._step_executors = {
            "filter": FilterStep,
            "aggregate": AggregateStep,
            "transform": TransformStep,
            "validate": ValidateStep,
        }

    def register_step(self, step_name: str, step_class: type[BaseStep]) -> None:
        """Register a custom step executor."""
        self._step_executors[step_name] = step_class

    def process(
        self,
        df: pd.DataFrame,
        brand_config: BrandConfig,
        source_file: str | None = None,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> tuple[pd.DataFrame | None, ProcessingResult]:
        """
        Process a DataFrame through the brand's pipeline.

        Args:
            df: Input DataFrame
            brand_config: Brand configuration
            source_file: Source filename for tracking
            progress_callback: Optional callback(step_name, current, total)

        Returns:
            Tuple of (output DataFrame or None, ProcessingResult)
        """
        started_at = datetime.now()
        input_rows = len(df)

        # Create processing context
        context = ProcessingContext(
            global_config=self.global_config,
            brand_config=brand_config,
            source_file=source_file,
        )

        # Validate input schema
        schema_errors = self._validate_schema(df, brand_config, context)
        if schema_errors:
            return None, context.get_result(
                input_rows=input_rows,
                output_rows=0,
                success=False,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        # Execute pipeline steps
        current_df = df.copy()
        total_steps = len(brand_config.pipeline)

        for i, step_config in enumerate(brand_config.pipeline):
            step_name = step_config.step
            context.current_step = step_name

            if progress_callback:
                progress_callback(step_name, i + 1, total_steps)

            # Get step executor
            executor_class = self._step_executors.get(step_name)
            if not executor_class:
                context.add_error(
                    f"Unknown step type: {step_name}",
                    severity=ErrorSeverity.CRITICAL,
                )
                return None, context.get_result(
                    input_rows=input_rows,
                    output_rows=0,
                    success=False,
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            # Execute step
            step_start = time.time()
            executor = executor_class(context)

            try:
                result_df = executor.execute(current_df, step_config.config)
            except Exception as e:
                context.add_error(
                    f"Step '{step_name}' failed: {str(e)}",
                    severity=ErrorSeverity.CRITICAL,
                )
                return None, context.get_result(
                    input_rows=input_rows,
                    output_rows=0,
                    success=False,
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            step_duration = (time.time() - step_start) * 1000

            # Record step result
            step_result = StepResult(
                step_name=step_name,
                input_rows=len(current_df),
                output_rows=len(result_df) if result_df is not None else 0,
                filtered_rows=len(current_df) - len(result_df) if result_df is not None else 0,
                duration_ms=step_duration,
            )
            context.add_step_result(step_result)

            if result_df is None or len(result_df) == 0:
                context.add_warning(
                    f"Step '{step_name}' produced no output rows"
                )
                return None, context.get_result(
                    input_rows=input_rows,
                    output_rows=0,
                    success=True,  # Empty result is not a failure
                    started_at=started_at,
                    completed_at=datetime.now(),
                )

            current_df = result_df

        # Ensure output columns are in correct order
        output_df = self._order_output_columns(current_df, brand_config, context)

        return output_df, context.get_result(
            input_rows=input_rows,
            output_rows=len(output_df) if output_df is not None else 0,
            success=True,
            started_at=started_at,
            completed_at=datetime.now(),
        )

    def _validate_schema(
        self,
        df: pd.DataFrame,
        brand_config: BrandConfig,
        context: ProcessingContext,
    ) -> list[str]:
        """
        Validate DataFrame against expected input schema.

        Returns list of error messages (empty if valid).
        """
        errors = []
        schema = brand_config.input_schema

        # Check required columns
        for col in schema.required_columns:
            if col not in df.columns:
                error_msg = f"Missing required column: {col}"
                errors.append(error_msg)
                context.add_error(error_msg, severity=ErrorSeverity.CRITICAL)

        # Warn about optional columns
        for col in schema.optional_columns:
            if col not in df.columns:
                context.add_warning(f"Optional column not found: {col}")

        return errors

    def _order_output_columns(
        self,
        df: pd.DataFrame,
        brand_config: BrandConfig,
        context: ProcessingContext,
    ) -> pd.DataFrame | None:
        """Ensure output columns are in the correct order."""
        output_columns = brand_config.output_columns

        # Check all required output columns exist
        missing = [col for col in output_columns if col not in df.columns]
        if missing:
            context.add_error(
                f"Missing output columns: {missing}",
                severity=ErrorSeverity.ERROR,
            )
            # Add missing columns with None values
            for col in missing:
                df[col] = None

        # Select and order columns
        try:
            return df[output_columns].copy()
        except KeyError as e:
            context.add_error(
                f"Failed to order output columns: {e}",
                severity=ErrorSeverity.ERROR,
            )
            return df

    def validate_brand_config(self, brand_config: BrandConfig) -> list[str]:
        """
        Validate a brand configuration without processing.

        Returns list of validation errors.
        """
        errors = []

        # Check pipeline has at least a transform step
        has_transform = any(s.step == "transform" for s in brand_config.pipeline)
        if not has_transform:
            errors.append("Pipeline must have at least one 'transform' step")

        # Validate each step config
        for i, step in enumerate(brand_config.pipeline):
            step_errors = self._validate_step_config(step, i)
            errors.extend(step_errors)

        return errors

    def _validate_step_config(self, step: PipelineStep, index: int) -> list[str]:
        """Validate a single step configuration."""
        errors = []
        prefix = f"Step {index + 1} ({step.step})"

        if step.step == "filter":
            if isinstance(step.config, FilterConfig):
                if not step.config.conditions:
                    errors.append(f"{prefix}: No filter conditions defined")
            else:
                errors.append(f"{prefix}: Invalid filter config type")

        elif step.step == "aggregate":
            if isinstance(step.config, AggregateConfig):
                if not step.config.group_by:
                    errors.append(f"{prefix}: No group_by column defined")
                if not step.config.aggregations:
                    errors.append(f"{prefix}: No aggregations defined")
            else:
                errors.append(f"{prefix}: Invalid aggregate config type")

        elif step.step == "transform":
            if isinstance(step.config, TransformConfig):
                if not step.config.mappings:
                    errors.append(f"{prefix}: No field mappings defined")
            else:
                errors.append(f"{prefix}: Invalid transform config type")

        return errors
