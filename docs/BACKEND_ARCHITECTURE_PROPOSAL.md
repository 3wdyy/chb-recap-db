# Backend Architecture Proposal: E-Commerce Order Processor

## Part 1: Deep Analysis of Current Workarounds & Pain Points

### 1.1 Fragile Code Patterns Identified

| Issue | Location | Problem | Impact |
|-------|----------|---------|--------|
| Positional column access | Elemis line 205: `df.iloc[:, -5]` | Breaks if columns reorder | Silent data corruption |
| Fixed column slice | All: `df.iloc[:, -9:]` | Assumes exact column count | Breaks if schema changes |
| Hardcoded phone format | Elemis: `"+971" + str[-11:-2]` | UAE-only, ignores country | Wrong numbers for Saudi |
| In-place DataFrame mutation | Most functions modify input | Side effects, no rollback | Debugging nightmare |
| Duplicate `first_non_null` | Tumi & Axel Arigato | Same helper defined twice | Maintenance burden |

### 1.2 Inconsistent Patterns Across Brands

**Filter Conditions:**
```
Ghawali, Yeda, Farm Rio:  Fulfillment Status == "fulfilled"
Elemis:                    Order Status == "COMPLETED"
Tumi:                      Payment Status == "PAID" AND Confirmation Status == "CONFIRMED" AND Export Status == "EXPORTED"
Lacoste, Axel Arigato:     Country IN [UAE, Saudi, Kuwait]
Jacquemus:                 NO FILTER (processes all rows)
```

**Amount Source Fields:**
```
Total              → Farm Rio
Subtotal           → Ghawali, Yeda
Order Total Inc VAT → Elemis, Jacquemus
Gross Revenue (USD) → Lacoste, Axel Arigato (requires conversion)
Total (aggregated)  → Tumi (max of line items)
```

**Tax Handling:**
```
SUBTRACT:        amount = total - taxes      (Farm Rio, Ghawali, Yeda, Tumi)
DIVIDE:          amount = total / divisor    (Lacoste, Axel Arigato)
PRE_CALCULATED:  amount = column_value       (Elemis, Jacquemus)
```

### 1.3 Hidden Business Logic

1. **Tumi aggregation**: Total is MAX (header repeated), Tax is SUM (distributed across lines)
2. **Order prefix routing**: TUAE/JQAE → UAE, TUSA/JQSA → Saudi, TUKW → Kuwait
3. **Country code normalization**: "AE" = "United Arab Emirates" = "UAE" must all map to +971
4. **Currency symbols**: Lacoste data has "$1,234.56" format requiring cleanup
5. **Phone digit extraction**: Last 9 digits used (not 10) for all countries

---

## Part 2: Architectural Principles

### 2.1 Core Design Goals

1. **Zero-Code Configuration**: All brand logic expressible via JSON/YAML config
2. **Declarative Pipelines**: Define WHAT to do, not HOW
3. **Strategy Pattern**: Swappable algorithms for location/currency/tax/phone
4. **Schema Registry**: Version-controlled input schemas per brand
5. **Validation First**: Fail fast with clear errors before processing
6. **Audit Trail**: Track every transformation for debugging

### 2.2 Separation of Concerns

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFIGURATION LAYER                      │
│  • Global settings (rates, divisors, country codes)         │
│  • Brand definitions (schemas, mappings, strategies)        │
│  • Output format specifications                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING ENGINE                        │
│  • Pipeline orchestrator                                    │
│  • Step executors (filter, aggregate, transform, etc.)      │
│  • Strategy implementations                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                        │
│  • File readers (CSV, Excel, future: API)                   │
│  • File writers (CSV, Excel, JSON)                          │
│  • Config persistence (JSON files or database)              │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 3: Configuration Schema Design

### 3.1 Global Configuration

