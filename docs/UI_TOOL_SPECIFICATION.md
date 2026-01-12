# UI Tool Technical Specification

## Overview

This document specifies the requirements for building a UI tool that replicates and enhances the functionality of `ecomm_processor.py`.

---

## 1. Core Data Structures

### 1.1 Brand Configuration Schema

```typescript
interface BrandConfig {
  name: string;                          // "Ghawali"
  enabled: boolean;                      // Toggle for processing
  platform: 'shopify' | 'salesforce' | 'custom';

  // Filtering
  filterColumn?: string;                 // "Fulfillment Status"
  filterValue?: string;                  // "fulfilled"
  filterOperator?: 'equals' | 'contains' | 'in';

  // Aggregation (for line-item data)
  requiresAggregation: boolean;
  aggregationKey?: string;               // "OrderNo", "Order ID"
  aggregationRules?: {
    [outputField: string]: {
      sourceColumn: string;
      operation: 'sum' | 'max' | 'first' | 'first_non_null';
    }
  };

  // Location mapping
  locationStrategy: 'static' | 'country_map' | 'order_prefix' | 'currency_map';
  staticLocation?: number;               // For single-location brands
  locationMap?: Record<string, number>;  // Country/currency → location ID
  orderPrefixLocations?: {               // For prefix-based detection
    prefix: string;
    location: number;
    currency: string;
  }[];

  // Column mappings (source → standard output)
  columnMappings: {
    dateColumn: string;                  // Source column for date
    dateFormat?: string;                 // Optional format string
    orderIdColumn: string;               // Source column for order ID
    phoneColumn: string;                 // Source column for phone
    countryColumn: string;               // Source column for country
    currencyColumn?: string;             // Direct currency column (if available)
    totalWithTaxColumn?: string;         // Total including tax
    totalWithoutTaxColumn?: string;      // Total excluding tax (if pre-calculated)
    taxColumn?: string;                  // Separate tax column
    subtotalColumn?: string;             // Subtotal column
  };

  // Currency handling
  currencyStrategy: 'direct' | 'country_map' | 'order_prefix' | 'conversion';
  conversionRequired: boolean;           // USD → local currency

  // Tax handling
  taxStrategy: 'subtract' | 'divide' | 'pre_calculated';
}
```

### 1.2 Global Configuration

```typescript
interface GlobalConfig {
  directoryPath: string;                 // "NOV 2025"

  conversionRates: {
    'United Arab Emirates': number;      // 3.67
    'Saudi Arabia': number;              // 3.75
    'Kuwait': number;                    // 0.3058
  };

  taxDivisors: {
    'United Arab Emirates': number;      // 1.05
    'Saudi Arabia': number;              // 1.15
    'Kuwait': number;                    // 1.00
  };

  countryCodes: {
    'United Arab Emirates': string;      // "+971"
    'Saudi Arabia': string;              // "+966"
    'Kuwait': string;                    // "+965"
    'Bahrain': string;                   // "+973"
  };

  brands: BrandConfig[];
}
```

### 1.3 Current Brand Configurations

