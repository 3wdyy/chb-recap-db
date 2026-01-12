"""File writer for output files."""

from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..core.config_models import OutputConfig


class FileWriter:
    """
    Writes DataFrames to various output formats.

    Supports:
    - CSV with configurable delimiter
    - Excel
    - In-memory bytes for downloads
    """

    def __init__(self, output_config: OutputConfig | None = None):
        """
        Initialize the writer.

        Args:
            output_config: Output configuration (uses defaults if None)
        """
        self.config = output_config

    def write_csv(
        self,
        df: pd.DataFrame,
        output_path: str | Path,
        delimiter: str | None = None,
        include_header: bool | None = None,
        include_index: bool | None = None,
        encoding: str | None = None,
    ) -> str:
        """
        Write DataFrame to CSV file.

        Args:
            df: DataFrame to write
            output_path: Path to output file
            delimiter: Field delimiter (overrides config)
            include_header: Include header row (overrides config)
            include_index: Include index column (overrides config)
            encoding: File encoding (overrides config)

        Returns:
            Path to written file
        """
        # Apply defaults from config
        delimiter = delimiter or (self.config.delimiter if self.config else "|")
        include_header = include_header if include_header is not None else (
            self.config.include_header if self.config else False
        )
        include_index = include_index if include_index is not None else (
            self.config.include_index if self.config else False
        )
        encoding = encoding or (self.config.encoding if self.config else "utf-8")

        # Ensure parent directory exists
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        df.to_csv(
            output_path,
            sep=delimiter,
            header=include_header,
            index=include_index,
            encoding=encoding,
        )

        return str(output_path)

    def write_csv_bytes(
        self,
        df: pd.DataFrame,
        delimiter: str | None = None,
        include_header: bool | None = None,
        include_index: bool | None = None,
        encoding: str | None = None,
    ) -> bytes:
        """
        Write DataFrame to CSV bytes (for downloads).

        Returns:
            CSV content as bytes
        """
        delimiter = delimiter or (self.config.delimiter if self.config else "|")
        include_header = include_header if include_header is not None else (
            self.config.include_header if self.config else False
        )
        include_index = include_index if include_index is not None else (
            self.config.include_index if self.config else False
        )
        encoding = encoding or (self.config.encoding if self.config else "utf-8")

        buffer = StringIO()
        df.to_csv(
            buffer,
            sep=delimiter,
            header=include_header,
            index=include_index,
        )

        return buffer.getvalue().encode(encoding)

    def write_excel(
        self,
        df: pd.DataFrame,
        output_path: str | Path,
        sheet_name: str = "Sheet1",
        include_index: bool | None = None,
    ) -> str:
        """
        Write DataFrame to Excel file.

        Args:
            df: DataFrame to write
            output_path: Path to output file
            sheet_name: Name of the sheet
            include_index: Include index column

        Returns:
            Path to written file
        """
        include_index = include_index if include_index is not None else (
            self.config.include_index if self.config else False
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df.to_excel(output_path, sheet_name=sheet_name, index=include_index)

        return str(output_path)

    def write_excel_bytes(
        self,
        df: pd.DataFrame,
        sheet_name: str = "Sheet1",
        include_index: bool | None = None,
    ) -> bytes:
        """
        Write DataFrame to Excel bytes (for downloads).

        Returns:
            Excel content as bytes
        """
        include_index = include_index if include_index is not None else (
            self.config.include_index if self.config else False
        )

        buffer = BytesIO()
        df.to_excel(buffer, sheet_name=sheet_name, index=include_index)
        buffer.seek(0)

        return buffer.getvalue()

    def format_filename(
        self,
        brand_name: str,
        period: str,
        template: str | None = None,
    ) -> str:
        """
        Format output filename using template.

        Args:
            brand_name: Brand name
            period: Period string (e.g., "NOV 2025")
            template: Filename template (overrides config)

        Returns:
            Formatted filename
        """
        template = template or (
            self.config.filename_template if self.config else "{brand} - {period}.csv"
        )

        return template.format(brand=brand_name, period=period)
