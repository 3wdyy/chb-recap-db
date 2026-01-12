import axios from 'axios';
import type {
  GlobalConfig,
  BrandConfig,
  BrandSummary,
  PreviewResponse,
  ValidationResult,
  ProcessingResult,
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Global Config
export async function getGlobalConfig(): Promise<GlobalConfig> {
  const { data } = await api.get('/config/global');
  return data;
}

export async function updateGlobalConfig(updates: Partial<GlobalConfig>): Promise<GlobalConfig> {
  const { data } = await api.put('/config/global', updates);
  return data.config;
}

// Brand Config
export async function listBrands(): Promise<{ brands: BrandSummary[] }> {
  const { data } = await api.get('/config/brands');
  return data;
}

export async function getBrandConfig(brandName: string): Promise<BrandConfig> {
  const { data } = await api.get(`/config/brands/${encodeURIComponent(brandName)}`);
  return data;
}

export async function updateBrandConfig(brandName: string, config: BrandConfig): Promise<void> {
  await api.put(`/config/brands/${encodeURIComponent(brandName)}`, config);
}

export async function createBrand(config: BrandConfig): Promise<void> {
  await api.post('/config/brands', config);
}

export async function deleteBrand(brandName: string): Promise<void> {
  await api.delete(`/config/brands/${encodeURIComponent(brandName)}`);
}

// File Processing
export async function detectBrand(file: File): Promise<{ filename: string; detected_brand: string | null; available_brands: string[] }> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/process/detect-brand', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function previewFile(file: File, maxRows: number = 10): Promise<PreviewResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('max_rows', maxRows.toString());
  const { data } = await api.post('/process/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function validateFile(file: File, brand: string): Promise<ValidationResult> {
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
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('period', period);
  const { data } = await api.post('/process/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export default api;