```typescript
const BRAND_CONFIGS: BrandConfig[] = [
  {
    name: "Ghawali",
    enabled: true,
    platform: 'shopify',
    filterColumn: "Fulfillment Status",
    filterValue: "fulfilled",
    filterOperator: 'equals',
    requiresAggregation: false,
    locationStrategy: 'currency_map',
    locationMap: { 'AED': 13010, 'SAR': 13009 },
    columnMappings: {
      dateColumn: "Fulfilled at",
      orderIdColumn: "Name",
      phoneColumn: "Shipping Phone",
      countryColumn: "Shipping Country",
      currencyColumn: "Currency",
      subtotalColumn: "Subtotal",
      taxColumn: "Taxes"
    },
    currencyStrategy: 'direct',
    conversionRequired: false,
    taxStrategy: 'subtract'
  },

  {
    name: "Tumi",
    enabled: true,
    platform: 'salesforce',
    filterColumn: "Payment Status",    // Multiple filters applied
    filterValue: "PAID",
    requiresAggregation: true,
    aggregationKey: "OrderNo",
    aggregationRules: {
      order_total: { sourceColumn: "Total", operation: "max" },
      order_tax: { sourceColumn: "Tax", operation: "sum" },
      date_created: { sourceColumn: "Date created", operation: "first_non_null" },
      ship_country: { sourceColumn: "Shipping Country", operation: "first_non_null" },
      ship_phone: { sourceColumn: "Shipping Phone", operation: "first_non_null" }
    },
    locationStrategy: 'order_prefix',
    orderPrefixLocations: [
      { prefix: "TUAE", location: 32028, currency: "AED" },
      { prefix: "TUSA", location: 32029, currency: "SAR" },
      { prefix: "TUKW", location: 32030, currency: "KWD" }
    ],
    columnMappings: {
      dateColumn: "Date created",
      dateFormat: "%d.%m.%Y %H:%M",
      orderIdColumn: "OrderNo",
      phoneColumn: "Shipping Phone",
      countryColumn: "Shipping Country",
      totalWithTaxColumn: "Total",
      taxColumn: "Tax"
    },
    currencyStrategy: 'order_prefix',
    conversionRequired: false,
    taxStrategy: 'subtract'
  },

  {
    name: "Axel Arigato",
    enabled: true,
    platform: 'custom',
    filterColumn: "Country",
    filterValue: "United Arab Emirates,Saudi Arabia,Kuwait",
    filterOperator: 'in',
    requiresAggregation: true,
    aggregationKey: "Order ID",
    aggregationRules: {
      order_total_usd: { sourceColumn: "Gross Revenue (USD)", operation: "sum" },
      order_date: { sourceColumn: "Order Date", operation: "first_non_null" },
      country: { sourceColumn: "Country", operation: "first_non_null" },
      contact_number: { sourceColumn: "Contact Number", operation: "first_non_null" }
    },
    locationStrategy: 'country_map',
    locationMap: {
      'United Arab Emirates': 99901,
      'Saudi Arabia': 99902,
      'Kuwait': 99903
    },
    columnMappings: {
      dateColumn: "Order Date",
      orderIdColumn: "Order ID",
      phoneColumn: "Contact Number",
      countryColumn: "Country",
      totalWithTaxColumn: "Gross Revenue (USD)"  // In USD
    },
    currencyStrategy: 'country_map',
    conversionRequired: true,
    taxStrategy: 'divide'
  },

  {
    name: "Elemis",
    enabled: true,
    platform: 'salesforce',
    filterColumn: "Order Status",
    filterValue: "COMPLETED",
    filterOperator: 'equals',
    requiresAggregation: false,
    locationStrategy: 'country_map',
    locationMap: {
      'United Arab Emirates': 74903,
      'Saudi Arabia': 74904
    },
    columnMappings: {
      dateColumn: "__POSITIONAL_-5__",  // FRAGILE: uses position
      orderIdColumn: "OrderNo",
      phoneColumn: "Shipping Phone",
      countryColumn: "Shipping Country",
      totalWithTaxColumn: "Order Total Including VAT",
      totalWithoutTaxColumn: "Order Total Excluding VAT"
    },
    currencyStrategy: 'country_map',
    conversionRequired: false,
    taxStrategy: 'pre_calculated'
  },

  {
    name: "Lacoste",
    enabled: true,
    platform: 'custom',
    filterColumn: "Country",
    filterValue: "United Arab Emirates,Saudi Arabia,Kuwait",
    filterOperator: 'in',
    requiresAggregation: false,
    locationStrategy: 'country_map',
    locationMap: {
      'United Arab Emirates': 52052,
      'Saudi Arabia': 52053,
      'Kuwait': 52060
    },
    columnMappings: {
      dateColumn: "Record Date",
      orderIdColumn: "Order ID",
      phoneColumn: "Contact Number",
      countryColumn: "Country",
      totalWithTaxColumn: "Gross Revenue (USD)"  // In USD with $ formatting
    },
    currencyStrategy: 'country_map',
    conversionRequired: true,
    taxStrategy: 'divide'
  },

  {
    name: "Farm Rio",
    enabled: true,
    platform: 'shopify',
    filterColumn: "Fulfillment Status",
    filterValue: "fulfilled",
    filterOperator: 'equals',
    requiresAggregation: false,
    locationStrategy: 'static',
    staticLocation: 61201,
    columnMappings: {
      dateColumn: "Fulfilled at",
      orderIdColumn: "Name",
      phoneColumn: "Shipping Phone",
      countryColumn: "Shipping Country",
      currencyColumn: "Currency",
      totalWithTaxColumn: "Total",
      taxColumn: "Taxes"
    },
    currencyStrategy: 'direct',
    conversionRequired: false,
    taxStrategy: 'subtract'
  },

  {
    name: "Yeda",
    enabled: true,
    platform: 'shopify',
    filterColumn: "Fulfillment Status",
    filterValue: "fulfilled",
    filterOperator: 'equals',
    requiresAggregation: false,
    locationStrategy: 'static',
    staticLocation: 72901,
    columnMappings: {
      dateColumn: "Fulfilled at",
      orderIdColumn: "Name",
      phoneColumn: "Shipping Phone",
      countryColumn: "Shipping Country",
      currencyColumn: "Currency",
      subtotalColumn: "Subtotal",
      taxColumn: "Taxes"
    },
    currencyStrategy: 'direct',
    conversionRequired: false,
    taxStrategy: 'subtract'
  },

  {
    name: "Jacquemus",
    enabled: true,
    platform: 'salesforce',
    requiresAggregation: false,
    locationStrategy: 'order_prefix',
    orderPrefixLocations: [
      { prefix: "JQAE", location: 79701, currency: "AED" },
      { prefix: "JQSA", location: 79703, currency: "SAR" }
    ],
    columnMappings: {
      dateColumn: "Date created",
      dateFormat: "%d.%m.%Y %H:%M",
      orderIdColumn: "OrderNo",
      phoneColumn: "Shipping Phone",
      countryColumn: "Shipping Country",
      totalWithTaxColumn: "Order Total Including VAT",
      totalWithoutTaxColumn: "Order Total Excluding VAT"
    },
    currencyStrategy: 'order_prefix',
    conversionRequired: false,
    taxStrategy: 'pre_calculated'
  }
];
```