```yaml
# global_config.yaml
version: "1.0"

# Currency conversion rates (from USD)
conversion_rates:
  United Arab Emirates: 3.67
  Saudi Arabia: 3.75
  Kuwait: 0.3058  # 1/3.27

# Tax divisors for back-calculating pre-tax amounts
tax_divisors:
  United Arab Emirates: 1.05  # 5% VAT
  Saudi Arabia: 1.15          # 15% VAT
  Kuwait: 1.00                # 0% VAT

# Phone country codes
country_phone_codes:
  - patterns: ["AE", "United Arab Emirates", "UAE"]
    code: "+971"
    digits_to_keep: 9
  - patterns: ["SA", "Saudi Arabia", "KSA"]
    code: "+966"
    digits_to_keep: 9
  - patterns: ["KW", "Kuwait"]
    code: "+965"
    digits_to_keep: 9
  - patterns: ["BH", "Bahrain"]
    code: "+973"
    digits_to_keep: 9

# Supported countries (for filtering)
supported_countries:
  - United Arab Emirates
  - Saudi Arabia
  - Kuwait

# Default output settings
output:
  delimiter: "|"
  include_header: false
  include_index: false
  date_format: "%Y-%m-%dT%H:%M"
  encoding: "utf-8"
```

### 3.2 Brand Configuration Schema

```yaml
# brands/ghawali.yaml
brand:
  name: "Ghawali"
  enabled: true
  description: "Shopify-based perfume brand"

# Input schema definition
input_schema:
  platform: "shopify"
  required_columns:
    - Fulfillment Status
    - Fulfilled at
    - Currency
    - Name
    - Shipping Country
    - Shipping Phone
    - Subtotal
    - Taxes
  optional_columns:
    - Discount Code
    - Notes

# Processing pipeline (executed in order)
pipeline:
  # Step 1: Filter rows
  - step: filter
    config:
      column: "Fulfillment Status"
      operator: "equals"
      value: "fulfilled"
      case_sensitive: false

  # Step 2: No aggregation needed (order-level data)
  # - step: aggregate (omitted)

  # Step 3: Transform to output schema
  - step: transform
    config:
      mappings:
        # Output field: Source definition
        Brand:
          type: static
          value: "Ghawali"

        h_location:
          type: lookup
          strategy: currency_map
          source_column: "Currency"
          mapping:
            AED: 13010
            SAR: 13009
          default: null

        h_bit_date:
          type: date
          source_column: "Fulfilled at"
          input_format: auto  # Auto-detect
          output_format: "%Y-%m-%dT%H:%M"

        h_bit_currency:
          type: direct
          source_column: "Currency"

        h_bit_source_generated_id:
          type: direct
          source_column: "Name"
          transform: to_string

        h_mobile_number:
          type: phone
          country_column: "Shipping Country"
          phone_column: "Shipping Phone"

        h_original_bit_amount:
          type: direct
          source_column: "Subtotal"
          transform: to_numeric

        h_bit_amount:
          type: formula
          expression: "{Subtotal} - {Taxes}"
          # Alternative explicit config:
          # strategy: subtract
          # total_column: "Subtotal"
          # tax_column: "Taxes"

        h_bit_source:
          type: static
          value: "ECOMM"

# Output column order (explicit, not positional)
output_columns:
  - Brand
  - h_location
  - h_bit_date
  - h_bit_currency
  - h_bit_source_generated_id
  - h_mobile_number
  - h_original_bit_amount
  - h_bit_amount
  - h_bit_source
```

### 3.3 Complex Brand Example: Tumi (with aggregation)

