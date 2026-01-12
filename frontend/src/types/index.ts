// Global Configuration Types
export interface PhoneCodeConfig {
  patterns: string[];
  code: string;
  digits_to_keep: number;
}

export interface OutputConfig {
  delimiter: string;
  include_header: boolean;
  include_index: boolean;
  date_format: string;
  encoding: string;
  filename_template: string;
}

export interface GlobalConfig {
  version: string;
  conversion_rates: Record<string, number>;
  tax_divisors: Record<string, number>;
  country_phone_codes: PhoneCodeConfig[];
  supported_countries: string[];
  output: OutputConfig;
}

// Brand Configuration Types
export interface BrandInfo {
  name: string;
  enabled: boolean;
  description: string;
}

export interface InputSchema {
  platform: string;
  required_columns: string[];
  optional_columns: string[];
}

export interface FilterCondition {
  column: string;
  operator: string;
  value: string | string[] | number;
  case_sensitive?: boolean;
  skip_if_column_missing?: boolean;
}

export interface FilterConfig {
  mode?: 'all_of' | 'any_of';
  conditions: FilterCondition[];
}

export interface AggregationRule {
  source: string;
  function: string;
  coerce_numeric?: boolean;
}

export interface AggregateConfig {
  group_by: string;
  aggregations: Record<string, AggregationRule>;
}

export interface FieldMapping {
  type: string;
  value?: any;
  source_column?: string;
  transform?: string;
  lookup?: {
    strategy: string;
    source_column: string;
    mapping: Record<string, any>;
    default?: any;
    prefix_length?: number;
  };
  date?: {
    source_column: string;
    input_format: string;
    output_format: string;
  };
  phone?: {
    country_column: string;
    phone_column: string;
  };
  formula?: {
    expression: string;
    coerce_numeric?: boolean;
  };
  currency?: {
    source_column: string;
    source_currency: string;
    target_currency_column: string;
    rates_ref: string;
  };
  tax?: {
    strategy: string;
    amount_column: string;
    tax_column?: string;
    pre_tax_column?: string;
    divisor_lookup_column?: string;
    divisors_ref?: string;
  };
}

export interface TransformConfig {
  mappings: Record<string, FieldMapping>;
}

export interface PipelineStep {
  step: 'filter' | 'aggregate' | 'transform' | 'validate';
  config: FilterConfig | AggregateConfig | TransformConfig | Record<string, any>;
}

export interface BrandConfig {
  brand: BrandInfo;
  input_schema: InputSchema;
  pipeline: PipelineStep[];
  output_columns: string[];
  filename_patterns: string[];
}

export interface BrandSummary {
  name: string;
  enabled: boolean;
  description: string;
  platform: string;
}

// Processing Types
export interface ProcessingError {
  row_index: number;
  column: string | null;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  original_value?: string;
}

export interface StepResult {
  step_name: string;
  input_rows: number;
  output_rows: number;
  filtered_rows: number;
  error_count: number;
  warning_count: number;
  duration_ms: number;
}

export interface ProcessingResult {
  brand_name: string;
  source_file: string | null;
  success: boolean;
  input_rows: number;
  output_rows: number;
  error_count: number;
  warning_count: number;
  quarantined_count: number;
  duration_ms: number;
  started_at: string | null;
  completed_at: string | null;
  output_file: string | null;
  step_results: StepResult[];
  errors: ProcessingError[];
  warnings: ProcessingError[];
  output_preview?: Record<string, any>[];
}

export interface FilePreview {
  filename: string;
  sheet_name: string | null;
  row_count: number;
  column_count: number;
  columns: string[];
  preview_rows: Record<string, any>[];
}

export interface PreviewResponse {
  file_count: number;
  total_rows: number;
  previews: FilePreview[];
  detected_brand: string | null;
  available_brands: string[];
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  row_count: number;
  columns_found: string[];
}

// UI State Types
export interface ProcessingJob {
  id: string;
  filename: string;
  brand: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result?: ProcessingResult;
  error?: string;
}
