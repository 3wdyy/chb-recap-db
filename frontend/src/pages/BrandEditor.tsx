import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Input, Select, Modal } from '@/components/ui';
import { cn, getBrandColor } from '@/lib/utils';
import {
  ArrowLeft,
  Save,
  Plus,
  Trash2,
  GripVertical,
  ChevronDown,
  ChevronRight,
  Filter,
  Layers,
  Settings,
  AlertCircle,
  CheckCircle2,
  Play,
  Code,
  Eye,
  Copy,
} from 'lucide-react';
import { getBrandConfig, updateBrandConfig, createBrand } from '@/api/client';
import type { BrandConfig, PipelineStep, FilterConfig, AggregateConfig, TransformConfig, FieldMapping } from '@/types';

const STEP_ICONS: Record<string, React.ElementType> = {
  filter: Filter,
  aggregate: Layers,
  transform: Settings,
  validate: CheckCircle2,
};

const STEP_COLORS: Record<string, string> = {
  filter: 'bg-amber-100 text-amber-600',
  aggregate: 'bg-purple-100 text-purple-600',
  transform: 'bg-blue-100 text-blue-600',
  validate: 'bg-emerald-100 text-emerald-600',
};

export function BrandEditor() {
  const { brandName } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isNew = !brandName;

  const [config, setConfig] = useState<BrandConfig | null>(null);
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [showJson, setShowJson] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch existing config
  const { data, isLoading, error } = useQuery({
    queryKey: ['brand', brandName],
    queryFn: () => getBrandConfig(brandName!),
    enabled: !isNew,
  });

  useEffect(() => {
    if (data) {
      setConfig(data);
    } else if (isNew) {
      setConfig(getDefaultConfig());
    }
  }, [data, isNew]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (config: BrandConfig) => {
      if (isNew) {
        await createBrand(config);
      } else {
        await updateBrandConfig(brandName!, config);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      queryClient.invalidateQueries({ queryKey: ['brand', brandName] });
      setHasChanges(false);
      if (isNew && config) {
        navigate(`/brands/${encodeURIComponent(config.brand.name)}`);
      }
    },
  });

  const updateConfig = (updates: Partial<BrandConfig>) => {
    setConfig(prev => prev ? { ...prev, ...updates } : null);
    setHasChanges(true);
  };

  const addPipelineStep = (type: PipelineStep['step']) => {
    if (!config) return;

    const newStep: PipelineStep = {
      step: type,
      config: getDefaultStepConfig(type),
    };

    updateConfig({
      pipeline: [...config.pipeline, newStep],
    });
    setActiveStep(config.pipeline.length);
  };

  const removeStep = (index: number) => {
    if (!config) return;
    updateConfig({
      pipeline: config.pipeline.filter((_, i) => i !== index),
    });
    if (activeStep === index) {
      setActiveStep(null);
    }
  };

  const updateStep = (index: number, updates: Partial<PipelineStep>) => {
    if (!config) return;
    updateConfig({
      pipeline: config.pipeline.map((step, i) =>
        i === index ? { ...step, ...updates } : step
      ),
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-48" />
        <div className="h-64 bg-slate-200 rounded" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto text-red-400" />
        <h3 className="mt-4 font-medium text-slate-900">Failed to load brand</h3>
        <p className="mt-2 text-sm text-slate-500">{(error as Error).message}</p>
        <Link to="/brands">
          <Button variant="outline" className="mt-4">Back to Brands</Button>
        </Link>
      </div>
    );
  }

  if (!config) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/brands">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div className="flex items-center gap-3">
            <div className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold',
              getBrandColor(config.brand.name || 'New')
            )}>
              {(config.brand.name || 'N').slice(0, 2).toUpperCase()}
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">
                {isNew ? 'New Brand' : config.brand.name}
              </h1>
              <p className="text-sm text-slate-500">{config.brand.description}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            onClick={() => setShowJson(true)}
          >
            <Code className="h-4 w-4 mr-2" />
            View JSON
          </Button>
          <Button
            onClick={() => saveMutation.mutate(config)}
            disabled={saveMutation.isPending || !hasChanges}
            icon={<Save className="h-4 w-4" />}
          >
            {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Brand Info & Input Schema */}
        <div className="space-y-6">
          {/* Brand Info */}
          <Card>
            <CardHeader>
              <CardTitle>Brand Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                label="Brand Name"
                value={config.brand.name}
                onChange={(e) => updateConfig({
                  brand: { ...config.brand, name: e.target.value }
                })}
                disabled={!isNew}
              />
              <Input
                label="Description"
                value={config.brand.description}
                onChange={(e) => updateConfig({
                  brand: { ...config.brand, description: e.target.value }
                })}
              />
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="enabled"
                  checked={config.brand.enabled}
                  onChange={(e) => updateConfig({
                    brand: { ...config.brand, enabled: e.target.checked }
                  })}
                  className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                <label htmlFor="enabled" className="text-sm text-slate-700">
                  Enable brand for processing
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Input Schema */}
          <Card>
            <CardHeader>
              <CardTitle>Input Schema</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select
                label="Platform"
                value={config.input_schema.platform}
                onChange={(e) => updateConfig({
                  input_schema: { ...config.input_schema, platform: e.target.value }
                })}
              >
                <option value="shopify">Shopify</option>
                <option value="salesforce">Salesforce</option>
                <option value="custom">Custom</option>
              </Select>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Required Columns
                </label>
                <div className="space-y-2">
                  {config.input_schema.required_columns.map((col, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <Input
                        value={col}
                        onChange={(e) => {
                          const cols = [...config.input_schema.required_columns];
                          cols[i] = e.target.value;
                          updateConfig({
                            input_schema: { ...config.input_schema, required_columns: cols }
                          });
                        }}
                        className="flex-1"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          updateConfig({
                            input_schema: {
                              ...config.input_schema,
                              required_columns: config.input_schema.required_columns.filter((_, j) => j !== i)
                            }
                          });
                        }}
                        className="text-slate-400 hover:text-red-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => updateConfig({
                      input_schema: {
                        ...config.input_schema,
                        required_columns: [...config.input_schema.required_columns, '']
                      }
                    })}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Column
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Filename Patterns */}
          <Card>
            <CardHeader>
              <CardTitle>Filename Patterns</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {config.filename_patterns.map((pattern, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      value={pattern}
                      onChange={(e) => {
                        const patterns = [...config.filename_patterns];
                        patterns[i] = e.target.value;
                        updateConfig({ filename_patterns: patterns });
                      }}
                      placeholder="e.g., ghawali*.csv"
                      className="flex-1 font-mono text-sm"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => updateConfig({
                        filename_patterns: config.filename_patterns.filter((_, j) => j !== i)
                      })}
                      className="text-slate-400 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateConfig({
                    filename_patterns: [...config.filename_patterns, '']
                  })}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add Pattern
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Middle Column - Pipeline Steps */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Processing Pipeline</CardTitle>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => addPipelineStep('filter')}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Filter
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => addPipelineStep('aggregate')}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Aggregate
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => addPipelineStep('transform')}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Transform
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {config.pipeline.length === 0 ? (
                <div className="text-center py-8 border-2 border-dashed border-slate-200 rounded-lg">
                  <Layers className="h-8 w-8 mx-auto text-slate-300" />
                  <p className="mt-2 text-sm text-slate-500">
                    No pipeline steps defined. Add a step to get started.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {config.pipeline.map((step, index) => {
                    const Icon = STEP_ICONS[step.step];
                    const isActive = activeStep === index;

                    return (
                      <div key={index}>
                        <div
                          className={cn(
                            'flex items-center gap-3 p-4 rounded-lg border transition-all cursor-pointer',
                            isActive
                              ? 'border-brand-500 bg-brand-50/50 shadow-sm'
                              : 'border-slate-200 hover:border-brand-300 hover:bg-slate-50'
                          )}
                          onClick={() => setActiveStep(isActive ? null : index)}
                        >
                          <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', STEP_COLORS[step.step])}>
                            <Icon className="h-4 w-4" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-slate-900 capitalize">{step.step}</span>
                              <Badge variant="outline" size="sm">Step {index + 1}</Badge>
                            </div>
                            <p className="text-xs text-slate-500 mt-0.5">
                              {getStepDescription(step)}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => { e.stopPropagation(); removeStep(index); }}
                              className="text-slate-400 hover:text-red-500"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                            {isActive ? (
                              <ChevronDown className="h-4 w-4 text-slate-400" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-slate-400" />
                            )}
                          </div>
                        </div>

                        {/* Step Configuration Panel */}
                        {isActive && (
                          <div className="mt-2 ml-11 p-4 bg-slate-50 rounded-lg border border-slate-200">
                            <StepConfigEditor
                              step={step}
                              onChange={(updates) => updateStep(index, updates)}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Output Columns */}
          <Card>
            <CardHeader>
              <CardTitle>Output Columns</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {config.output_columns.map((col, i) => (
                  <div key={i} className="flex items-center gap-1 bg-slate-100 rounded-lg px-3 py-1.5 group">
                    <span className="text-sm font-mono text-slate-700">{col}</span>
                    <button
                      onClick={() => updateConfig({
                        output_columns: config.output_columns.filter((_, j) => j !== i)
                      })}
                      className="text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => {
                    const col = prompt('Enter column name:');
                    if (col) {
                      updateConfig({
                        output_columns: [...config.output_columns, col]
                      });
                    }
                  }}
                  className="flex items-center gap-1 text-sm text-brand-600 hover:text-brand-700 px-3 py-1.5"
                >
                  <Plus className="h-3 w-3" />
                  Add
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* JSON Preview Modal */}
      <Modal
        isOpen={showJson}
        onClose={() => setShowJson(false)}
        title="Configuration JSON"
        size="lg"
      >
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 right-2"
            onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(config, null, 2));
            }}
          >
            <Copy className="h-4 w-4 mr-1" />
            Copy
          </Button>
          <pre className="p-4 bg-slate-900 text-slate-100 rounded-lg overflow-auto max-h-[60vh] text-sm font-mono">
            {JSON.stringify(config, null, 2)}
          </pre>
        </div>
      </Modal>
    </div>
  );
}

interface StepConfigEditorProps {
  step: PipelineStep;
  onChange: (updates: Partial<PipelineStep>) => void;
}

function StepConfigEditor({ step, onChange }: StepConfigEditorProps) {
  switch (step.step) {
    case 'filter':
      return <FilterStepEditor config={step.config as FilterConfig} onChange={(config) => onChange({ config })} />;
    case 'aggregate':
      return <AggregateStepEditor config={step.config as AggregateConfig} onChange={(config) => onChange({ config })} />;
    case 'transform':
      return <TransformStepEditor config={step.config as TransformConfig} onChange={(config) => onChange({ config })} />;
    default:
      return <div className="text-sm text-slate-500">Configuration not available for this step type.</div>;
  }
}

function FilterStepEditor({ config, onChange }: { config: FilterConfig; onChange: (config: FilterConfig) => void }) {
  return (
    <div className="space-y-4">
      <Select
        label="Filter Mode"
        value={config.mode || 'all_of'}
        onChange={(e) => onChange({ ...config, mode: e.target.value as 'all_of' | 'any_of' })}
      >
        <option value="all_of">All conditions must match</option>
        <option value="any_of">Any condition must match</option>
      </Select>

      <div className="space-y-3">
        <label className="text-sm font-medium text-slate-700">Conditions</label>
        {config.conditions.map((condition, i) => (
          <div key={i} className="flex items-start gap-2 p-3 bg-white rounded-lg border border-slate-200">
            <div className="flex-1 grid grid-cols-3 gap-2">
              <Input
                placeholder="Column"
                value={condition.column}
                onChange={(e) => {
                  const conditions = [...config.conditions];
                  conditions[i] = { ...condition, column: e.target.value };
                  onChange({ ...config, conditions });
                }}
              />
              <Select
                value={condition.operator}
                onChange={(e) => {
                  const conditions = [...config.conditions];
                  conditions[i] = { ...condition, operator: e.target.value };
                  onChange({ ...config, conditions });
                }}
              >
                <option value="eq">Equals</option>
                <option value="neq">Not Equals</option>
                <option value="contains">Contains</option>
                <option value="in">In List</option>
                <option value="gt">Greater Than</option>
                <option value="lt">Less Than</option>
              </Select>
              <Input
                placeholder="Value"
                value={String(condition.value)}
                onChange={(e) => {
                  const conditions = [...config.conditions];
                  conditions[i] = { ...condition, value: e.target.value };
                  onChange({ ...config, conditions });
                }}
              />
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onChange({
                ...config,
                conditions: config.conditions.filter((_, j) => j !== i)
              })}
              className="text-slate-400 hover:text-red-500"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange({
            ...config,
            conditions: [...config.conditions, { column: '', operator: 'eq', value: '' }]
          })}
        >
          <Plus className="h-4 w-4 mr-1" />
          Add Condition
        </Button>
      </div>
    </div>
  );
}

function AggregateStepEditor({ config, onChange }: { config: AggregateConfig; onChange: (config: AggregateConfig) => void }) {
  return (
    <div className="space-y-4">
      <Input
        label="Group By Column"
        value={config.group_by}
        onChange={(e) => onChange({ ...config, group_by: e.target.value })}
        placeholder="e.g., OrderNo"
      />

      <div className="space-y-3">
        <label className="text-sm font-medium text-slate-700">Aggregations</label>
        {Object.entries(config.aggregations).map(([key, agg], i) => (
          <div key={i} className="flex items-start gap-2 p-3 bg-white rounded-lg border border-slate-200">
            <div className="flex-1 grid grid-cols-3 gap-2">
              <Input
                placeholder="Output Column"
                value={key}
                onChange={(e) => {
                  const aggregations = { ...config.aggregations };
                  delete aggregations[key];
                  aggregations[e.target.value] = agg;
                  onChange({ ...config, aggregations });
                }}
              />
              <Input
                placeholder="Source Column"
                value={agg.source}
                onChange={(e) => {
                  const aggregations = { ...config.aggregations };
                  aggregations[key] = { ...agg, source: e.target.value };
                  onChange({ ...config, aggregations });
                }}
              />
              <Select
                value={agg.function}
                onChange={(e) => {
                  const aggregations = { ...config.aggregations };
                  aggregations[key] = { ...agg, function: e.target.value };
                  onChange({ ...config, aggregations });
                }}
              >
                <option value="first">First</option>
                <option value="sum">Sum</option>
                <option value="count">Count</option>
                <option value="max">Max</option>
                <option value="min">Min</option>
              </Select>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const aggregations = { ...config.aggregations };
                delete aggregations[key];
                onChange({ ...config, aggregations });
              }}
              className="text-slate-400 hover:text-red-500"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            const key = `column_${Object.keys(config.aggregations).length + 1}`;
            onChange({
              ...config,
              aggregations: { ...config.aggregations, [key]: { source: '', function: 'first' } }
            });
          }}
        >
          <Plus className="h-4 w-4 mr-1" />
          Add Aggregation
        </Button>
      </div>
    </div>
  );
}

function TransformStepEditor({ config, onChange }: { config: TransformConfig; onChange: (config: TransformConfig) => void }) {
  const [selectedField, setSelectedField] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <label className="text-sm font-medium text-slate-700">Field Mappings</label>
      <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
        {Object.entries(config.mappings).map(([fieldName, mapping]) => (
          <div
            key={fieldName}
            className={cn(
              'p-3 rounded-lg border cursor-pointer transition-all',
              selectedField === fieldName
                ? 'border-brand-500 bg-brand-50'
                : 'border-slate-200 hover:border-brand-300'
            )}
            onClick={() => setSelectedField(selectedField === fieldName ? null : fieldName)}
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm text-slate-700">{fieldName}</span>
              <Badge variant="outline" size="sm">{mapping.type}</Badge>
            </div>
          </div>
        ))}
        <button
          onClick={() => {
            const fieldName = prompt('Enter field name:');
            if (fieldName && !config.mappings[fieldName]) {
              onChange({
                ...config,
                mappings: { ...config.mappings, [fieldName]: { type: 'static', value: '' } }
              });
            }
          }}
          className="p-3 rounded-lg border-2 border-dashed border-slate-200 hover:border-brand-300 text-sm text-slate-500 hover:text-brand-600 transition-colors"
        >
          <Plus className="h-4 w-4 mx-auto mb-1" />
          Add Field
        </button>
      </div>

      {selectedField && config.mappings[selectedField] && (
        <div className="p-4 bg-white rounded-lg border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-slate-900">{selectedField}</h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                const mappings = { ...config.mappings };
                delete mappings[selectedField];
                onChange({ ...config, mappings });
                setSelectedField(null);
              }}
              className="text-red-500"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
          <FieldMappingEditor
            mapping={config.mappings[selectedField]}
            onChange={(mapping) => {
              onChange({
                ...config,
                mappings: { ...config.mappings, [selectedField]: mapping }
              });
            }}
          />
        </div>
      )}
    </div>
  );
}

