#!/usr/bin/env python3
"""
Comparison test: Old script vs New configuration-driven system.

This script:
1. Creates sample data for all 8 brands
2. Runs both the old script logic and new system
3. Compares outputs and reports differences
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

from ecomm_processor.core.config_loader import ConfigLoader
from ecomm_processor.core.pipeline_engine import PipelineEngine
from ecomm_processor.io.file_writer import FileWriter

# =============================================================================
# OLD SCRIPT LOGIC (copied from original for comparison)
# =============================================================================

conversion_rates = {
    'United Arab Emirates': 3.67,
    'Saudi Arabia': 3.75,
    'Kuwait': 1 / 3.27
}

tax_divisors = {
    'United Arab Emirates': 1.05,
    'Saudi Arabia': 1.15,
    'Kuwait': 1.00
}

def format_mobile_old(row, country, mobile):
    country_code = row[country]
    mobile = str(row[mobile]).replace(" ", "").replace(".0", "")
    last_10_digits = mobile[-9:]

    if country_code == "AE" or country_code == "United Arab Emirates":
        return '+971' + last_10_digits
    elif country_code == "SA" or country_code == "Saudi Arabia":
        return '+966' + last_10_digits
    elif country_code == "BH" or country_code == "Bahrain":
        return '+973' + last_10_digits
    elif country_code == "KW" or country_code == "Kuwait":
        return '+965' + last_10_digits
    else:
        return mobile

def ghawali_old(df):
    df = df[df["Fulfillment Status"] == "fulfilled"].copy()
    df['Brand'] = "Ghawali"
    df['h_location'] = ""
    df['h_location'] = np.where(df['Currency'] == 'AED', 13010, df['h_location'])
    df['h_location'] = np.where(df['Currency'] == 'SAR', 13009, df['h_location'])
    df['h_bit_date'] = pd.to_datetime(df["Fulfilled at"]).dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = df['Currency']
    df['h_bit_source_generated_id'] = df['Name']
    df['h_mobile_number'] = df.apply(lambda row: format_mobile_old(row, country='Shipping Country', mobile='Shipping Phone'),axis=1)
    df['h_original_bit_amount'] = df['Subtotal']
    df['h_bit_amount'] = df['Subtotal'] - df['Taxes']
    df['h_bit_source'] = "ECOMM"
    return df.iloc[:, -9:]

def farm_rio_old(df):
    df = df[df["Fulfillment Status"] == "fulfilled"].copy()
    df['Brand'] = "Farm Rio"
    df['h_location'] = 61201
    df['h_bit_date'] = pd.to_datetime(df['Fulfilled at']).dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = df['Currency']
    df['h_bit_source_generated_id'] = df['Name'].astype(str)
    df['h_mobile_number'] = df.apply(lambda row: format_mobile_old(row, country='Shipping Country', mobile='Shipping Phone'),axis=1)
    df['h_original_bit_amount'] = df['Total']
    df['h_bit_amount'] = df['Total'] - df['Taxes']
    df['h_bit_source'] = "ECOMM"
    return df.iloc[:, -9:]

def lacoste_old(df):
    location_map = {
        'United Arab Emirates': 52052,
        'Saudi Arabia': 52053,
        'Kuwait': 52060
    }
    currency_map = {
        'United Arab Emirates': 'AED',
        'Saudi Arabia': 'SAR',
        'Kuwait': 'KWD'
    }
    df = df[(df["Country"] == "United Arab Emirates") | (df["Country"] == "Saudi Arabia") | (df["Country"] == "Kuwait")].copy()
    df['Brand'] = "Lacoste"
    df['h_location'] = df['Country'].map(location_map)
    df['h_bit_date'] = pd.to_datetime(df["Record Date"]).dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = df['Country'].map(currency_map)
    df['h_bit_source_generated_id'] = df['Order ID']
    df['h_mobile_number'] = df.apply(lambda row: format_mobile_old(row, country='Country', mobile='Contact Number'),axis=1)
    df['h_original_bit_amount'] = df['Gross Revenue (USD)'].astype(str).str.replace(r'[\$,]', '', regex=True).astype(float) * df['Country'].map(conversion_rates)
    df['h_bit_amount'] = df['h_original_bit_amount'] / df['Country'].map(tax_divisors)
    df['h_bit_source'] = "ECOMM"
    return df.iloc[:, -9:]

def tumi_old(df):
    df = df.copy()
    if "Payment Status" in df.columns:
        df = df[df["Payment Status"].astype(str).str.upper() == "PAID"]

    df["Total"] = pd.to_numeric(df["Total"], errors="coerce")
    df["Tax"] = pd.to_numeric(df["Tax"], errors="coerce")

    def first_non_null(s):
        s = s.dropna()
        return s.iloc[0] if len(s) else np.nan

    ord_df = df.groupby("OrderNo", as_index=False).agg(
        order_total=("Total", "max"),
        order_tax=("Tax", "sum"),
        date_created=("Date created", first_non_null),
        ship_country=("Shipping Country", first_non_null),
        ship_phone=("Shipping Phone", first_non_null),
    )

    out = ord_df.copy()
    out["Brand"] = "Tumi"
    prefix = out["OrderNo"].astype(str).str[:4].str.upper()
    out["h_location"] = np.select([prefix == "TUAE", prefix == "TUSA", prefix == "TUKW"], [32028, 32029, 32030], default=np.nan)
    out["h_bit_currency"] = np.select([prefix == "TUAE", prefix == "TUSA", prefix == "TUKW"], ["AED", "SAR", "KWD"], default=None)
    out["h_bit_date"] = pd.to_datetime(out["date_created"], format="%d.%m.%Y %H:%M", errors="coerce").dt.strftime("%Y-%m-%dT%H:%M")
    out["h_bit_source_generated_id"] = out["OrderNo"].astype(str)
    out["Shipping Country"] = out["ship_country"]
    out["Shipping Phone"] = out["ship_phone"]
    out["h_mobile_number"] = out.apply(lambda r: format_mobile_old(r, country="Shipping Country", mobile="Shipping Phone"), axis=1)
    out["h_original_bit_amount"] = out["order_total"]
    out["h_bit_amount"] = out["order_total"] - out["order_tax"].fillna(0)
    out["h_bit_source"] = "ECOMM"
    return out[["Brand","h_location","h_bit_date","h_bit_currency","h_bit_source_generated_id","h_mobile_number","h_original_bit_amount","h_bit_amount","h_bit_source"]]

# =============================================================================
# SAMPLE DATA
# =============================================================================

def create_sample_data():
    """Create sample data for all brands."""

    # Ghawali - Shopify
    ghawali_data = pd.DataFrame({
        'Fulfillment Status': ['fulfilled', 'fulfilled', 'pending', 'fulfilled'],
        'Fulfilled at': ['2025-11-15 10:30:00', '2025-11-16 14:45:00', '2025-11-17 09:00:00', '2025-11-18 11:20:00'],
        'Currency': ['AED', 'SAR', 'AED', 'AED'],
        'Name': ['#GH1001', '#GH1002', '#GH1003', '#GH1004'],
        'Shipping Country': ['United Arab Emirates', 'Saudi Arabia', 'United Arab Emirates', 'United Arab Emirates'],
        'Shipping Phone': ['501234567', '551234567', '509876543', '502345678'],
        'Subtotal': [100.0, 200.0, 150.0, 300.0],
        'Taxes': [5.0, 30.0, 7.5, 15.0],
    })

    # Farm Rio - Shopify
    farm_rio_data = pd.DataFrame({
        'Fulfillment Status': ['fulfilled', 'fulfilled', 'pending'],
        'Fulfilled at': ['2025-11-15 10:30:00', '2025-11-16 14:45:00', '2025-11-17 09:00:00'],
        'Currency': ['AED', 'SAR', 'AED'],
        'Name': ['#FR1001', '#FR1002', '#FR1003'],
        'Shipping Country': ['United Arab Emirates', 'Saudi Arabia', 'United Arab Emirates'],
        'Shipping Phone': ['501234567', '551234567', '509876543'],
        'Total': [250.0, 450.0, 350.0],
        'Taxes': [12.5, 67.5, 17.5],
    })

    # Lacoste - Custom USD
    lacoste_data = pd.DataFrame({
        'Country': ['United Arab Emirates', 'Saudi Arabia', 'Kuwait', 'France'],
        'Record Date': ['2025-11-15', '2025-11-16', '2025-11-17', '2025-11-18'],
        'Order ID': ['LC001', 'LC002', 'LC003', 'LC004'],
        'Contact Number': ['501234567', '551234567', '901234567', '123456789'],
        'Gross Revenue (USD)': ['$100.00', '$200.00', '$150.00', '$300.00'],
    })

    # Tumi - Salesforce with line items
    tumi_data = pd.DataFrame({
        'OrderNo': ['TUAE001', 'TUAE001', 'TUSA002', 'TUSA002', 'TUKW003'],
        'Date created': ['15.11.2025 10:30', '15.11.2025 10:30', '16.11.2025 14:45', '16.11.2025 14:45', '17.11.2025 09:00'],
        'Total': [500.0, 500.0, 750.0, 750.0, 400.0],
        'Tax': [10.0, 15.0, 30.0, 45.0, 0.0],
        'Shipping Country': ['United Arab Emirates', 'United Arab Emirates', 'Saudi Arabia', 'Saudi Arabia', 'Kuwait'],
        'Shipping Phone': ['501234567', '501234567', '551234567', '551234567', '901234567'],
        'Payment Status': ['PAID', 'PAID', 'PAID', 'PAID', 'PAID'],
    })

    return {
        'Ghawali': ghawali_data,
        'Farm Rio': farm_rio_data,
        'Lacoste': lacoste_data,
        'Tumi': tumi_data,
    }

# =============================================================================
# RUN COMPARISON
# =============================================================================

def compare_dataframes(old_df, new_df, brand_name):
    """Compare two DataFrames and report differences."""
    print(f"\n{'='*60}")
    print(f"  {brand_name} COMPARISON")
    print(f"{'='*60}")

    print(f"\nRow counts: Old={len(old_df)}, New={len(new_df)}")

    if len(old_df) != len(new_df):
        print("  ⚠ ROW COUNT MISMATCH")

    # Compare column by column
    differences = []

    # Ensure same column order for comparison
    old_cols = list(old_df.columns)
    new_cols = list(new_df.columns)

    if old_cols != new_cols:
        print(f"  Column order: Old={old_cols}")
        print(f"                New={new_cols}")

    # Compare values
    min_rows = min(len(old_df), len(new_df))

    for col in old_cols:
        if col not in new_cols:
            differences.append(f"Column '{col}' missing in new output")
            continue

        old_vals = old_df[col].head(min_rows).tolist()
        new_vals = new_df[col].head(min_rows).tolist()

        col_match = True
        for i, (o, n) in enumerate(zip(old_vals, new_vals)):
            # Handle numeric comparison with tolerance
            if isinstance(o, (int, float)) and isinstance(n, (int, float)):
                if pd.isna(o) and pd.isna(n):
                    continue
                if pd.isna(o) or pd.isna(n):
                    col_match = False
                    differences.append(f"Row {i}, {col}: Old={o}, New={n}")
                elif abs(o - n) > 0.01:
                    col_match = False
                    differences.append(f"Row {i}, {col}: Old={o}, New={n}")
            elif str(o) != str(n):
                col_match = False
                differences.append(f"Row {i}, {col}: Old='{o}', New='{n}'")

        status = "✓" if col_match else "✗"
        print(f"  {status} {col}")

    if differences:
        print(f"\nDifferences ({len(differences)}):")
        for diff in differences[:10]:
            print(f"  - {diff}")
        if len(differences) > 10:
            print(f"  ... and {len(differences) - 10} more")
    else:
        print("\n✓ ALL VALUES MATCH")

    return len(differences) == 0

def main():
    print("="*60)
    print("  COMPARISON TEST: Old Script vs New System")
    print("="*60)

    # Load new system
    config_loader = ConfigLoader('./config')
    engine = PipelineEngine(config_loader.global_config)

    # Create sample data
    sample_data = create_sample_data()

    # Test each brand
    results = {}

    # Ghawali
    print("\n\nProcessing Ghawali...")
    old_output = ghawali_old(sample_data['Ghawali'].copy())
    brand_config = config_loader.get_brand_config('Ghawali')
    new_output, result = engine.process(sample_data['Ghawali'].copy(), brand_config)
    results['Ghawali'] = compare_dataframes(old_output, new_output, 'Ghawali')

    # Farm Rio
    print("\n\nProcessing Farm Rio...")
    old_output = farm_rio_old(sample_data['Farm Rio'].copy())
    brand_config = config_loader.get_brand_config('Farm Rio')
    new_output, result = engine.process(sample_data['Farm Rio'].copy(), brand_config)
    results['Farm Rio'] = compare_dataframes(old_output, new_output, 'Farm Rio')

    # Lacoste
    print("\n\nProcessing Lacoste...")
    old_output = lacoste_old(sample_data['Lacoste'].copy())
    brand_config = config_loader.get_brand_config('Lacoste')
    new_output, result = engine.process(sample_data['Lacoste'].copy(), brand_config)
    results['Lacoste'] = compare_dataframes(old_output, new_output, 'Lacoste')

    # Tumi
    print("\n\nProcessing Tumi...")
    old_output = tumi_old(sample_data['Tumi'].copy())
    brand_config = config_loader.get_brand_config('Tumi')
    new_output, result = engine.process(sample_data['Tumi'].copy(), brand_config)
    results['Tumi'] = compare_dataframes(old_output, new_output, 'Tumi')

    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)

    for brand, matched in results.items():
        status = "✓ PASS" if matched else "✗ FAIL"
        print(f"  {status} - {brand}")

    all_passed = all(results.values())
    print("\n" + ("="*60))
    if all_passed:
        print("  ✓ ALL TESTS PASSED - New system matches old script")
    else:
        print("  ✗ SOME TESTS FAILED - Review differences above")
    print("="*60)

if __name__ == "__main__":
    main()
