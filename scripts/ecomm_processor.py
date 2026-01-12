import pandas as pd
import glob
import os
import numpy as np
import warnings
warnings.filterwarnings("ignore")


brands = ['Ghawali', 'Elemis', 'Lacoste', 'Farm Rio', 'Jacquemus', 'Yeda', 'Tumi', 'Axel Arigato']
# brands = ['Axel Arigato']  # Uncomment for testing single brand


directory_path = 'NOV 2025'

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

def format_mobile(row, country, mobile):
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

def farm_rio(df):
    df = df[df["Fulfillment Status"] == "fulfilled"]
    df['Brand'] = "Farm Rio"
    df['h_location'] = 61201
    df['h_bit_date'] = pd.to_datetime(df['Fulfilled at']).dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = df['Currency']
    df['h_bit_source_generated_id'] = df['Name'].astype(str)
    df['h_mobile_number'] = df.apply(lambda row: format_mobile(row, country='Shipping Country', mobile='Shipping Phone'),axis=1)
    df['h_original_bit_amount'] = df['Total']
    df['h_bit_amount'] = df['Total'] - df['Taxes']
    df['h_bit_source'] = "ECOMM"

    return df.iloc[:, -9:]

def tumi(df):
    # NEW (Salesforce) schema: one row per order-line → MUST aggregate to order level
    df = df.copy()

    # Optional safety filters (apply only if columns exist)
    if "Payment Status" in df.columns:
        df = df[df["Payment Status"].astype(str).str.upper() == "PAID"]
    if "Confirmation Status" in df.columns:
        df = df[df["Confirmation Status"].astype(str).str.upper() == "CONFIRMED"]
    if "Export Status" in df.columns:
        df = df[df["Export Status"].astype(str).str.upper() == "EXPORTED"]

    # Required columns for the Salesforce extract
    required = ["OrderNo", "Date created", "Total", "Tax", "Shipping Country", "Shipping Phone"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Tumi Salesforce schema missing columns: {missing}")

    # Enforce numeric (prevents lexicographic max / bad math)
    df["Total"] = pd.to_numeric(df["Total"], errors="coerce")
    df["Tax"] = pd.to_numeric(df["Tax"], errors="coerce")

    # Helper: first non-null value in a group
    def first_non_null(s):
        s = s.dropna()
        return s.iloc[0] if len(s) else np.nan

    # Aggregate to ORDER level (prevents overpay across multiple lines)
    ord_df = df.groupby("OrderNo", as_index=False).agg(
        order_total=("Total", "max"),          # order header total repeated on lines → take max
        order_tax=("Tax", "sum"),              # tax is distributed across lines → sum
        date_created=("Date created", first_non_null),
        ship_country=("Shipping Country", first_non_null),
        ship_phone=("Shipping Phone", first_non_null),
    )

    # Build standardized output
    out = ord_df.copy()
    out["Brand"] = "Tumi"

    prefix = out["OrderNo"].astype(str).str[:4].str.upper()

    out["h_location"] = np.select(
        [prefix == "TUAE", prefix == "TUSA", prefix == "TUKW"],
        [32028, 32029, 32030],
        default=""
    )
    out["h_bit_currency"] = np.select(
        [prefix == "TUAE", prefix == "TUSA", prefix == "TUKW"],
        ["AED", "SAR", "KWD"],
        default=""
    )

    out["h_bit_date"] = pd.to_datetime(
        out["date_created"], format="%d.%m.%Y %H:%M", errors="coerce"
    ).dt.strftime("%Y-%m-%dT%H:%M")

    out["h_bit_source_generated_id"] = out["OrderNo"].astype(str)

    # Reuse your existing formatter (expects these column names)
    out["Shipping Country"] = out["ship_country"]
    out["Shipping Phone"] = out["ship_phone"]
    out["h_mobile_number"] = out.apply(lambda r: format_mobile(r, country="Shipping Country", mobile="Shipping Phone"), axis=1)

    out["h_original_bit_amount"] = out["order_total"]
    out["h_bit_amount"] = out["order_total"] - out["order_tax"].fillna(0)
    out["h_bit_source"] = "ECOMM"

    return out[
        ["Brand","h_location","h_bit_date","h_bit_currency","h_bit_source_generated_id","h_mobile_number","h_original_bit_amount","h_bit_amount","h_bit_source"]
    ]

def axel_arigato(df):
    """
    Axel Arigato - Line-level data requiring aggregation
    - Amounts in USD → converted to local currency
    - No tax column → use tax_divisors to back-calculate
    - Order prefix indicates country: AAAE=UAE, AASA=Saudi, AAKW=Kuwait
    """
    df = df.copy()

    # Location mapping (UPDATE THESE VALUES as needed)
    location_map = {
        'United Arab Emirates': 99901,  # TODO: Replace with actual location ID
        'Saudi Arabia': 99902,          # TODO: Replace with actual location ID
        'Kuwait': 99903                 # TODO: Replace with actual location ID
    }

    currency_map = {
        'United Arab Emirates': 'AED',
        'Saudi Arabia': 'SAR',
        'Kuwait': 'KWD'
    }

    # Filter to supported countries only
    df = df[df["Country"].isin(conversion_rates.keys())]

    # Enforce numeric on revenue
    df["Gross Revenue (USD)"] = pd.to_numeric(df["Gross Revenue (USD)"], errors="coerce")

    # Helper: first non-null value in a group
    def first_non_null(s):
        s = s.dropna()
        return s.iloc[0] if len(s) else np.nan

    # Aggregate to ORDER level (sum line-item revenues)
    ord_df = df.groupby("Order ID", as_index=False).agg(
        order_total_usd=("Gross Revenue (USD)", "sum"),
        order_date=("Order Date", first_non_null),
        country=("Country", first_non_null),
        contact_number=("Contact Number", first_non_null),
    )

    # Build standardized output
    out = ord_df.copy()
    out["Brand"] = "Axel Arigato"

    out["h_location"] = out["country"].map(location_map)
    out["h_bit_date"] = pd.to_datetime(out["order_date"]).dt.strftime('%Y-%m-%dT%H:%M')
    out["h_bit_currency"] = out["country"].map(currency_map)
    out["h_bit_source_generated_id"] = out["Order ID"].astype(str)

    # Format mobile - set up columns for format_mobile function
    out["Country"] = out["country"]
    out["Contact Number"] = out["contact_number"]
    out["h_mobile_number"] = out.apply(
        lambda row: format_mobile(row, country="Country", mobile="Contact Number"), axis=1
    )

    # Convert USD to local currency
    out["h_original_bit_amount"] = out["order_total_usd"] * out["country"].map(conversion_rates)

    # Calculate amount excluding tax
    out["h_bit_amount"] = out["h_original_bit_amount"] / out["country"].map(tax_divisors)

    out["h_bit_source"] = "ECOMM"

    return out[
        ["Brand", "h_location", "h_bit_date", "h_bit_currency", "h_bit_source_generated_id",
         "h_mobile_number", "h_original_bit_amount", "h_bit_amount", "h_bit_source"]
    ]

def elemis(df):
    df = df[df["Order Status"] == "COMPLETED"]
    df['Brand'] = "Elemis"
    df['h_location'] = ""
    df['h_location'] = np.where(df['Shipping Country'] == 'United Arab Emirates', 74903, df['h_location'])
    df['h_location'] = np.where(df['Shipping Country'] == 'Saudi Arabia',         74904, df['h_location'])
    df['h_bit_date'] = pd.to_datetime(df.iloc[:, -5]).dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = ""
    df['h_bit_currency'] = np.where(df['Shipping Country'] == 'United Arab Emirates', 'AED', df['h_bit_currency'])
    df['h_bit_currency'] = np.where(df['Shipping Country'] == 'Saudi Arabia',         'SAR', df['h_bit_currency'])
    df['h_bit_source_generated_id'] = df['OrderNo'].astype(str)
    df['h_mobile_number'] = "+971" + df['Shipping Phone'].astype(str).astype(str).str[-11:-2]
    df['h_original_bit_amount'] = df['Order Total Including VAT']
    df['h_bit_amount'] = df['Order Total Excluding VAT']
    df['h_bit_source'] = "ECOMM"

    return df.iloc[:, -9:]

def lacoste(df):
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
    df = df[(df["Country"] == "United Arab Emirates") | (df["Country"] == "Saudi Arabia") | (df["Country"] == "Kuwait")]
    df['Brand'] = "Lacoste"
    df['h_location'] = df['Country'].map(location_map)
    df['h_bit_date'] = pd.to_datetime(df["Record Date"]).dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = df['Country'].map(currency_map)
    df['h_bit_source_generated_id'] = df['Order ID']
    df['h_mobile_number'] = df.apply(lambda row: format_mobile(row, country='Country', mobile='Contact Number'),axis=1)
    df['h_original_bit_amount'] = df['Gross Revenue (USD)'].astype(str).str.replace(r'[\$,]', '', regex=True).astype(float) * df['Country'].map(conversion_rates)
    df['h_bit_amount'] = df['h_original_bit_amount'] / df['Country'].map(tax_divisors)
    df['h_bit_source'] = "ECOMM"

    return df.iloc[:, -9:]

def ghawali(df):
    df = df[df["Fulfillment Status"] == "fulfilled"]
    df['Brand'] = "Ghawali"
    df['h_location'] = ""
    df['h_location'] = np.where(df['Currency'] == 'AED', 13010, df['h_location'])
    df['h_location'] = np.where(df['Currency'] == 'SAR', 13009, df['h_location'])
    df['h_bit_date'] = pd.to_datetime(df["Fulfilled at"]).dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = df['Currency']
    df['h_bit_source_generated_id'] = df['Name']
    df['h_mobile_number'] = df.apply(lambda row: format_mobile(row, country='Shipping Country', mobile='Shipping Phone'),axis=1)
    df['h_original_bit_amount'] = df['Subtotal']
    df['h_bit_amount'] = df['Subtotal'] - df['Taxes']
    df['h_bit_source'] = "ECOMM"

    return df.iloc[:, -9:]

def yeda(df):
    df = df[df["Fulfillment Status"] == "fulfilled"]
    df['Brand'] = "Yeda"
    df['h_location'] = 72901
    df['h_bit_date'] = pd.to_datetime(df["Fulfilled at"]).dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = df['Currency']
    df['h_bit_source_generated_id'] = df['Name']
    df['h_mobile_number'] = df.apply(lambda row: format_mobile(row, country='Shipping Country', mobile='Shipping Phone'),axis=1)
    df['h_original_bit_amount'] = df['Subtotal']
    df['h_bit_amount'] = df['Subtotal'] - df['Taxes']
    df['h_bit_source'] = "ECOMM"

    return df.iloc[:, -9:]

def jacquemus(df):
    df['Brand'] = "Jacquemus"
    df['h_location'] = np.nan
    df['h_location'] = np.where(df['OrderNo'].str.upper().str.startswith('JQAE'), "79701", df['h_location'])
    df['h_location'] = np.where(df['OrderNo'].str.upper().str.startswith('JQSA'), "79703", df['h_location'])
    df['h_bit_date'] = pd.to_datetime(df["Date created"], format='%d.%m.%Y %H:%M').dt.strftime('%Y-%m-%dT%H:%M')
    df['h_bit_currency'] = ""
    df['h_bit_currency'] = np.where(df['OrderNo'].str.upper().str.startswith('JQAE'), 'AED', df['h_bit_currency'])
    df['h_bit_currency'] = np.where(df['OrderNo'].str.upper().str.startswith('JQSA'), 'SAR', df['h_bit_currency'])
    df['h_bit_source_generated_id'] = df['OrderNo']
    df['h_mobile_number'] = df.apply(lambda row: format_mobile(row, country='Shipping Country', mobile='Shipping Phone'),axis=1)
    df['h_original_bit_amount'] = df['Order Total Including VAT']
    df['h_bit_amount'] = df['Order Total Excluding VAT']
    df['h_bit_source'] = "ECOMM"

    return df.iloc[:, -9:]

master_df = pd.DataFrame()

file_patterns = [os.path.join(directory_path,'input','*.csv'), os.path.join(directory_path,'input','*.xlsx')]
files = []
for pattern in file_patterns:
    files.extend(glob.glob(pattern))

brand_dataframes = {}

print("---------------------------------------------------------")
print("")

for file in files:
    file_name = os.path.basename(file)
    identified_brand = None
    for brand in brands:
        # Handle brand names with underscores or spaces in filenames
        brand_variants = [brand.upper(), brand.upper().replace(" ", "_"), brand.upper().replace(" ", "")]
        if any(variant in file_name.upper() for variant in brand_variants):
            identified_brand = brand
            break

    if identified_brand:
        if file.endswith('.csv'):
            df = pd.read_csv(file)
            brand_dataframes[identified_brand] = brand_dataframes.get(identified_brand, []) + [df]
            print(f"Loaded {file_name} as {identified_brand} (CSV)")
        elif file.endswith('.xlsx'):
            excel_file = pd.ExcelFile(file)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet_name)
                brand_dataframes[identified_brand] = brand_dataframes.get(identified_brand, []) + [df]
                print(f"Loaded {file_name} (Sheet: {sheet_name}) as {identified_brand} (Excel)")
print("")
print("---------------------------------------------------------")
print("")
for brand, df_list in brand_dataframes.items():
    for i, df in enumerate(df_list):
        if brand == "Farm Rio":
            current_df = farm_rio(df)
        elif brand == "Tumi":
            current_df = tumi(df)
        elif brand == "Elemis":
            current_df = elemis(df)
        elif brand == "Ghawali":
            current_df = ghawali(df)
        elif brand == "Yeda":
            current_df = yeda(df)
        elif brand == "Lacoste":
            current_df = lacoste(df)
        elif brand == "Jacquemus":
            current_df = jacquemus(df)
        elif brand == "Axel Arigato":
            current_df = axel_arigato(df)
        print(f"Processed {brand} - {i+1}")
        master_df = pd.concat([master_df, current_df], ignore_index=True)

print("")
print("---------------------------------------------------------")
print("")
grouped_df = master_df.groupby('Brand')

for brand, group in grouped_df:
    brand_data = group.iloc[:, 1:]
    filename = f"{directory_path}/output/{brand} - {directory_path}.csv"
    brand_data.to_csv(filename, index=False, header=False, sep='|')
    print(f"Exported {filename}")

print("")
print("Done! ---------------------------------------------------")
print("")