function FieldMappingEditor({ mapping, onChange }: { mapping: FieldMapping; onChange: (mapping: FieldMapping) => void }) {
  return (
    <div className="space-y-4">
      <Select
        label="Transform Type"
        value={mapping.type}
        onChange={(e) => onChange({ ...mapping, type: e.target.value })}
      >
        <option value="static">Static Value</option>
        <option value="direct">Direct Copy</option>
        <option value="lookup">Lookup</option>
        <option value="date">Date Format</option>
        <option value="phone">Phone Format</option>
        <option value="formula">Formula</option>
        <option value="currency_convert">Currency Convert</option>
        <option value="tax_exclude">Tax Exclude</option>
        <option value="clean">Clean</option>
        <option value="conditional">Conditional</option>
      </Select>

      {mapping.type === 'static' && (
        <Input
          label="Value"
          value={String(mapping.value || '')}
          onChange={(e) => onChange({ ...mapping, value: e.target.value })}
        />
      )}

      {mapping.type === 'direct' && (
        <Input
          label="Source Column"
          value={mapping.source_column || ''}
          onChange={(e) => onChange({ ...mapping, source_column: e.target.value })}
        />
      )}

      {mapping.type === 'formula' && (
        <div className="space-y-3">
          <Input
            label="Expression"
            value={mapping.formula?.expression || ''}
            onChange={(e) => onChange({
              ...mapping,
              formula: { ...mapping.formula, expression: e.target.value }
            })}
            placeholder="e.g., {subtotal} - {tax}"
          />
          <p className="text-xs text-slate-500">
            Use {"{"}"column_name{"}"} to reference columns. Supports COALESCE(col, default).
          </p>
        </div>
      )}

      {mapping.type === 'date' && (
        <div className="grid grid-cols-3 gap-3">
          <Input
            label="Source Column"
            value={mapping.date?.source_column || ''}
            onChange={(e) => onChange({
              ...mapping,
              date: { ...mapping.date!, source_column: e.target.value }
            })}
          />
          <Input
            label="Input Format"
            value={mapping.date?.input_format || ''}
            onChange={(e) => onChange({
              ...mapping,
              date: { ...mapping.date!, input_format: e.target.value }
            })}
            placeholder="%Y-%m-%d"
          />
          <Input
            label="Output Format"
            value={mapping.date?.output_format || ''}
            onChange={(e) => onChange({
              ...mapping,
              date: { ...mapping.date!, output_format: e.target.value }
            })}
            placeholder="%d/%m/%Y"
          />
        </div>
      )}

      {mapping.type === 'phone' && (
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Country Column"
            value={mapping.phone?.country_column || ''}
            onChange={(e) => onChange({
              ...mapping,
              phone: { ...mapping.phone!, country_column: e.target.value }
            })}
          />
          <Input
            label="Phone Column"
            value={mapping.phone?.phone_column || ''}
            onChange={(e) => onChange({
              ...mapping,
              phone: { ...mapping.phone!, phone_column: e.target.value }
            })}
          />
        </div>
      )}
    </div>
  );
}

