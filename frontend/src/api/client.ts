import axios from 'axios';
import type {
  GlobalConfig,
  BrandConfig,
  BrandSummary,
  PreviewResponse,
  ValidationResult,
  ProcessingResult,
} from '@/types';

// Check if we're in demo mode (no backend available)
const DEMO_MODE = import.meta.env.PROD && !import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Demo data for GitHub Pages deployment
const DEMO_BRANDS: BrandSummary[] = [
  { name: 'Ghawali', enabled: true, description: 'Premium fragrances - UAE market', platform: 'shopify' },
  { name: 'Tumi', enabled: true, description: 'Luxury travel bags', platform: 'salesforce' },
  { name: 'Lacoste', enabled: true, description: 'Fashion and sportswear', platform: 'shopify' },
  { name: 'Farm Rio', enabled: true, description: 'Brazilian fashion brand', platform: 'shopify' },
  { name: 'Jacquemus', enabled: true, description: 'French luxury fashion', platform: 'shopify' },
  { name: 'Yeda', enabled: true, description: 'Beauty and cosmetics', platform: 'custom' },
  { name: 'Elemis', enabled: true, description: 'Skincare products', platform: 'shopify' },
  { name: 'Axel Arigato', enabled: false, description: 'Scandinavian streetwear', platform: 'shopify' },
];

const DEMO_GLOBAL_CONFIG: GlobalConfig = {
  version: '1.0.0',
  conversion_rates: {
    'United Arab Emirates': 3.67,
    'Saudi Arabia': 3.75,
    'Kuwait': 0.31,
    'Bahrain': 0.38,
    'Qatar': 3.64,
    'Oman': 0.39,
  },
  tax_divisors: {
    'United Arab Emirates': 1.05,
    'Saudi Arabia': 1.15,
    'France': 1.20,
    'United Kingdom': 1.20,
  },
  country_phone_codes: [
    { patterns: ['United Arab Emirates', 'UAE', 'Dubai'], code: '+971', digits_to_keep: 9 },
    { patterns: ['Saudi Arabia', 'KSA'], code: '+966', digits_to_keep: 9 },
    { patterns: ['Kuwait'], code: '+965', digits_to_keep: 8 },
    { patterns: ['Bahrain'], code: '+973', digits_to_keep: 8 },
    { patterns: ['Qatar'], code: '+974', digits_to_keep: 8 },
    { patterns: ['Oman'], code: '+968', digits_to_keep: 8 },
  ],
  supported_countries: [
    'United Arab Emirates',
    'Saudi Arabia',
    'Kuwait',
    'Bahrain',
    'Qatar',
    'Oman',
  ],
  output: {
    delimiter: ',',
    include_header: true,
    include_index: false,
    date_format: '%d/%m/%Y',
    encoding: 'utf-8-sig',
    filename_template: '{brand}_{period}_processed.csv',
  },
};

// Global Config
export async function getGlobalConfig(): Promise<GlobalConfig> {
  if (DEMO_MODE) {
    return DEMO_GLOBAL_CONFIG;
  }
  const { data } = await api.get('/config/global');
  return data;
}

export async function updateGlobalConfig(updates: Partial<GlobalConfig>): Promise<GlobalConfig> {
  if (DEMO_MODE) {
    console.log('Demo mode: Config update simulated', updates);
    return { ...DEMO_GLOBAL_CONFIG, ...updates };
  }
  const { data } = await api.put('/config/global', updates);
  return data.config;
}

// Brand Config
export async function listBrands(): Promise<{ brands: BrandSummary[] }> {
  if (DEMO_MODE) {
    return { brands: DEMO_BRANDS };
  }
  const { data } = await api.get('/config/brands');
  return data;
}

export async function getBrandConfig(brandName: string): Promise<BrandConfig> {
  if (DEMO_MODE) {
    const brand = DEMO_BRANDS.find(b => b.name === brandName);
    if (!brand) throw new Error('Brand not found');
    return {
      brand: { name: brand.name, enabled: brand.enabled, description: brand.description },
      input_schema: { platform: brand.platform, required_columns: ['Email', 'Name'], optional_columns: [] },
      pipeline: [
        { step: 'filter', config: { mode: 'all_of', conditions: [{ column: 'status', operator: 'eq', value: 'paid' }] } },
        { step: 'aggregate', config: { group_by: 'order_id', aggregations: { total: { source: 'amount', function: 'sum' } } } },
        { step: 'transform', config: { mappings: { h_location: { type: 'static', value: 'UAE' } } } },
      ],
      output_columns: ['h_location', 'h_bit_date', 'h_ext_reference', 'h_mobile_number', 'h_bit_currency', 'h_bit_amount'],
      filename_patterns: [`${brandName.toLowerCase()}*.csv`],
    };
  }
  const { data } = await api.get(`/config/brands/${encodeURIComponent(brandName)}`);
  return data;
}

export async function updateBrandConfig(brandName: string, config: BrandConfig): Promise<void> {
  if (DEMO_MODE) {
    console.log('Demo mode: Brand config update simulated', brandName, config);
    return;
  }
  await api.put(`/config/brands/${encodeURIComponent(brandName)}`, config);
}

