"""
FastAPI application for the E-Commerce Processor.

Provides REST endpoints for:
- Configuration management (global and brand configs)
- File processing (upload, process, download)
- Preview and validation
"""

from __future__ import annotations

import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from ..core.config_loader import ConfigLoader
from ..core.config_models import BrandConfig, GlobalConfig
from ..core.pipeline_engine import PipelineEngine
from ..io.brand_detector import BrandDetector
from ..io.file_reader import FileReader
from ..io.file_writer import FileWriter


def create_app(config_dir: str | Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="E-Commerce Order Processor",
        description="Configuration-driven pipeline for transforming e-commerce order data",
        version="1.0.0",
    )

    # CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize services
    config_loader = ConfigLoader(config_dir)
    file_reader = FileReader()

    # Store in app state
    app.state.config_loader = config_loader
    app.state.file_reader = file_reader

    # ==========================================================================
    # HEALTH CHECK
    # ==========================================================================

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}

    # ==========================================================================
    # GLOBAL CONFIG ENDPOINTS
    # ==========================================================================

    @app.get("/api/config/global")
    async def get_global_config() -> dict:
        """Get global configuration."""
        config = config_loader.global_config
        return config.model_dump()

    @app.put("/api/config/global")
    async def update_global_config(updates: dict[str, Any]) -> dict:
        """Update global configuration."""
        try:
            new_config = config_loader.update_global_config(updates)
            return {"success": True, "config": new_config.model_dump()}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ==========================================================================
    # BRAND CONFIG ENDPOINTS
    # ==========================================================================

    @app.get("/api/config/brands")
    async def list_brands() -> dict:
        """List all available brands."""
        brands = config_loader.load_all_brands()
        return {
            "brands": [
                {
                    "name": config.brand.name,
                    "enabled": config.brand.enabled,
                    "description": config.brand.description,
                    "platform": config.input_schema.platform,
                }
                for config in brands.values()
            ]
        }

    @app.get("/api/config/brands/{brand_name}")
    async def get_brand_config(brand_name: str) -> dict:
        """Get configuration for a specific brand."""
        config = config_loader.get_brand_config(brand_name)
        if not config:
            raise HTTPException(status_code=404, detail=f"Brand '{brand_name}' not found")
        return config.model_dump()

    @app.put("/api/config/brands/{brand_name}")
    async def update_brand_config(brand_name: str, config_data: dict[str, Any]) -> dict:
        """Update configuration for a brand."""
        try:
            config = BrandConfig(**config_data)
            config_loader.save_brand_config(config)
            return {"success": True, "brand": config.brand.name}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/config/brands")
    async def create_brand(config_data: dict[str, Any]) -> dict:
        """Create a new brand configuration."""
        try:
            config = BrandConfig(**config_data)

            # Check if brand already exists
            existing = config_loader.get_brand_config(config.brand.name)
            if existing:
                raise HTTPException(
                    status_code=409, detail=f"Brand '{config.brand.name}' already exists"
                )

            config_loader.save_brand_config(config)
            return {"success": True, "brand": config.brand.name}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.delete("/api/config/brands/{brand_name}")
    async def delete_brand(brand_name: str) -> dict:
        """Delete a brand configuration."""
        if config_loader.delete_brand_config(brand_name):
            return {"success": True, "deleted": brand_name}
        raise HTTPException(status_code=404, detail=f"Brand '{brand_name}' not found")

    # ==========================================================================
    # FILE PROCESSING ENDPOINTS
    # ==========================================================================

    class ProcessRequest(BaseModel):
        """Request model for processing."""

        period: str = "export"
        brand_override: str | None = None

    @app.post("/api/process/detect-brand")
    async def detect_brand(file: UploadFile = File(...)) -> dict:
        """Detect brand from uploaded file."""
        brands = config_loader.load_all_brands()
        detector = BrandDetector(brands)

        detected = detector.detect(file.filename or "")
        return {
            "filename": file.filename,
            "detected_brand": detected,
            "available_brands": detector.list_enabled_brands(),
        }

    @app.post("/api/process/preview")
    async def preview_file(
        file: UploadFile = File(...),
        max_rows: int = Form(default=10),
    ) -> dict:
        """Preview uploaded file without processing."""
        try:
            content = await file.read()
            file_obj = BytesIO(content)

            preview = file_reader.preview_file(
                file_obj, filename=file.filename, max_rows=max_rows
            )

            # Detect brand
            brands = config_loader.load_all_brands()
            detector = BrandDetector(brands)
            detected_brand = detector.detect(file.filename or "")

            preview["detected_brand"] = detected_brand
            preview["available_brands"] = detector.list_enabled_brands()

            return preview
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/process/validate")
    async def validate_file(
        file: UploadFile = File(...),
        brand: str = Form(...),
    ) -> dict:
        """Validate file against brand schema."""
        try:
            # Get brand config
            brand_config = config_loader.get_brand_config(brand)
            if not brand_config:
                raise HTTPException(status_code=404, detail=f"Brand '{brand}' not found")

            # Read file
            content = await file.read()
            file_obj = BytesIO(content)
            results = file_reader.read_file(file_obj, filename=file.filename)

            if not results:
                return {"valid": False, "errors": ["No data found in file"]}

            # Validate schema
            df = results[0].dataframe
            errors = []
            warnings = []

            for col in brand_config.input_schema.required_columns:
                if col not in df.columns:
                    errors.append(f"Missing required column: {col}")

            for col in brand_config.input_schema.optional_columns:
                if col not in df.columns:
                    warnings.append(f"Optional column not found: {col}")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "row_count": len(df),
                "columns_found": list(df.columns),
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/process/execute")
    async def process_file(
        file: UploadFile = File(...),
        brand: str = Form(...),
        period: str = Form(default="export"),
    ) -> dict:
        """Process uploaded file and return results."""
        try:
            # Get configs
            global_config = config_loader.global_config
            brand_config = config_loader.get_brand_config(brand)
            if not brand_config:
                raise HTTPException(status_code=404, detail=f"Brand '{brand}' not found")

            # Read file
            content = await file.read()
            file_obj = BytesIO(content)
            results = file_reader.read_file(file_obj, filename=file.filename)

            if not results:
                raise HTTPException(status_code=400, detail="No data found in file")

            # Process
            engine = PipelineEngine(global_config)
            all_results = []

            for read_result in results:
                output_df, proc_result = engine.process(
                    read_result.dataframe,
                    brand_config,
                    source_file=f"{file.filename}:{read_result.sheet_name or 'main'}",
                )

                result_data = proc_result.to_dict()

                if output_df is not None and len(output_df) > 0:
                    # Generate output
                    writer = FileWriter(global_config.output)
                    output_bytes = writer.write_csv_bytes(output_df)
                    result_data["output_preview"] = output_df.head(10).to_dict(orient="records")
                    result_data["output_size_bytes"] = len(output_bytes)

                all_results.append(result_data)

            return {
                "success": all(r.get("success", False) for r in all_results),
                "results": all_results,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/process/download")
    async def process_and_download(
        file: UploadFile = File(...),
        brand: str = Form(...),
        period: str = Form(default="export"),
    ) -> Response:
        """Process file and download result."""
        try:
            # Get configs
            global_config = config_loader.global_config
            brand_config = config_loader.get_brand_config(brand)
            if not brand_config:
                raise HTTPException(status_code=404, detail=f"Brand '{brand}' not found")

            # Read and process
            content = await file.read()
            file_obj = BytesIO(content)
            results = file_reader.read_file(file_obj, filename=file.filename)

            if not results:
                raise HTTPException(status_code=400, detail="No data found in file")

            engine = PipelineEngine(global_config)
            writer = FileWriter(global_config.output)

            # Process first result
            output_df, proc_result = engine.process(
                results[0].dataframe,
                brand_config,
                source_file=file.filename,
            )

            if output_df is None or len(output_df) == 0:
                raise HTTPException(status_code=400, detail="Processing produced no output")

            # Generate output
            output_bytes = writer.write_csv_bytes(output_df)
            filename = writer.format_filename(brand_config.brand.name, period)

            return Response(
                content=output_bytes,
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/process/batch")
    async def process_batch(
        files: list[UploadFile] = File(...),
        period: str = Form(default="export"),
    ) -> dict:
        """Process multiple files at once."""
        try:
            global_config = config_loader.global_config
            brands = config_loader.load_all_brands()
            detector = BrandDetector(brands)
            engine = PipelineEngine(global_config)

            results = []
            for file in files:
                # Detect brand
                brand_name = detector.detect(file.filename or "")
                if not brand_name:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "Could not detect brand from filename",
                    })
                    continue

                brand_config = brands.get(brand_name)
                if not brand_config:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": f"Brand config not found: {brand_name}",
                    })
                    continue

                # Read and process
                try:
                    content = await file.read()
                    file_obj = BytesIO(content)
                    read_results = file_reader.read_file(file_obj, filename=file.filename)

                    for read_result in read_results:
                        output_df, proc_result = engine.process(
                            read_result.dataframe,
                            brand_config,
                            source_file=file.filename,
                        )

                        result_data = proc_result.to_dict()
                        result_data["filename"] = file.filename
                        result_data["sheet"] = read_result.sheet_name
                        results.append(result_data)
                except Exception as e:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": str(e),
                    })

            return {
                "total_files": len(files),
                "successful": sum(1 for r in results if r.get("success", False)),
                "results": results,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# Default app instance
app = create_app()