```yaml
# brands/tumi.yaml
brand:
  name: "Tumi"
  enabled: true
  description: "Salesforce Commerce Cloud - line item data"

input_schema:
  platform: "salesforce"
  required_columns:
    - OrderNo
    - Date created
    - Total
    - Tax
    - Shipping Country
    - Shipping Phone
  optional_columns:
    - Payment Status
    - Confirmation Status
    - Export Status

pipeline:
  # Step 1: Multiple conditional filters
  - step: filter
    config:
      mode: all_of  # AND logic
      conditions:
        - column: "Payment Status"
          operator: "equals"
          value: "PAID"
          case_sensitive: false
          skip_if_column_missing: true  # Optional filter
        - column: "Confirmation Status"
          operator: "equals"
          value: "CONFIRMED"
          case_sensitive: false
          skip_if_column_missing: true
        - column: "Export Status"
          operator: "equals"
          value: "EXPORTED"
          case_sensitive: false
          skip_if_column_missing: true

  # Step 2: Aggregate line items to order level
  - step: aggregate
    config:
      group_by: "OrderNo"
      aggregations:
        order_total:
          source: "Total"
          function: "max"      # Header value repeated on each line
          coerce_numeric: true
        order_tax:
          source: "Tax"
          function: "sum"      # Tax distributed across lines
          coerce_numeric: true
        date_created:
          source: "Date created"
          function: "first_non_null"
        ship_country:
          source: "Shipping Country"
          function: "first_non_null"
        ship_phone:
          source: "Shipping Phone"
          function: "first_non_null"

  # Step 3: Transform
  - step: transform
    config:
      mappings:
        Brand:
          type: static
          value: "Tumi"

        h_location:
          type: lookup
          strategy: order_prefix
          source_column: "OrderNo"
          prefix_length: 4
          mapping:
            TUAE: 32028
            TUSA: 32029
            TUKW: 32030
          default: null

        h_bit_date:
          type: date
          source_column: "date_created"  # From aggregation
          input_format: "%d.%m.%Y %H:%M"
          output_format: "%Y-%m-%dT%H:%M"

        h_bit_currency:
          type: lookup
          strategy: order_prefix
          source_column: "OrderNo"
          prefix_length: 4
          mapping:
            TUAE: "AED"
            TUSA: "SAR"
            TUKW: "KWD"
          default: null

        h_bit_source_generated_id:
          type: direct
          source_column: "OrderNo"
          transform: to_string

        h_mobile_number:
          type: phone
          country_column: "ship_country"
          phone_column: "ship_phone"

        h_original_bit_amount:
          type: direct
          source_column: "order_total"

        h_bit_amount:
          type: formula
          expression: "{order_total} - COALESCE({order_tax}, 0)"

        h_bit_source:
          type: static
          value: "ECOMM"

output_columns:
  - Brand
  - h_location
  - h_bit_date
  - h_bit_currency
  - h_bit_source_generated_id
  - h_mobile_number
  - h_original_bit_amount
  - h_bit_amount
  - h_bit_source
```

### 3.4 USD Conversion Brand Example: Axel Arigato

```yaml
# brands/axel_arigato.yaml
brand:
  name: "Axel Arigato"
  enabled: true
  description: "Custom export with USD amounts"

input_schema:
  platform: "custom"
  required_columns:
    - Order ID
    - Order Date
    - Country
    - Contact Number
    - Gross Revenue (USD)

pipeline:
  # Step 1: Filter to supported countries
  - step: filter
    config:
      column: "Country"
      operator: "in"
      value: "$ref:global.supported_countries"  # Reference global config

  # Step 2: Aggregate line items
  - step: aggregate
    config:
      group_by: "Order ID"
      aggregations:
        order_total_usd:
          source: "Gross Revenue (USD)"
          function: "sum"
          coerce_numeric: true
        order_date:
          source: "Order Date"
          function: "first_non_null"
        country:
          source: "Country"
          function: "first_non_null"
        contact_number:
          source: "Contact Number"
          function: "first_non_null"

  # Step 3: Transform with currency conversion
  - step: transform
    config:
      mappings:
        Brand:
          type: static
          value: "Axel Arigato"

        h_location:
          type: lookup
          strategy: country_map
          source_column: "country"
          mapping:
            United Arab Emirates: 99901  # TODO: Update
            Saudi Arabia: 99902
            Kuwait: 99903
          default: null

        h_bit_date:
          type: date
          source_column: "order_date"
          input_format: auto
          output_format: "%Y-%m-%dT%H:%M"

        h_bit_currency:
          type: lookup
          strategy: country_map
          source_column: "country"
          mapping:
            United Arab Emirates: "AED"
            Saudi Arabia: "SAR"
            Kuwait: "KWD"

        h_bit_source_generated_id:
          type: direct
          source_column: "Order ID"
          transform: to_string

        h_mobile_number:
          type: phone
          country_column: "country"
          phone_column: "contact_number"

        h_original_bit_amount:
          type: currency_convert
          source_column: "order_total_usd"
          source_currency: "USD"
          target_currency_column: "country"  # Look up from country
          rates_ref: "$ref:global.conversion_rates"

        h_bit_amount:
          type: tax_exclude
          strategy: divide
          amount_column: "h_original_bit_amount"  # Use calculated field
          divisor_lookup_column: "country"
          divisors_ref: "$ref:global.tax_divisors"

        h_bit_source:
          type: static
          value: "ECOMM"
```

