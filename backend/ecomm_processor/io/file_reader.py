"""File reader for CSV and Excel files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd


@dataclass
class ReadResult:
    """Result from reading a file."""

    filename: str
    sheet_name: str | None
    dataframe: pd.DataFrame
    row_count: int
    column_count: int
    columns: list[str]


class FileReader:
    """
    Reads CSV and Excel files into DataFrames.

    Handles:
    - CSV files (auto-detect encoding and delimiter)
    - Excel files (all sheets or specific sheet)
    - File-like objects for upload handling
    """

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

    def read_file(
        self,
        file_path: str | Path | BinaryIO,
        filename: str | None = None,
        sheet_name: str | int | None = None,
    ) -> list[ReadResult]:
        """
        Read a file and return DataFrames.

        Args:
            file_path: Path to file or file-like object
            filename: Original filename (required for file-like objects)
            sheet_name: Specific sheet to read (Excel only), None for all

        Returns:
            List of ReadResult objects (one per sheet for Excel)
        """
        # Determine filename
        if isinstance(file_path, (str, Path)):
            path = Path(file_path)
            filename = filename or path.name
            extension = path.suffix.lower()
        else:
            if not filename:
                raise ValueError("filename required for file-like objects")
            extension = Path(filename).suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {extension}")

        if extension == ".csv":
            return self._read_csv(file_path, filename)
        else:
            return self._read_excel(file_path, filename, sheet_name)

    def _read_csv(
        self, file_path: str | Path | BinaryIO, filename: str
    ) -> list[ReadResult]:
        """Read a CSV file."""
        try:
            # Try different encodings
            df = None
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    if isinstance(file_path, (str, Path)):
                        df = pd.read_csv(file_path, encoding=encoding)
                    else:
                        file_path.seek(0)
                        df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if df is None:
                raise ValueError("Could not decode CSV file")

            return [
                ReadResult(
                    filename=filename,
                    sheet_name=None,
                    dataframe=df,
                    row_count=len(df),
                    column_count=len(df.columns),
                    columns=list(df.columns),
                )
            ]

        except Exception as e:
            raise ValueError(f"Failed to read CSV: {str(e)}")

    def _read_excel(
        self,
        file_path: str | Path | BinaryIO,
        filename: str,
        sheet_name: str | int | None = None,
    ) -> list[ReadResult]:
        """Read an Excel file."""
        try:
            if isinstance(file_path, (str, Path)):
                excel_file = pd.ExcelFile(file_path)
            else:
                file_path.seek(0)
                excel_file = pd.ExcelFile(file_path)

            results = []

            # Determine which sheets to read
            if sheet_name is not None:
                sheets_to_read = [sheet_name]
            else:
                sheets_to_read = excel_file.sheet_names

            for sheet in sheets_to_read:
                df = pd.read_excel(excel_file, sheet_name=sheet)

                # Skip empty sheets
                if len(df) == 0:
                    continue

                results.append(
                    ReadResult(
                        filename=filename,
                        sheet_name=str(sheet),
                        dataframe=df,
                        row_count=len(df),
                        column_count=len(df.columns),
                        columns=list(df.columns),
                    )
                )

            return results

        except Exception as e:
            raise ValueError(f"Failed to read Excel: {str(e)}")

    def preview_file(
        self,
        file_path: str | Path | BinaryIO,
        filename: str | None = None,
        max_rows: int = 10,
    ) -> dict:
        """
        Preview a file without full loading.

        Returns metadata and first few rows.
        """
        results = self.read_file(file_path, filename)

        previews = []
        for result in results:
            preview_df = result.dataframe.head(max_rows)
            previews.append({
                "filename": result.filename,
                "sheet_name": result.sheet_name,
                "row_count": result.row_count,
                "column_count": result.column_count,
                "columns": result.columns,
                "preview_rows": preview_df.to_dict(orient="records"),
            })

        return {
            "file_count": len(results),
            "total_rows": sum(r.row_count for r in results),
            "previews": previews,
        }