export async function createBrand(config: BrandConfig): Promise<void> {
  if (DEMO_MODE) {
    console.log('Demo mode: Brand creation simulated', config);
    return;
  }
  await api.post('/config/brands', config);
}

export async function deleteBrand(brandName: string): Promise<void> {
  if (DEMO_MODE) {
    console.log('Demo mode: Brand deletion simulated', brandName);
    return;
  }
  await api.delete(`/config/brands/${encodeURIComponent(brandName)}`);
}

// File Processing
export async function detectBrand(file: File): Promise<{ filename: string; detected_brand: string | null; available_brands: string[] }> {
  if (DEMO_MODE) {
    const filename = file.name.toLowerCase();
    const detected = DEMO_BRANDS.find(b => filename.includes(b.name.toLowerCase()))?.name || null;
    return { filename: file.name, detected_brand: detected, available_brands: DEMO_BRANDS.map(b => b.name) };
  }
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/process/detect-brand', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function previewFile(file: File, maxRows: number = 10): Promise<PreviewResponse> {
  if (DEMO_MODE) {
    // Parse CSV/Excel file for preview in demo mode
    const text = await file.text();
    const lines = text.split('\n').filter(l => l.trim());
    const columns = lines[0]?.split(',').map(c => c.trim().replace(/"/g, '')) || [];
    const previewRows = lines.slice(1, maxRows + 1).map(line => {
      const values = line.split(',').map(v => v.trim().replace(/"/g, ''));
      return columns.reduce((obj, col, i) => ({ ...obj, [col]: values[i] || '' }), {});
    });
    return {
      file_count: 1,
      total_rows: lines.length - 1,
      previews: [{
        filename: file.name,
        sheet_name: null,
        row_count: lines.length - 1,
        column_count: columns.length,
        columns,
        preview_rows: previewRows,
      }],
      detected_brand: null,
      available_brands: DEMO_BRANDS.map(b => b.name),
    };
  }
  const formData = new FormData();
  formData.append('file', file);
  formData.append('max_rows', maxRows.toString());
  const { data } = await api.post('/process/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function validateFile(file: File, brand: string): Promise<ValidationResult> {
  if (DEMO_MODE) {
    return { valid: true, errors: [], warnings: [], row_count: 100, columns_found: ['Email', 'Name', 'Amount'] };
  }
  const formData = new FormData();
  formData.append('file', file);
  formData.append('brand', brand);
  const { data } = await api.post('/process/validate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function processFile(
  file: File,
  brand: string,
  period: string = 'export'
): Promise<{ success: boolean; results: ProcessingResult[] }> {
  if (DEMO_MODE) {
    // Simulate processing in demo mode
    await new Promise(r => setTimeout(r, 1500));
    return {
      success: true,
      results: [{
        brand_name: brand,
        source_file: file.name,
        success: true,
        input_rows: 150,
        output_rows: 142,
        error_count: 0,
        warning_count: 3,
        quarantined_count: 8,
        duration_ms: 234,
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        output_file: `${brand}_${period}_processed.csv`,
        step_results: [
          { step_name: 'filter', input_rows: 150, output_rows: 148, filtered_rows: 2, error_count: 0, warning_count: 0, duration_ms: 12 },
          { step_name: 'aggregate', input_rows: 148, output_rows: 145, filtered_rows: 3, error_count: 0, warning_count: 1, duration_ms: 45 },
          { step_name: 'transform', input_rows: 145, output_rows: 142, filtered_rows: 3, error_count: 0, warning_count: 2, duration_ms: 177 },
        ],
        errors: [],
        warnings: [
          { row_index: 23, column: 'phone', message: 'Invalid phone format', severity: 'warning' },
          { row_index: 67, column: 'email', message: 'Missing email address', severity: 'warning' },
          { row_index: 89, column: 'amount', message: 'Zero amount detected', severity: 'warning' },
        ],
      }],
    };
  }
  const formData = new FormData();
  formData.append('file', file);
  formData.append('brand', brand);
  formData.append('period', period);
  const { data } = await api.post('/process/execute', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function downloadProcessedFile(
  file: File,
  brand: string,
  period: string = 'export'
): Promise<Blob> {
  if (DEMO_MODE) {
    // Generate a demo CSV file
    const csv = `h_location,h_bit_date,h_ext_reference,h_mobile_number,h_bit_currency,h_bit_amount
UAE,15/01/2025,ORD-001,+971501234567,AED,150.00
UAE,15/01/2025,ORD-002,+971502345678,AED,275.50
UAE,16/01/2025,ORD-003,+971503456789,AED,89.99`;
    return new Blob([csv], { type: 'text/csv' });
  }
  const formData = new FormData();
  formData.append('file', file);
  formData.append('brand', brand);
  formData.append('period', period);
  const { data } = await api.post('/process/download', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  });
  return data;
}

export async function processBatch(
  files: File[],
  period: string = 'export'
): Promise<{ total_files: number; successful: number; results: ProcessingResult[] }> {
  if (DEMO_MODE) {
    const results = await Promise.all(files.map(f => processFile(f, 'Demo', period)));
    return { total_files: files.length, successful: files.length, results: results.flatMap(r => r.results) };
  }
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('period', period);
  const { data } = await api.post('/process/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export default api;