---

## Part 4: Processing Engine Architecture

### 4.1 Pipeline Step Types

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE STEPS                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐   ┌───────────┐   ┌───────────┐   ┌─────────┐ │
│  │ FILTER  │ → │ AGGREGATE │ → │ TRANSFORM │ → │VALIDATE │ │
│  └─────────┘   └───────────┘   └───────────┘   └─────────┘ │
│       │              │               │               │      │
│       ▼              ▼               ▼               ▼      │
│  • equals        • group_by      • static        • required │
│  • not_equals    • sum           • direct        • type     │
│  • contains      • max           • lookup        • range    │
│  • in            • min           • date          • pattern  │
│  • not_in        • first         • phone         • custom   │
│  • greater_than  • first_non_null• formula                  │
│  • less_than     • count         • currency_convert         │
│  • is_null       • concat        • tax_exclude              │
│  • is_not_null                   • clean (regex)            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Transformation Types (Detailed)

| Type | Description | Config Options |
|------|-------------|----------------|
| `static` | Fixed value | `value` |
| `direct` | Copy from source column | `source_column`, `transform` (to_string, to_numeric, to_upper, to_lower) |
| `lookup` | Map value via lookup table | `strategy` (country_map, currency_map, order_prefix), `source_column`, `mapping`, `default` |
| `date` | Parse and format date | `source_column`, `input_format` (or "auto"), `output_format` |
| `phone` | Format phone number | `country_column`, `phone_column` |
| `formula` | Calculate from expression | `expression` with `{column}` placeholders |
| `currency_convert` | Convert currencies | `source_column`, `source_currency`, `target_currency_column`, `rates_ref` |
| `tax_exclude` | Calculate pre-tax amount | `strategy` (subtract, divide, pre_calculated), relevant columns |
| `clean` | Regex-based cleaning | `source_column`, `pattern`, `replacement` |
| `conditional` | Value based on condition | `conditions` array with when/then/else |

### 4.3 Lookup Strategies

