# E-Commerce Order Processor - Complete Script Analysis

## Executive Summary

This script is a **multi-brand e-commerce order data normalizer** that transforms order exports from various e-commerce platforms (Shopify, Salesforce Commerce Cloud, custom systems) into a standardized output format for a loyalty/rewards system (likely "bits" based on column naming).

---

## 1. High-Level Purpose

**Input:** Raw order data files (CSV/Excel) from 8 different retail brands
**Output:** Normalized pipe-delimited CSV files with standardized schema per brand
**Use Case:** Feeding order transaction data into a loyalty points system

---

## 2. Supported Brands & Their Data Sources

| Brand | Platform Type | Data Granularity | Key Identifier |
|-------|--------------|------------------|----------------|
| Ghawali | Shopify | Order-level | Name (order name) |
| Elemis | Custom/Salesforce | Order-level | OrderNo |
| Lacoste | Custom Export | Order-level | Order ID |
| Farm Rio | Shopify | Order-level | Name |
| Jacquemus | Salesforce | Order-level | OrderNo |
| Yeda | Shopify | Order-level | Name |
| Tumi | Salesforce | Line-item → aggregated | OrderNo |
| Axel Arigato | Custom | Line-item → aggregated | Order ID |

---

## 3. Configuration Constants

### 3.1 Directory Structure
```
{directory_path}/
├── input/          # Source files (CSV, XLSX)
└── output/         # Generated normalized files
```

Current configured path: `NOV 2025`

### 3.2 Currency Conversion Rates (USD to Local)
```python
conversion_rates = {
    'United Arab Emirates': 3.67,   # USD → AED
    'Saudi Arabia': 3.75,           # USD → SAR
    'Kuwait': 1 / 3.27              # USD → KWD (~0.3058)
}
```

### 3.3 Tax Divisors (for back-calculating pre-tax amounts)
```python
tax_divisors = {
    'United Arab Emirates': 1.05,   # 5% VAT
    'Saudi Arabia': 1.15,           # 15% VAT
    'Kuwait': 1.00                  # 0% VAT
}
```

---

## 4. Standardized Output Schema

Every brand processor outputs exactly **9 columns**:

| Column | Description | Example |
|--------|-------------|---------|
| `Brand` | Brand name string | "Ghawali" |
| `h_location` | Store/location ID (numeric) | 13010 |
| `h_bit_date` | Transaction timestamp (ISO format) | "2025-11-15T14:30" |
| `h_bit_currency` | Currency code | "AED", "SAR", "KWD" |
| `h_bit_source_generated_id` | Original order ID | "#12345" |
| `h_mobile_number` | Formatted phone with country code | "+971501234567" |
| `h_original_bit_amount` | Total amount WITH tax | 150.00 |
| `h_bit_amount` | Amount EXCLUDING tax | 142.86 |
| `h_bit_source` | Data source identifier | "ECOMM" (always) |

---

## 5. Shared Utility Functions

### 5.1 `format_mobile(row, country, mobile)`

**Purpose:** Normalizes phone numbers to international format with country code.

**Logic:**
1. Extracts raw mobile value, removes spaces and ".0" suffix
2. Takes last 9 digits of the number
3. Prepends appropriate country code based on country field

**Country Code Mapping:**
| Country | Code |
|---------|------|
| UAE / AE | +971 |
| Saudi Arabia / SA | +966 |
| Bahrain / BH | +973 |
| Kuwait / KW | +965 |
| Other | Returns original |

---

## 6. Brand-Specific Processors (Detailed)

### 6.1 `farm_rio(df)` - Shopify Export

**Platform:** Shopify
**Filter:** `Fulfillment Status == "fulfilled"`
**Location:** Static `61201` (single location)

**Column Mappings:**
| Output | Source |
|--------|--------|
| h_bit_date | `Fulfilled at` |
| h_bit_currency | `Currency` |
| h_bit_source_generated_id | `Name` |
| h_mobile_number | `Shipping Country` + `Shipping Phone` |
| h_original_bit_amount | `Total` |
| h_bit_amount | `Total - Taxes` |

**Required Input Columns:**
- Fulfillment Status, Fulfilled at, Currency, Name, Shipping Country, Shipping Phone, Total, Taxes

---

### 6.2 `tumi(df)` - Salesforce Commerce Cloud (Line-Item Aggregation)

**Platform:** Salesforce Commerce Cloud
**Filter:** Payment Status=PAID, Confirmation Status=CONFIRMED, Export Status=EXPORTED
**Aggregation:** Groups by `OrderNo`, takes max(Total), sum(Tax)

**Location Logic (by order prefix):**
| Prefix | Country | Location ID | Currency |
|--------|---------|-------------|----------|
| TUAE | UAE | 32028 | AED |
| TUSA | Saudi | 32029 | SAR |
| TUKW | Kuwait | 32030 | KWD |

**Date Format:** `%d.%m.%Y %H:%M` (European format)