---

## 2. Processing Pipeline

### 2.1 File Discovery & Loading

```
INPUT: directory path, supported file extensions
OUTPUT: Map<brandName, DataFrame[]>

1. Glob for *.csv and *.xlsx in {path}/input/
2. For each file:
   a. Extract filename (case-insensitive)
   b. Match against brand names (handle variants: spaces, underscores, no separator)
   c. If CSV: load directly
   d. If XLSX: load each sheet as separate DataFrame
   e. Add to brand's DataFrame list
```

### 2.2 Brand Processing Pipeline

```
INPUT: DataFrame, BrandConfig
OUTPUT: Standardized 9-column DataFrame

1. FILTER (if filterColumn specified)
   - Apply filter: df[filterColumn] == filterValue

2. AGGREGATE (if requiresAggregation)
   - Group by aggregationKey
   - Apply aggregation rules per field

3. TRANSFORM to standard schema:
   a. Brand = config.name
   b. h_location = resolveLocation(row, config)
   c. h_bit_date = parseDate(row[dateColumn], dateFormat)
   d. h_bit_currency = resolveCurrency(row, config)
   e. h_bit_source_generated_id = row[orderIdColumn]
   f. h_mobile_number = formatMobile(row, countryColumn, phoneColumn)
   g. h_original_bit_amount = calculateTotalWithTax(row, config)
   h. h_bit_amount = calculateTotalWithoutTax(row, config)
   i. h_bit_source = "ECOMM"

4. RETURN standardized DataFrame
```

### 2.3 Amount Calculations

```typescript
function calculateTotalWithTax(row: Row, config: BrandConfig): number {
  let amount: number;

  if (config.columnMappings.totalWithTaxColumn) {
    amount = parseAmount(row[config.columnMappings.totalWithTaxColumn]);
  } else if (config.columnMappings.subtotalColumn) {
    amount = parseAmount(row[config.columnMappings.subtotalColumn]);
  }

  if (config.conversionRequired) {
    const country = row[config.columnMappings.countryColumn];
    amount *= globalConfig.conversionRates[country];
  }

  return amount;
}

function calculateTotalWithoutTax(row: Row, config: BrandConfig): number {
  switch (config.taxStrategy) {
    case 'pre_calculated':
      return parseAmount(row[config.columnMappings.totalWithoutTaxColumn]);

    case 'subtract':
      const total = row.h_original_bit_amount;
      const tax = parseAmount(row[config.columnMappings.taxColumn]);
      return total - tax;

    case 'divide':
      const totalWithTax = row.h_original_bit_amount;
      const country = row[config.columnMappings.countryColumn];
      return totalWithTax / globalConfig.taxDivisors[country];
  }
}

function parseAmount(value: string | number): number {
  if (typeof value === 'number') return value;
  // Remove $, commas, spaces
  return parseFloat(value.replace(/[\$,\s]/g, ''));
}
```

### 2.4 Location Resolution

```typescript
function resolveLocation(row: Row, config: BrandConfig): number | string {
  switch (config.locationStrategy) {
    case 'static':
      return config.staticLocation;

    case 'country_map':
      const country = row[config.columnMappings.countryColumn];
      return config.locationMap[country];

    case 'currency_map':
      const currency = row[config.columnMappings.currencyColumn];
      return config.locationMap[currency];

    case 'order_prefix':
      const orderId = row[config.columnMappings.orderIdColumn].toUpperCase();
      for (const mapping of config.orderPrefixLocations) {
        if (orderId.startsWith(mapping.prefix)) {
          return mapping.location;
        }
      }
      return '';
  }
}
```

### 2.5 Phone Formatting

```typescript
function formatMobile(row: Row, countryCol: string, phoneCol: string): string {
  const country = row[countryCol];
  let phone = String(row[phoneCol])
    .replace(/\s/g, '')
    .replace('.0', '');

  const last9 = phone.slice(-9);

  const countryCodeMap: Record<string, string> = {
    'AE': '+971', 'United Arab Emirates': '+971',
    'SA': '+966', 'Saudi Arabia': '+966',
    'BH': '+973', 'Bahrain': '+973',
    'KW': '+965', 'Kuwait': '+965'
  };

  return countryCodeMap[country]
    ? countryCodeMap[country] + last9
    : phone;
}
```