```
┌─────────────────────────────────────────────────────────────┐
│                    LOOKUP STRATEGIES                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  STATIC                                                     │
│  ├── Returns same value for all rows                        │
│  └── Config: { value: 61201 }                               │
│                                                             │
│  DIRECT_MAP                                                 │
│  ├── Maps column value directly                             │
│  └── Config: { column: "Currency", AED: 13010, SAR: 13009 } │
│                                                             │
│  COUNTRY_MAP                                                │
│  ├── Maps country name to value                             │
│  ├── Handles country name variations automatically          │
│  └── Config: { column: "Country", UAE: 74903, KSA: 74904 }  │
│                                                             │
│  ORDER_PREFIX                                               │
│  ├── Extracts prefix from order ID                          │
│  ├── Maps prefix to value                                   │
│  └── Config: { column: "OrderNo", length: 4,                │
│                TUAE: 32028, TUSA: 32029 }                   │
│                                                             │
│  CONDITIONAL                                                │
│  ├── Evaluates conditions in order                          │
│  └── Config: { conditions: [                                │
│                  { when: "Currency == 'AED'", then: 13010 },│
│                  { when: "Currency == 'SAR'", then: 13009 } │
│                ]}                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Tax Calculation Strategies

```
┌─────────────────────────────────────────────────────────────┐
│                    TAX STRATEGIES                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SUBTRACT                                                   │
│  ├── pre_tax = total - tax_amount                           │
│  ├── Used when: Separate tax column exists                  │
│  └── Brands: Farm Rio, Ghawali, Yeda, Tumi                  │
│                                                             │
│  DIVIDE                                                     │
│  ├── pre_tax = total / (1 + tax_rate)                       │
│  ├── Or: pre_tax = total / tax_divisor                      │
│  ├── Used when: No tax column, only total with tax          │
│  └── Brands: Lacoste, Axel Arigato                          │
│                                                             │
│  PRE_CALCULATED                                             │
│  ├── pre_tax = value from dedicated column                  │
│  ├── Used when: System provides both columns                │
│  └── Brands: Elemis, Jacquemus                              │
│                                                             │
│  PERCENTAGE                                                 │
│  ├── pre_tax = total / (1 + percentage/100)                 │
│  ├── Used when: Tax rate varies by row                      │
│  └── Config: { rate_column: "Tax Rate" }                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 5: Data Flow Architecture

