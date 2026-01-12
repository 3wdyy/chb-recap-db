"""
Command-line interface for the E-Commerce Processor.

Usage:
    ecomm-processor process <input_dir> <output_dir> [--period=<period>] [--brand=<brand>]
    ecomm-processor process-file <file> [--brand=<brand>] [--output=<output>] [--period=<period>]
    ecomm-processor list-brands
    ecomm-processor validate <file> --brand=<brand>
    ecomm-processor serve [--host=<host>] [--port=<port>]

Examples:
    ecomm-processor process ./input ./output --period="NOV 2025"
    ecomm-processor process-file ghawali_orders.csv --brand=Ghawali
    ecomm-processor serve --port=8000
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import pandas as pd


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="E-Commerce Order Processor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Process directory command
    process_parser = subparsers.add_parser(
        "process", help="Process all files in a directory"
    )
    process_parser.add_argument("input_dir", help="Input directory with CSV/Excel files")
    process_parser.add_argument("output_dir", help="Output directory for processed files")
    process_parser.add_argument("--period", default="export", help="Period name for output files")
    process_parser.add_argument("--brand", help="Process only this brand")
    process_parser.add_argument("--config", help="Path to config directory")

    # Process single file command
    file_parser = subparsers.add_parser(
        "process-file", help="Process a single file"
    )
    file_parser.add_argument("file", help="Input file (CSV or Excel)")
    file_parser.add_argument("--brand", required=True, help="Brand name")
    file_parser.add_argument("--output", help="Output file path")
    file_parser.add_argument("--period", default="export", help="Period name")
    file_parser.add_argument("--config", help="Path to config directory")

    # List brands command
    list_parser = subparsers.add_parser(
        "list-brands", help="List available brands"
    )
    list_parser.add_argument("--config", help="Path to config directory")

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a file against brand schema"
    )
    validate_parser.add_argument("file", help="Input file to validate")
    validate_parser.add_argument("--brand", required=True, help="Brand name")
    validate_parser.add_argument("--config", help="Path to config directory")

    # Serve command
    serve_parser = subparsers.add_parser(
        "serve", help="Start the API server"
    )
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    serve_parser.add_argument("--config", help="Path to config directory")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "process":
        cmd_process_directory(args)
    elif args.command == "process-file":
        cmd_process_file(args)
    elif args.command == "list-brands":
        cmd_list_brands(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "serve":
        cmd_serve(args)


def cmd_process_directory(args):
    """Process all files in a directory."""
    from .core.config_loader import ConfigLoader
    from .core.pipeline_engine import PipelineEngine
    from .io.brand_detector import BrandDetector
    from .io.file_reader import FileReader
    from .io.file_writer import FileWriter

    config_dir = args.config
    config_loader = ConfigLoader(config_dir)
    global_config = config_loader.global_config

    # Load brands
    brands = config_loader.load_all_brands()
    if not brands:
        print("Error: No brand configurations found")
        sys.exit(1)

    print(f"Loaded {len(brands)} brand configurations")

    # Setup
    detector = BrandDetector(brands)
    reader = FileReader()
    writer = FileWriter(global_config.output)
    engine = PipelineEngine(global_config)

    # Find files
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = list(input_dir.glob("*.csv")) + list(input_dir.glob("*.xlsx"))
    print(f"Found {len(files)} files to process")
    print("-" * 60)

    # Process each file
    results_by_brand: dict[str, list[pd.DataFrame]] = {}

    for file_path in files:
        # Detect brand
        brand_name = detector.detect(file_path.name)

        if args.brand and brand_name != args.brand:
            continue

        if not brand_name:
            print(f"⚠ Skipping {file_path.name}: Could not detect brand")
            continue

        brand_config = brands.get(brand_name)
        if not brand_config:
            print(f"⚠ Skipping {file_path.name}: No config for brand '{brand_name}'")
            continue

        print(f"Processing {file_path.name} as {brand_name}...")

        try:
            # Read file
            read_results = reader.read_file(file_path)

            for read_result in read_results:
                # Process
                output_df, proc_result = engine.process(
                    read_result.dataframe,
                    brand_config,
                    source_file=str(file_path),
                )

                if output_df is not None and len(output_df) > 0:
                    if brand_name not in results_by_brand:
                        results_by_brand[brand_name] = []
                    results_by_brand[brand_name].append(output_df)

                    print(
                        f"  ✓ {read_result.sheet_name or 'main'}: "
                        f"{proc_result.input_rows} → {proc_result.output_rows} rows"
                    )

                    if proc_result.warning_count > 0:
                        print(f"    ({proc_result.warning_count} warnings)")
                else:
                    print(f"  ✗ No output generated")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    print("-" * 60)

    # Write output files
    for brand_name, dfs in results_by_brand.items():
        combined_df = pd.concat(dfs, ignore_index=True)

        # Remove Brand column for output
        output_df = combined_df.iloc[:, 1:] if "Brand" in combined_df.columns else combined_df

        filename = writer.format_filename(brand_name, args.period)
        output_path = output_dir / filename

        writer.write_csv(output_df, output_path)
        print(f"✓ Exported {filename} ({len(output_df)} rows)")

    print("-" * 60)
    print("Done!")


def cmd_process_file(args):
    """Process a single file."""
    from .core.config_loader import ConfigLoader
    from .core.pipeline_engine import PipelineEngine
    from .io.file_reader import FileReader
    from .io.file_writer import FileWriter

    config_loader = ConfigLoader(args.config)
    global_config = config_loader.global_config
    brand_config = config_loader.get_brand_config(args.brand)

    if not brand_config:
        print(f"Error: Brand '{args.brand}' not found")
        sys.exit(1)

    reader = FileReader()
    writer = FileWriter(global_config.output)
    engine = PipelineEngine(global_config)

    # Read file
    file_path = Path(args.file)
    read_results = reader.read_file(file_path)

    all_outputs = []
    for read_result in read_results:
        output_df, proc_result = engine.process(
            read_result.dataframe,
            brand_config,
            source_file=str(file_path),
        )

        print(f"Processed: {proc_result.input_rows} → {proc_result.output_rows} rows")

        if proc_result.error_count > 0:
            print(f"Errors: {proc_result.error_count}")
            for error in proc_result.errors[:5]:
                print(f"  - Row {error.row_index}: {error.message}")

        if proc_result.warning_count > 0:
            print(f"Warnings: {proc_result.warning_count}")

        if output_df is not None:
            all_outputs.append(output_df)

    if all_outputs:
        combined_df = pd.concat(all_outputs, ignore_index=True)
        output_df = combined_df.iloc[:, 1:] if "Brand" in combined_df.columns else combined_df

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = file_path.parent / writer.format_filename(args.brand, args.period)

        writer.write_csv(output_df, output_path)
        print(f"Output: {output_path}")
    else:
        print("No output generated")
        sys.exit(1)


def cmd_list_brands(args):
    """List available brands."""
    from .core.config_loader import ConfigLoader

    config_loader = ConfigLoader(args.config)
    brands = config_loader.load_all_brands()

    if not brands:
        print("No brand configurations found")
        return

    print(f"Available brands ({len(brands)}):")
    print("-" * 60)

    for name, config in sorted(brands.items()):
        status = "✓" if config.brand.enabled else "✗"
        print(f"  {status} {name}")
        print(f"      Platform: {config.input_schema.platform}")
        print(f"      Required columns: {len(config.input_schema.required_columns)}")
        print(f"      Pipeline steps: {len(config.pipeline)}")
        if config.brand.description:
            print(f"      Description: {config.brand.description}")
        print()


def cmd_validate(args):
    """Validate a file against brand schema."""
    from .core.config_loader import ConfigLoader
    from .io.file_reader import FileReader

    config_loader = ConfigLoader(args.config)
    brand_config = config_loader.get_brand_config(args.brand)

    if not brand_config:
        print(f"Error: Brand '{args.brand}' not found")
        sys.exit(1)

    reader = FileReader()
    file_path = Path(args.file)
    read_results = reader.read_file(file_path)

    print(f"Validating {file_path.name} against {args.brand} schema")
    print("-" * 60)

    for read_result in read_results:
        df = read_result.dataframe
        sheet = read_result.sheet_name or "main"

        print(f"\nSheet: {sheet}")
        print(f"Rows: {len(df)}")
        print(f"Columns: {len(df.columns)}")

        # Check required columns
        missing = []
        found = []
        for col in brand_config.input_schema.required_columns:
            if col in df.columns:
                found.append(col)
            else:
                missing.append(col)

        print(f"\nRequired columns ({len(found)}/{len(brand_config.input_schema.required_columns)}):")
        for col in found:
            print(f"  ✓ {col}")
        for col in missing:
            print(f"  ✗ {col} (MISSING)")

        # Check optional columns
        optional_found = [
            col for col in brand_config.input_schema.optional_columns
            if col in df.columns
        ]
        if optional_found:
            print(f"\nOptional columns found: {optional_found}")

        # Extra columns
        known_cols = set(brand_config.input_schema.required_columns + brand_config.input_schema.optional_columns)
        extra = [col for col in df.columns if col not in known_cols]
        if extra:
            print(f"\nExtra columns: {extra[:10]}{'...' if len(extra) > 10 else ''}")

        # Validation result
        if missing:
            print(f"\n✗ INVALID: Missing {len(missing)} required columns")
        else:
            print(f"\n✓ VALID: All required columns present")


def cmd_serve(args):
    """Start the API server."""
    import uvicorn
    from .api.main import create_app

    app = create_app(args.config)
    print(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
