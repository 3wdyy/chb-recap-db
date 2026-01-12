import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Select, Modal } from '@/components/ui';
import { cn } from '@/lib/utils';
import {
  Upload,
  FileSpreadsheet,
  X,
  Play,
  Download,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Eye,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
} from 'lucide-react';
import { listBrands, previewFile, detectBrand, processFile, downloadProcessedFile } from '@/api/client';
import type { ProcessingJob, FilePreview, ProcessingResult, BrandSummary } from '@/types';

interface UploadedFile {
  file: File;
  preview?: FilePreview;
  detectedBrand?: string | null;
  selectedBrand?: string;
  status: 'pending' | 'previewing' | 'ready' | 'processing' | 'completed' | 'failed';
  result?: ProcessingResult;
  error?: string;
}

export function ProcessFiles() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [period, setPeriod] = useState('export');
  const [showPreview, setShowPreview] = useState<FilePreview | null>(null);
  const [showResults, setShowResults] = useState<ProcessingResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch available brands
  const { data: brandsData } = useQuery({
    queryKey: ['brands'],
    queryFn: listBrands,
  });

  const brands = brandsData?.brands || [];
  const enabledBrands = brands.filter(b => b.enabled);

  // Handle file drop
  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      f => f.name.endsWith('.csv') || f.name.endsWith('.xlsx') || f.name.endsWith('.xls')
    );

    await processDroppedFiles(droppedFiles);
  }, []);

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files ? Array.from(e.target.files) : [];
    await processDroppedFiles(selectedFiles);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const processDroppedFiles = async (newFiles: File[]) => {
    const uploadedFiles: UploadedFile[] = newFiles.map(file => ({
      file,
      status: 'previewing' as const,
    }));

    setFiles(prev => [...prev, ...uploadedFiles]);

    // Process each file
    for (let i = 0; i < uploadedFiles.length; i++) {
      const currentIndex = files.length + i;
      try {
        // Get preview and detect brand
        const [preview, detection] = await Promise.all([
          previewFile(newFiles[i], 5),
          detectBrand(newFiles[i]),
        ]);

        setFiles(prev => prev.map((f, idx) =>
          idx === currentIndex
            ? {
                ...f,
                preview: preview.previews[0],
                detectedBrand: detection.detected_brand,
                selectedBrand: detection.detected_brand || undefined,
                status: 'ready',
              }
            : f
        ));
      } catch (error) {
        setFiles(prev => prev.map((f, idx) =>
          idx === currentIndex
            ? { ...f, status: 'failed', error: 'Failed to read file' }
            : f
        ));
      }
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const updateFileBrand = (index: number, brand: string) => {
    setFiles(prev => prev.map((f, i) =>
      i === index ? { ...f, selectedBrand: brand } : f
    ));
  };

  const processAllFiles = async () => {
    const readyFiles = files.filter(f => f.status === 'ready' && f.selectedBrand);

    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (f.status !== 'ready' || !f.selectedBrand) continue;

      setFiles(prev => prev.map((file, idx) =>
        idx === i ? { ...file, status: 'processing' } : file
      ));

      try {
        const result = await processFile(f.file, f.selectedBrand, period);
        setFiles(prev => prev.map((file, idx) =>
          idx === i
            ? { ...file, status: 'completed', result: result.results[0] }
            : file
        ));
      } catch (error: any) {
        setFiles(prev => prev.map((file, idx) =>
          idx === i
            ? { ...file, status: 'failed', error: error.message || 'Processing failed' }
            : file
        ));
      }
    }
  };

  const downloadFile = async (file: UploadedFile) => {
    if (!file.selectedBrand) return;

    try {
      const blob = await downloadProcessedFile(file.file, file.selectedBrand, period);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${file.selectedBrand}_${period}_processed.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const readyCount = files.filter(f => f.status === 'ready' && f.selectedBrand).length;
  const completedCount = files.filter(f => f.status === 'completed').length;
  const failedCount = files.filter(f => f.status === 'failed').length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Process Files</h1>
          <p className="text-slate-500 mt-1">
            Upload e-commerce order files to transform into loyalty format
          </p>
        </div>
        {files.length > 0 && (
          <div className="flex items-center gap-3">
            <Select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-40"
            >
              <option value="export">Export Period</option>
              <option value="q1_2025">Q1 2025</option>
              <option value="q2_2025">Q2 2025</option>
              <option value="q3_2025">Q3 2025</option>
              <option value="q4_2025">Q4 2025</option>
            </Select>
            <Button
              onClick={processAllFiles}
              disabled={readyCount === 0}
              icon={<Play className="h-4 w-4" />}
            >
              Process {readyCount > 0 ? `(${readyCount})` : 'All'}
            </Button>
          </div>
        )}
      </div>

      {/* Drop Zone */}
      <Card
        className={cn(
          'border-2 border-dashed transition-all duration-200',
          isDragging
            ? 'border-brand-500 bg-brand-50/50 scale-[1.01]'
            : 'border-slate-300 hover:border-brand-400'
        )}
        padding="none"
      >
        <div
          className="p-12 text-center"
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".csv,.xlsx,.xls"
            onChange={handleFileInput}
            className="hidden"
          />

          <div className={cn(
            'mx-auto w-16 h-16 rounded-2xl flex items-center justify-center transition-colors',
            isDragging ? 'bg-brand-100 text-brand-600' : 'bg-slate-100 text-slate-400'
          )}>
            <Upload className="h-8 w-8" />
          </div>

          <h3 className="mt-4 text-lg font-semibold text-slate-900">
            Drop files here or click to upload
          </h3>
          <p className="mt-2 text-slate-500">
            Supports CSV, XLSX, and XLS files. Brand will be auto-detected.
          </p>

          <Button
            variant="outline"
            className="mt-6"
            onClick={() => fileInputRef.current?.click()}
          >
            Browse Files
          </Button>
        </div>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">
              Uploaded Files ({files.length})
            </h2>
            {completedCount > 0 && (
              <div className="flex items-center gap-4 text-sm">
                <span className="text-emerald-600">
                  <CheckCircle2 className="h-4 w-4 inline mr-1" />
                  {completedCount} completed
                </span>
                {failedCount > 0 && (
                  <span className="text-red-600">
                    <AlertCircle className="h-4 w-4 inline mr-1" />
                    {failedCount} failed
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="space-y-3">
            {files.map((file, index) => (
              <FileCard
                key={`${file.file.name}-${index}`}
                file={file}
                brands={enabledBrands}
                onRemove={() => removeFile(index)}
                onBrandChange={(brand) => updateFileBrand(index, brand)}
                onPreview={() => file.preview && setShowPreview(file.preview)}
                onViewResults={() => file.result && setShowResults(file.result)}
                onDownload={() => downloadFile(file)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {files.length === 0 && (
        <Card className="text-center py-12">
          <FileSpreadsheet className="h-12 w-12 mx-auto text-slate-300" />
          <h3 className="mt-4 font-medium text-slate-900">No files uploaded</h3>
          <p className="mt-2 text-sm text-slate-500">
            Drag and drop files above or click to browse
          </p>
        </Card>
      )}

      {/* Preview Modal */}
      <Modal
        isOpen={!!showPreview}
        onClose={() => setShowPreview(null)}
        title={`Preview: ${showPreview?.filename}`}
        size="xl"
      >
        {showPreview && (
          <div className="space-y-4">
            <div className="flex items-center gap-4 text-sm text-slate-600">
              <span>{showPreview.row_count.toLocaleString()} rows</span>
              <span>•</span>
              <span>{showPreview.column_count} columns</span>
            </div>
            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    {showPreview.columns.map((col) => (
                      <th key={col} className="px-3 py-2 text-left font-medium text-slate-600 whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {showPreview.preview_rows.map((row, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      {showPreview.columns.map((col) => (
                        <td key={col} className="px-3 py-2 text-slate-700 whitespace-nowrap">
                          {String(row[col] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Modal>

      {/* Results Modal */}
      <Modal
        isOpen={!!showResults}
        onClose={() => setShowResults(null)}
        title={`Processing Results: ${showResults?.brand_name}`}
        size="lg"
      >
        {showResults && <ProcessingResultsView result={showResults} />}
      </Modal>
    </div>
  );
}

interface FileCardProps {
  file: UploadedFile;
  brands: BrandSummary[];
  onRemove: () => void;
  onBrandChange: (brand: string) => void;
  onPreview: () => void;
  onViewResults: () => void;
  onDownload: () => void;
}

function FileCard({ file, brands, onRemove, onBrandChange, onPreview, onViewResults, onDownload }: FileCardProps) {
  const [expanded, setExpanded] = useState(false);

  const statusConfig = {
    pending: { color: 'bg-slate-100 text-slate-600', icon: null, label: 'Pending' },
    previewing: { color: 'bg-blue-100 text-blue-600', icon: <Loader2 className="h-3 w-3 animate-spin" />, label: 'Reading...' },
    ready: { color: 'bg-brand-100 text-brand-600', icon: null, label: 'Ready' },
    processing: { color: 'bg-amber-100 text-amber-600', icon: <Loader2 className="h-3 w-3 animate-spin" />, label: 'Processing...' },
    completed: { color: 'bg-emerald-100 text-emerald-600', icon: <CheckCircle2 className="h-3 w-3" />, label: 'Completed' },
    failed: { color: 'bg-red-100 text-red-600', icon: <AlertCircle className="h-3 w-3" />, label: 'Failed' },
  };

  const status = statusConfig[file.status];

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="p-4 flex items-center gap-4">
        {/* File Icon */}
        <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
          <FileSpreadsheet className="h-6 w-6 text-slate-400" />
        </div>

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-slate-900 truncate">{file.file.name}</span>
            <Badge className={status.color} size="sm">
              {status.icon}
              {status.label}
            </Badge>
          </div>
          <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
            <span>{(file.file.size / 1024).toFixed(1)} KB</span>
            {file.preview && (
              <>
                <span>•</span>
                <span>{file.preview.row_count.toLocaleString()} rows</span>
              </>
            )}
            {file.detectedBrand && (
              <>
                <span>•</span>
                <span className="text-brand-600">Detected: {file.detectedBrand}</span>
              </>
            )}
          </div>
        </div>

        {/* Brand Selector */}
        {(file.status === 'ready' || file.status === 'pending') && (
          <Select
            value={file.selectedBrand || ''}
            onChange={(e) => onBrandChange(e.target.value)}
            className="w-44"
          >
            <option value="">Select brand...</option>
            {brands.map((brand) => (
              <option key={brand.name} value={brand.name}>
                {brand.name}
              </option>
            ))}
          </Select>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          {file.preview && (
            <Button variant="ghost" size="sm" onClick={onPreview}>
              <Eye className="h-4 w-4" />
            </Button>
          )}
          {file.status === 'completed' && (
            <>
              <Button variant="ghost" size="sm" onClick={onViewResults}>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button variant="primary" size="sm" onClick={onDownload}>
                <Download className="h-4 w-4" />
              </Button>
            </>
          )}
          <Button variant="ghost" size="sm" onClick={onRemove} className="text-slate-400 hover:text-red-500">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Error Message */}
      {file.status === 'failed' && file.error && (
        <div className="px-4 pb-4">
          <div className="p-3 bg-red-50 rounded-lg text-sm text-red-600">
            <AlertCircle className="h-4 w-4 inline mr-2" />
            {file.error}
          </div>
        </div>
      )}

      {/* Results Summary */}
      {file.status === 'completed' && file.result && (
        <div className="px-4 pb-4">
          <div className="p-3 bg-emerald-50 rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-4 text-sm">
              <span className="text-emerald-700 font-medium">
                <CheckCircle2 className="h-4 w-4 inline mr-1" />
                {file.result.output_rows.toLocaleString()} rows processed
              </span>
              {file.result.warning_count > 0 && (
                <span className="text-amber-600">
                  <AlertTriangle className="h-4 w-4 inline mr-1" />
                  {file.result.warning_count} warnings
                </span>
              )}
            </div>
            <span className="text-xs text-emerald-600">
              {file.result.duration_ms}ms
            </span>
          </div>
        </div>
      )}
    </Card>
  );
}

function ProcessingResultsView({ result }: { result: ProcessingResult }) {
  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 bg-slate-50 rounded-lg text-center">
          <p className="text-2xl font-bold text-slate-900">{result.input_rows.toLocaleString()}</p>
          <p className="text-xs text-slate-500 mt-1">Input Rows</p>
        </div>
        <div className="p-4 bg-emerald-50 rounded-lg text-center">
          <p className="text-2xl font-bold text-emerald-600">{result.output_rows.toLocaleString()}</p>
          <p className="text-xs text-slate-500 mt-1">Output Rows</p>
        </div>
        <div className="p-4 bg-amber-50 rounded-lg text-center">
          <p className="text-2xl font-bold text-amber-600">{result.warning_count}</p>
          <p className="text-xs text-slate-500 mt-1">Warnings</p>
        </div>
        <div className="p-4 bg-red-50 rounded-lg text-center">
          <p className="text-2xl font-bold text-red-600">{result.error_count}</p>
          <p className="text-xs text-slate-500 mt-1">Errors</p>
        </div>
      </div>

      {/* Step Results */}
      {result.step_results.length > 0 && (
        <div>
          <h4 className="font-medium text-slate-900 mb-3">Pipeline Steps</h4>
          <div className="space-y-2">
            {result.step_results.map((step, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full bg-brand-100 text-brand-600 text-xs font-medium flex items-center justify-center">
                    {i + 1}
                  </div>
                  <span className="font-medium text-slate-700 capitalize">{step.step_name}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-slate-500">
                  <span>{step.input_rows} → {step.output_rows} rows</span>
                  {step.filtered_rows > 0 && (
                    <span className="text-amber-600">-{step.filtered_rows} filtered</span>
                  )}
                  <span className="text-xs">{step.duration_ms}ms</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div>
          <h4 className="font-medium text-slate-900 mb-3">Warnings ({result.warnings.length})</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {result.warnings.slice(0, 20).map((warning, i) => (
              <div key={i} className="p-3 bg-amber-50 rounded-lg text-sm">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-amber-700">{warning.message}</p>
                    {warning.row_index !== undefined && (
                      <p className="text-xs text-amber-600 mt-1">
                        Row {warning.row_index + 1}
                        {warning.column && ` • Column: ${warning.column}`}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Output Preview */}
      {result.output_preview && result.output_preview.length > 0 && (
        <div>
          <h4 className="font-medium text-slate-900 mb-3">Output Preview</h4>
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-xs">
              <thead className="bg-slate-50">
                <tr>
                  {Object.keys(result.output_preview[0]).map((col) => (
                    <th key={col} className="px-2 py-2 text-left font-medium text-slate-600 whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.output_preview.slice(0, 5).map((row, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="px-2 py-2 text-slate-700 whitespace-nowrap">
                        {String(val ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