### 5.1 Complete Processing Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FILE UPLOAD                                 │
│  User uploads: ghawali_nov_2025.csv, TUMI_export.xlsx               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BRAND DETECTION                                  │
│  ┌─────────────────┐                                                │
│  │ Filename Match  │ → ghawali_nov → "Ghawali"                      │
│  │ (configurable)  │ → TUMI_export → "Tumi"                         │
│  └─────────────────┘                                                │
│  ┌─────────────────┐                                                │
│  │ Manual Override │ → User can reassign brand                      │
│  └─────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    SCHEMA VALIDATION                                │
│  Load brand config → Check required columns exist                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Ghawali requires: [Fulfillment Status, Fulfilled at, ...]    │  │
│  │ Found: [Fulfillment Status, Fulfilled at, Currency, ...]     │  │
│  │ Status: ✓ VALID                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Tumi requires: [OrderNo, Date created, Total, Tax, ...]      │  │
│  │ Found: [OrderNo, Date created, Total, Tax, Payment Status]   │  │
│  │ Status: ✓ VALID (Payment Status is optional)                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PIPELINE EXECUTION                               │
│                                                                     │
│  For each brand:                                                    │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ STEP 1: FILTER                                                 ││
│  │ Input:  1,245 rows                                             ││
│  │ Config: Fulfillment Status == "fulfilled"                      ││
│  │ Output: 1,102 rows (143 filtered out)                          ││
│  └────────────────────────────────────────────────────────────────┘│
│                          │                                          │
│                          ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ STEP 2: AGGREGATE (if configured)                              ││
│  │ Input:  1,102 rows (line items)                                ││
│  │ Config: Group by "OrderNo", sum Tax, max Total                 ││
│  │ Output: 487 rows (orders)                                      ││
│  └────────────────────────────────────────────────────────────────┘│
│                          │                                          │
│                          ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ STEP 3: TRANSFORM                                              ││
│  │ Input:  487 rows with source columns                           ││
│  │ Config: Apply all field mappings                               ││
│  │ Output: 487 rows with output schema                            ││
│  │                                                                ││
│  │ Per-row transformations:                                       ││
│  │ ┌────────────────────────────────────────────────────────────┐ ││
│  │ │ h_location    = lookup(Currency, {AED:13010, SAR:13009})  │ ││
│  │ │ h_bit_date    = format_date(Fulfilled at, auto, ISO)      │ ││
│  │ │ h_bit_currency = direct(Currency)                         │ ││
│  │ │ h_mobile      = format_phone(Shipping Country, Phone)     │ ││
│  │ │ h_original    = direct(Subtotal)                          │ ││
│  │ │ h_bit_amount  = subtract(Subtotal, Taxes)                 │ ││
│  │ └────────────────────────────────────────────────────────────┘ ││
│  └────────────────────────────────────────────────────────────────┘│
│                          │                                          │
│                          ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ STEP 4: VALIDATE OUTPUT                                        ││
│  │ Check: All required output columns populated                   ││
│  │ Check: Data types correct                                      ││
│  │ Check: No null values in required fields                       ││
│  │ Result: 485 valid, 2 with warnings (null location)             ││
│  └────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    OUTPUT GENERATION                                │
│  ┌─────────────────┐                                                │
│  │ Ghawali - NOV   │ → 485 rows, pipe-delimited, no header         │
│  │ 2025.csv        │                                                │
│  └─────────────────┘                                                │
│  ┌─────────────────┐                                                │
│  │ Tumi - NOV      │ → 312 rows, pipe-delimited, no header         │
│  │ 2025.csv        │                                                │
│  └─────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ERROR HANDLING STRATEGY                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  LEVEL 1: FILE ERRORS                                               │
│  ├── File not readable → Skip file, log error                       │
│  ├── Unknown format → Skip file, log error                          │
│  ├── No brand match → Prompt user for assignment                    │
│  └── Empty file → Skip with warning                                 │
│                                                                     │
│  LEVEL 2: SCHEMA ERRORS                                             │
│  ├── Missing required column → STOP, show clear error               │
│  ├── Missing optional column → Continue with warning                │
│  └── Column type mismatch → Attempt coercion, warn if fails         │
│                                                                     │
│  LEVEL 3: ROW ERRORS                                                │
│  ├── Invalid date format → Use null, log warning                    │
│  ├── Non-numeric amount → Use null, log warning                     │
│  ├── Unknown country → Use raw phone, log warning                   │
│  ├── Null required field → Quarantine row, continue                 │
│  └── Custom validation fail → Based on config (skip/warn/stop)      │
│                                                                     │
│  LEVEL 4: OUTPUT ERRORS                                             │
│  ├── Cannot write file → Retry, then fail with error                │
│  └── Disk full → Fail with clear error                              │
│                                                                     │
│  ERROR REPORT STRUCTURE:                                            │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │ {                                                              ││
│  │   "file": "ghawali_nov.csv",                                   ││
│  │   "brand": "Ghawali",                                          ││
│  │   "total_rows": 1245,                                          ││
│  │   "processed_rows": 1100,                                      ││
│  │   "filtered_rows": 143,                                        ││
│  │   "error_rows": 2,                                             ││
│  │   "warnings": [                                                ││
│  │     { "row": 45, "field": "h_bit_date", "message": "..." }     ││
│  │   ],                                                           ││
│  │   "quarantined": [                                             ││
│  │     { "row": 892, "reason": "Invalid phone format" }           ││
│  │   ]                                                            ││
│  │ }                                                              ││
│  └────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 6: Module Architecture

### 6.1 Backend Module Structure