---

## 3. UI Components Required

### 3.1 Dashboard / Home

- Current directory path display
- Brand status cards (enabled/disabled, file count, row count)
- Quick stats (total files, total orders, errors)
- Process button

### 3.2 Configuration Panel

- **Global Settings**
  - Directory path input
  - Conversion rates editor (table)
  - Tax divisors editor (table)

- **Brand Management**
  - List of brands with enable/disable toggles
  - Add new brand button
  - Per-brand configuration modal

### 3.3 Brand Configuration Modal

- Basic Info: Name, Platform type, Enabled
- Filtering: Column, Operator, Value
- Aggregation: Enable, Key column, Rules
- Location: Strategy selector, Map editor
- Column Mappings: Source → Target pairs
- Currency: Strategy, Conversion flag
- Tax: Strategy selector

### 3.4 File Upload / Selection

- Drag-and-drop zone
- File list with detected brand
- Manual brand override dropdown
- Excel sheet selector
- Column preview

### 3.5 Processing View

- Step-by-step progress indicator
- Per-brand processing status
- Error log with line numbers
- Skip/retry controls

### 3.6 Preview & Export

- Tabbed view per brand
- Data table with pagination
- Column validation indicators
- Download individual / Download all (ZIP)
- Output format options (delimiter, header)

---

## 4. Validation Rules

### 4.1 Pre-Processing Validation

```typescript
interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

interface ValidationError {
  type: 'missing_column' | 'invalid_data' | 'no_rows';
  column?: string;
  message: string;
  severity: 'error' | 'warning';
}

function validateBrandData(df: DataFrame, config: BrandConfig): ValidationResult {
  const errors: ValidationError[] = [];

  // Check required columns exist
  const requiredColumns = [
    config.columnMappings.dateColumn,
    config.columnMappings.orderIdColumn,
    config.columnMappings.phoneColumn,
    config.columnMappings.countryColumn
  ].filter(Boolean);

  for (const col of requiredColumns) {
    if (!df.columns.includes(col)) {
      errors.push({
        type: 'missing_column',
        column: col,
        message: `Required column "${col}" not found`,
        severity: 'error'
      });
    }
  }

  // Check filter column if specified
  if (config.filterColumn && !df.columns.includes(config.filterColumn)) {
    errors.push({
      type: 'missing_column',
      column: config.filterColumn,
      message: `Filter column "${config.filterColumn}" not found`,
      severity: 'error'
    });
  }

  return {
    valid: errors.filter(e => e.severity === 'error').length === 0,
    errors,
    warnings: errors.filter(e => e.severity === 'warning')
  };
}
```

### 4.2 Row-Level Validation

- Date parseable
- Phone number has digits
- Amount is numeric
- Country is recognized (for conversion/tax)

---

## 5. Output Specification

### 5.1 File Naming
```
{Brand} - {directory_path}.csv
Example: Ghawali - NOV 2025.csv
```

### 5.2 Format
- Delimiter: `|` (pipe)
- Header: None
- Index: None
- Quoting: Minimal (only if field contains delimiter)
- Encoding: UTF-8

### 5.3 Column Order (8 columns, Brand excluded)
```
h_location|h_bit_date|h_bit_currency|h_bit_source_generated_id|h_mobile_number|h_original_bit_amount|h_bit_amount|h_bit_source
```

---

## 6. Error Handling Strategy

### 6.1 File-Level Errors
- File not found → Skip, log warning
- Parse error → Skip file, log error with details
- No brand match → Skip, log info

### 6.2 Row-Level Errors
- Missing required field → Skip row, log warning
- Invalid date → Use null/empty, log warning
- Invalid phone → Use raw value, log info
- Invalid amount → Skip row, log error

### 6.3 Brand-Level Errors
- Zero valid rows after filtering → Skip brand, log warning
- Missing required columns → Skip brand, log error

---

## 7. Suggested Tech Stack

### Frontend
- **Framework:** React with TypeScript
- **UI Library:** Tailwind CSS + shadcn/ui
- **State Management:** Zustand or React Context
- **File Handling:** react-dropzone
- **Data Tables:** TanStack Table
- **Excel Parsing:** xlsx (SheetJS)
- **CSV Parsing:** PapaParse

### Backend (optional - for heavy processing)
- **Runtime:** Node.js or Python (FastAPI)
- **Data Processing:** pandas (Python) or Arquero (JS)

### Fully Client-Side Option
- All processing in browser using:
  - xlsx for Excel
  - PapaParse for CSV
  - Native JS for transformations
  - Blob/File API for downloads