**Required Input Columns:**
- OrderNo, Date created, Total, Tax, Shipping Country, Shipping Phone
- Optional: Payment Status, Confirmation Status, Export Status

**Aggregation Strategy:**
- `Total`: MAX (repeated header value on each line)
- `Tax`: SUM (distributed across line items)
- Other fields: First non-null value

---

### 6.3 `axel_arigato(df)` - Custom Export with USD Conversion

**Platform:** Custom (amounts in USD)
**Filter:** Country must be in `conversion_rates.keys()`
**Aggregation:** Groups by `Order ID`, sums `Gross Revenue (USD)`

**Currency Conversion:**
1. Sum USD revenue per order
2. Multiply by country's conversion rate
3. Divide by tax divisor to get pre-tax amount

**Location IDs (placeholder):**
| Country | Location ID |
|---------|-------------|
| UAE | 99901 |
| Saudi Arabia | 99902 |
| Kuwait | 99903 |

**Required Input Columns:**
- Order ID, Order Date, Country, Contact Number, Gross Revenue (USD)

---

### 6.4 `elemis(df)` - Custom/Salesforce

**Platform:** Custom
**Filter:** `Order Status == "COMPLETED"`

**Location Logic:**
| Country | Location ID | Currency |
|---------|-------------|----------|
| UAE | 74903 | AED |
| Saudi Arabia | 74904 | SAR |

**Phone Handling:** Hardcoded +971 prefix, takes characters [-11:-2] from phone string
**Date Source:** Uses column at position -5 (fragile positional reference)

**Required Input Columns:**
- Order Status, Shipping Country, OrderNo, Shipping Phone, Order Total Including VAT, Order Total Excluding VAT

---

### 6.5 `lacoste(df)` - Custom Export with USD Conversion

**Platform:** Custom (amounts in USD with $ formatting)
**Filter:** Country in [UAE, Saudi Arabia, Kuwait]

**Location IDs:**
| Country | Location ID |
|---------|-------------|
| UAE | 52052 |
| Saudi Arabia | 52053 |
| Kuwait | 52060 |

**Amount Processing:**
1. Remove `$` and `,` from `Gross Revenue (USD)`
2. Convert to float
3. Multiply by conversion rate
4. Divide by tax divisor

**Required Input Columns:**
- Country, Record Date, Order ID, Contact Number, Gross Revenue (USD)

---

### 6.6 `ghawali(df)` - Shopify Export

**Platform:** Shopify
**Filter:** `Fulfillment Status == "fulfilled"`

**Location Logic (by currency):**
| Currency | Location ID |
|----------|-------------|
| AED | 13010 |
| SAR | 13009 |

**Required Input Columns:**
- Fulfillment Status, Currency, Fulfilled at, Name, Shipping Country, Shipping Phone, Subtotal, Taxes

---

### 6.7 `yeda(df)` - Shopify Export

**Platform:** Shopify
**Filter:** `Fulfillment Status == "fulfilled"`
**Location:** Static `72901` (single location)

**Required Input Columns:**
- Fulfillment Status, Fulfilled at, Currency, Name, Shipping Country, Shipping Phone, Subtotal, Taxes

---

### 6.8 `jacquemus(df)` - Salesforce Export

**Platform:** Salesforce
**Filter:** None (processes all rows)

**Location Logic (by order prefix):**
| Prefix | Country | Location ID | Currency |
|--------|---------|-------------|----------|
| JQAE | UAE | 79701 | AED |
| JQSA | Saudi | 79703 | SAR |

**Date Format:** `%d.%m.%Y %H:%M` (European format)

**Required Input Columns:**
- OrderNo, Date created, Shipping Country, Shipping Phone, Order Total Including VAT, Order Total Excluding VAT

---

## 7. Main Processing Pipeline

### 7.1 File Discovery
```
1. Glob for *.csv and *.xlsx in {directory_path}/input/
2. Match files to brands by filename (case-insensitive)
3. Handle brand name variants: "Farm Rio" → "FARM RIO", "FARM_RIO", "FARMRIO"
```

### 7.2 File Loading
- **CSV:** Direct `pd.read_csv()`
- **Excel:** Loads ALL sheets individually as separate dataframes

### 7.3 Processing Loop
```
For each brand → For each dataframe:
    1. Call brand-specific processor function
    2. Concatenate to master_df
```

### 7.4 Output Generation
```
1. Group master_df by Brand
2. For each brand group:
   - Remove Brand column (first column)
   - Export to {directory_path}/output/{Brand} - {directory_path}.csv
   - Format: pipe-delimited, no header, no index
```

---