```
backend/
├── config/
│   ├── global_config.yaml          # Global settings
│   ├── brands/                     # Per-brand configs
│   │   ├── ghawali.yaml
│   │   ├── tumi.yaml
│   │   └── ...
│   └── schemas/                    # JSON Schema for validation
│       ├── global_config.schema.json
│       └── brand_config.schema.json
│
├── core/
│   ├── config_loader.py            # Load & validate configs
│   ├── pipeline_engine.py          # Orchestrate processing
│   ├── schema_registry.py          # Manage input schemas
│   └── validation_engine.py        # Validate data
│
├── steps/                          # Pipeline step implementations
│   ├── base_step.py                # Abstract base class
│   ├── filter_step.py              # Filtering logic
│   ├── aggregate_step.py           # Aggregation logic
│   ├── transform_step.py           # Transformation logic
│   └── validate_step.py            # Output validation
│
├── transformers/                   # Field transformation implementations
│   ├── base_transformer.py         # Abstract base class
│   ├── static_transformer.py       # Static values
│   ├── direct_transformer.py       # Direct column copy
│   ├── lookup_transformer.py       # Lookup tables
│   ├── date_transformer.py         # Date parsing/formatting
│   ├── phone_transformer.py        # Phone formatting
│   ├── formula_transformer.py      # Expression evaluation
│   ├── currency_transformer.py     # Currency conversion
│   └── tax_transformer.py          # Tax calculations
│
├── strategies/                     # Strategy implementations
│   ├── location_strategies.py      # Location resolution
│   ├── currency_strategies.py      # Currency resolution
│   └── tax_strategies.py           # Tax calculation
│
├── io/                             # Input/Output handling
│   ├── file_reader.py              # CSV, Excel readers
│   ├── file_writer.py              # CSV, Excel writers
│   └── brand_detector.py           # Filename → brand matching
│
├── api/                            # REST API endpoints
│   ├── config_api.py               # CRUD for configurations
│   ├── process_api.py              # File processing endpoints
│   └── preview_api.py              # Data preview endpoints
│
└── utils/
    ├── country_normalizer.py       # Normalize country names
    ├── phone_formatter.py          # Phone formatting utilities
    └── expression_parser.py        # Formula expression parser
```

### 6.2 Key Class Interfaces

```python
# Abstract Pipeline Step
class PipelineStep(ABC):
    @abstractmethod
    def execute(self, df: DataFrame, config: dict, context: ProcessingContext) -> DataFrame:
        pass

    @abstractmethod
    def validate_config(self, config: dict) -> ValidationResult:
        pass

# Abstract Transformer
class FieldTransformer(ABC):
    @abstractmethod
    def transform(self, row: Series, config: dict, context: ProcessingContext) -> Any:
        pass

# Processing Context (shared state)
class ProcessingContext:
    global_config: GlobalConfig
    brand_config: BrandConfig
    current_step: str
    row_errors: List[RowError]
    warnings: List[Warning]

# Configuration Service
class ConfigService:
    def get_global_config() -> GlobalConfig
    def update_global_config(config: GlobalConfig) -> None
    def get_brand_config(brand_name: str) -> BrandConfig
    def update_brand_config(brand_name: str, config: BrandConfig) -> None
    def create_brand(config: BrandConfig) -> None
    def delete_brand(brand_name: str) -> None
    def list_brands() -> List[BrandSummary]
```

---

## Part 7: Frontend Integration Points

### 7.1 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/config/global` | GET/PUT | Global configuration |
| `/api/config/brands` | GET/POST | List/create brands |
| `/api/config/brands/{name}` | GET/PUT/DELETE | Single brand CRUD |
| `/api/process/upload` | POST | Upload files |
| `/api/process/detect-brand` | POST | Auto-detect brand from file |
| `/api/process/validate` | POST | Validate file against schema |
| `/api/process/preview` | POST | Preview transformation (first N rows) |
| `/api/process/execute` | POST | Execute full processing |
| `/api/process/download/{job_id}` | GET | Download processed files |

### 7.2 Real-Time Feedback

```
WebSocket: /ws/process/{job_id}

Messages:
→ { "type": "progress", "step": "filter", "percent": 45 }
→ { "type": "row_count", "input": 1245, "filtered": 143, "processed": 500 }
→ { "type": "warning", "row": 45, "message": "Invalid date format" }
→ { "type": "error", "row": 892, "message": "Missing required field" }
→ { "type": "complete", "summary": {...} }
```

### 7.3 Configuration UI Requirements

**Global Settings Editor:**
- Editable table for conversion rates
- Editable table for tax divisors
- Editable list for country phone codes
- Add/remove countries