function getDefaultConfig(): BrandConfig {
  return {
    brand: {
      name: '',
      enabled: true,
      description: '',
    },
    input_schema: {
      platform: 'custom',
      required_columns: [],
      optional_columns: [],
    },
    pipeline: [],
    output_columns: [
      'h_location',
      'h_bit_date',
      'h_ext_reference',
      'h_mobile_number',
      'h_bit_currency',
      'h_bit_amount',
      'h_original_bit_currency',
      'h_original_bit_amount',
    ],
    filename_patterns: [],
  };
}

function getDefaultStepConfig(type: PipelineStep['step']): any {
  switch (type) {
    case 'filter':
      return { mode: 'all_of', conditions: [] };
    case 'aggregate':
      return { group_by: '', aggregations: {} };
    case 'transform':
      return { mappings: {} };
    default:
      return {};
  }
}

function getStepDescription(step: PipelineStep): string {
  switch (step.step) {
    case 'filter': {
      const config = step.config as FilterConfig;
      return `${config.conditions.length} condition(s), ${config.mode || 'all_of'} mode`;
    }
    case 'aggregate': {
      const config = step.config as AggregateConfig;
      return `Group by ${config.group_by || '(not set)'}, ${Object.keys(config.aggregations).length} aggregation(s)`;
    }
    case 'transform': {
      const config = step.config as TransformConfig;
      return `${Object.keys(config.mappings).length} field mapping(s)`;
    }
    default:
      return '';
  }
}