## 8. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT DIRECTORY                          │
│  {directory_path}/input/                                    │
│  ├── ghawali_orders.csv                                     │
│  ├── TUMI_export.xlsx                                       │
│  ├── lacoste-orders.csv                                     │
│  └── ...                                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              FILE DISCOVERY & BRAND MATCHING                │
│  1. Glob *.csv + *.xlsx                                     │
│  2. Match filename → brand (case-insensitive)               │
│  3. Excel: Load each sheet separately                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              BRAND-SPECIFIC PROCESSING                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Ghawali │ │  Tumi   │ │ Lacoste │ │   ...   │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│       │           │           │           │                 │
│       ▼           ▼           ▼           ▼                 │
│  ┌──────────────────────────────────────────────┐          │
│  │          STANDARDIZED 9-COLUMN OUTPUT         │          │
│  │  Brand | h_location | h_bit_date | ...        │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              MASTER DATAFRAME (CONCATENATED)                │
│  All brands combined into single DataFrame                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              GROUP BY BRAND & EXPORT                        │
│  {directory_path}/output/                                   │
│  ├── Ghawali - NOV 2025.csv                                 │
│  ├── Tumi - NOV 2025.csv                                    │
│  ├── Lacoste - NOV 2025.csv                                 │
│  └── ...                                                    │
│                                                             │
│  Format: pipe-delimited | no header | no index              │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. UI Tool Requirements (Derived)

Based on this analysis, a UI tool would need to support:

### 9.1 Configuration
- [ ] Directory path selection (input/output)
- [ ] Brand enable/disable toggles
- [ ] Editable conversion rates
- [ ] Editable tax divisors
- [ ] Editable location IDs per brand/country

### 9.2 File Management
- [ ] File upload (CSV, XLSX)
- [ ] Automatic brand detection from filename
- [ ] Manual brand assignment override
- [ ] Excel sheet selection

### 9.3 Processing
- [ ] Preview of raw input data
- [ ] Preview of transformed output
- [ ] Validation of required columns per brand
- [ ] Error handling with clear messages

### 9.4 Output
- [ ] Download individual brand files
- [ ] Download all as ZIP
- [ ] Preview before export
- [ ] Custom output directory selection

### 9.5 Brand-Specific Customization
- [ ] Add new brands
- [ ] Edit column mappings
- [ ] Edit filter conditions
- [ ] Edit location/currency mappings

---

## 10. Known Issues & Technical Debt

### 10.1 Fragile Code Patterns
1. **Elemis date column:** Uses positional index `df.iloc[:, -5]` instead of column name
2. **Column slicing:** Uses `df.iloc[:, -9:]` which assumes exact column count
3. **In-place DataFrame modification:** Some functions modify input df directly

### 10.2 Inconsistencies
1. **Phone formatting:** Elemis uses hardcoded +971 while others use `format_mobile()`
2. **Amount fields:** Some use `Total`, others `Subtotal`, others `Order Total Including VAT`
3. **Tax handling:** Some subtract tax, others divide by tax divisor

### 10.3 Missing Features
1. **No validation:** Missing required columns cause cryptic pandas errors
2. **No logging:** Only print statements for status
3. **No error recovery:** Single bad row can crash entire brand processing
4. **Hardcoded paths:** No command-line arguments or config file

---

## 11. Brand Processor Summary Matrix

| Brand | Filter | Aggregation | Currency Source | Tax Handling | Date Format |
|-------|--------|-------------|-----------------|--------------|-------------|
| Farm Rio | fulfilled | None | Column | Subtract | Auto-detect |
| Tumi | PAID+CONFIRMED+EXPORTED | By OrderNo | Order prefix | Subtract | dd.mm.yyyy HH:MM |
| Axel Arigato | Country filter | By Order ID | Country mapping | Divide | Auto-detect |
| Elemis | COMPLETED | None | Country mapping | Pre-calculated | Auto-detect |
| Lacoste | Country filter | None | Country mapping | Divide | Auto-detect |
| Ghawali | fulfilled | None | Column | Subtract | Auto-detect |
| Yeda | fulfilled | None | Column | Subtract | Auto-detect |
| Jacquemus | None | None | Order prefix | Pre-calculated | dd.mm.yyyy HH:MM |

---

## 12. Column Requirements by Brand

### Shopify-Style (Ghawali, Yeda, Farm Rio)
```
Fulfillment Status, Fulfilled at, Currency, Name,
Shipping Country, Shipping Phone, Subtotal/Total, Taxes
```

### Salesforce-Style (Tumi, Jacquemus, Elemis)
```
OrderNo, Date created, Shipping Country, Shipping Phone,
Total/Order Total Including VAT, Tax/Order Total Excluding VAT
Optional: Payment Status, Confirmation Status, Export Status
```

### Custom USD-Style (Lacoste, Axel Arigato)
```
Order ID, Order Date/Record Date, Country,
Contact Number, Gross Revenue (USD)
```

---

## 13. Output File Format Details

**Filename Pattern:** `{Brand} - {directory_path}.csv`
**Example:** `Ghawali - NOV 2025.csv`

**Format:**
- Delimiter: `|` (pipe)
- Header: None
- Index: None
- Columns: 8 (Brand column excluded in output)

**Sample Output Row:**
```
13010|2025-11-15T14:30|AED|#12345|+971501234567|150.00|142.86|ECOMM
```