**Brand Editor:**
- Visual pipeline builder (drag-drop steps)
- Column mapping interface (source → target)
- Lookup table editors
- Formula builder with column autocomplete
- Live preview panel

**File Processing:**
- Drag-drop upload zone
- Auto-detected brand with override dropdown
- Schema validation status
- Column mapping preview
- Row-level error display
- Progress indicator
- Download buttons

---

## Part 8: Extensibility & Future-Proofing

### 8.1 Adding a New Brand (Zero Code)

1. Create `brands/new_brand.yaml` via UI
2. Define input schema (required/optional columns)
3. Build pipeline (filter → aggregate → transform)
4. Map columns using visual interface
5. Test with sample file
6. Enable brand

### 8.2 Adding a New Country

1. Edit global config via UI
2. Add to `conversion_rates` (if USD conversion needed)
3. Add to `tax_divisors`
4. Add to `country_phone_codes` with patterns
5. Update individual brand location mappings as needed

### 8.3 Adding a New Transformation Type

1. Create new transformer class implementing `FieldTransformer`
2. Register in transformer factory
3. Add JSON Schema for config validation
4. UI automatically discovers new type

### 8.4 Adding a New Data Source

1. Create new reader class implementing `FileReader`
2. Register file extension handler
3. No changes to processing logic needed

### 8.5 Schema Evolution

```yaml
# Brand config versioning
brand:
  name: "Ghawali"
  config_version: "2.0"  # Schema version

# Migrations handled automatically
migrations:
  "1.0_to_2.0":
    - rename_field: { from: "amount_column", to: "total_column" }
    - add_field: { name: "tax_strategy", default: "subtract" }
```

---

## Part 9: Recommended Technology Stack

### 9.1 Backend Options

**Option A: Python (FastAPI)**
- Pros: Native pandas support, familiar to data teams, fast development
- Cons: GIL limits parallelism, requires Python runtime

**Option B: Node.js (Express/Fastify)**
- Pros: JavaScript full-stack, good streaming support, npm ecosystem
- Cons: Less mature data processing libraries, memory management

**Option C: Python Backend + JS Processing**
- Config management: Python FastAPI
- File processing: Browser-based with Papa Parse + custom transformers
- Pros: Best of both worlds, reduces server load
- Cons: Complexity, large file handling in browser

### 9.2 Recommendation: Python (FastAPI) + Pandas

**Rationale:**
1. Original script is Python/pandas - familiar territory
2. pandas handles all transformation patterns already
3. FastAPI provides modern async API with auto-docs
4. Easy to add workers for parallel processing later
5. YAML configs with Pydantic validation

### 9.3 Key Libraries

| Purpose | Library |
|---------|---------|
| API Framework | FastAPI |
| Data Processing | pandas, numpy |
| Config Validation | Pydantic, JSON Schema |
| File I/O | openpyxl (Excel), csv (CSV) |
| Expression Parsing | simpleeval (safe formula evaluation) |
| Date Parsing | dateutil (auto-detect formats) |
| Background Jobs | Celery or RQ (for large files) |
| WebSocket | FastAPI native |

---

## Part 10: Implementation Phases

### Phase 1: Core Engine (Foundation)
- Config loader with validation
- Pipeline engine with filter/transform steps
- Basic transformers (static, direct, lookup, date)
- File reader/writer
- CLI interface for testing

### Phase 2: Full Feature Parity
- Aggregation step
- All transformer types (phone, formula, currency, tax)
- All lookup strategies
- Error handling and reporting
- Match all 8 current brands

### Phase 3: API Layer
- REST API endpoints
- WebSocket progress streaming
- Config CRUD operations
- File upload handling

### Phase 4: UI Integration
- Connect UI to API
- Real-time processing feedback
- Configuration editors
- Preview functionality

### Phase 5: Advanced Features
- Parallel processing for large files
- Scheduled/automated processing
- Audit logging
- Config versioning and rollback
- Custom validation rules
