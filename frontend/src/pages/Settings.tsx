import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Input, Select, Modal } from '@/components/ui';
import { cn } from '@/lib/utils';
import {
  Save,
  Plus,
  Trash2,
  RefreshCw,
  DollarSign,
  Percent,
  Phone,
  Globe,
  FileOutput,
  AlertCircle,
  CheckCircle2,
  Edit2,
  X,
} from 'lucide-react';
import { getGlobalConfig, updateGlobalConfig } from '@/api/client';
import type { GlobalConfig, PhoneCodeConfig } from '@/types';

export function Settings() {
  const queryClient = useQueryClient();
  const [hasChanges, setHasChanges] = useState(false);
  const [config, setConfig] = useState<GlobalConfig | null>(null);
  const [activeTab, setActiveTab] = useState<'rates' | 'taxes' | 'phones' | 'countries' | 'output'>('rates');
  const [editingPhoneCode, setEditingPhoneCode] = useState<number | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['globalConfig'],
    queryFn: getGlobalConfig,
  });

  useEffect(() => {
    if (data) {
      setConfig(data);
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (updates: Partial<GlobalConfig>) => updateGlobalConfig(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['globalConfig'] });
      setHasChanges(false);
    },
  });

  const updateConfig = (updates: Partial<GlobalConfig>) => {
    setConfig(prev => prev ? { ...prev, ...updates } : null);
    setHasChanges(true);
  };

  const tabs = [
    { id: 'rates', label: 'Conversion Rates', icon: DollarSign },
    { id: 'taxes', label: 'Tax Divisors', icon: Percent },
    { id: 'phones', label: 'Phone Codes', icon: Phone },
    { id: 'countries', label: 'Countries', icon: Globe },
    { id: 'output', label: 'Output Format', icon: FileOutput },
  ] as const;

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-48" />
        <div className="h-96 bg-slate-200 rounded" />
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto text-red-400" />
        <h3 className="mt-4 font-medium text-slate-900">Failed to load settings</h3>
        <p className="mt-2 text-sm text-slate-500">{(error as Error)?.message || 'Unknown error'}</p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Global Settings</h1>
          <p className="text-slate-500 mt-1">
            Configure conversion rates, tax settings, and output format
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => refetch()}
            disabled={saveMutation.isPending}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Reload
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

      {/* Success Message */}
      {saveMutation.isSuccess && !hasChanges && (
        <div className="flex items-center gap-2 p-4 bg-emerald-50 text-emerald-700 rounded-lg">
          <CheckCircle2 className="h-5 w-5" />
          <span className="font-medium">Settings saved successfully!</span>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-brand-500 text-brand-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === 'rates' && (
          <ConversionRatesEditor
            rates={config.conversion_rates}
            onChange={(rates) => updateConfig({ conversion_rates: rates })}
          />
        )}

        {activeTab === 'taxes' && (
          <TaxDivisorsEditor
            divisors={config.tax_divisors}
            onChange={(divisors) => updateConfig({ tax_divisors: divisors })}
          />
        )}

        {activeTab === 'phones' && (
          <PhoneCodesEditor
            codes={config.country_phone_codes}
            onChange={(codes) => updateConfig({ country_phone_codes: codes })}
          />
        )}

        {activeTab === 'countries' && (
          <CountriesEditor
            countries={config.supported_countries}
            onChange={(countries) => updateConfig({ supported_countries: countries })}
          />
        )}

        {activeTab === 'output' && (
          <OutputFormatEditor
            output={config.output}
            onChange={(output) => updateConfig({ output })}
          />
        )}
      </div>
    </div>
  );
}

interface ConversionRatesEditorProps {
  rates: Record<string, number>;
  onChange: (rates: Record<string, number>) => void;
}

function ConversionRatesEditor({ rates, onChange }: ConversionRatesEditorProps) {
  const [newCountry, setNewCountry] = useState('');
  const [newRate, setNewRate] = useState('');

  const addRate = () => {
    if (newCountry && newRate) {
      onChange({ ...rates, [newCountry]: parseFloat(newRate) });
      setNewCountry('');
      setNewRate('');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>USD Conversion Rates</CardTitle>
        <p className="text-sm text-slate-500">Convert from USD to local currency for each country</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Object.entries(rates).map(([country, rate]) => (
            <div key={country} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <div className="flex-1">
                <span className="font-medium text-slate-900">{country}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">$1 USD =</span>
                <Input
                  type="number"
                  step="0.01"
                  value={rate}
                  onChange={(e) => onChange({ ...rates, [country]: parseFloat(e.target.value) })}
                  className="w-24 text-right"
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const newRates = { ...rates };
                  delete newRates[country];
                  onChange(newRates);
                }}
                className="text-slate-400 hover:text-red-500"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}

          <div className="flex items-center gap-3 pt-3 border-t border-slate-200">
            <Input
              placeholder="Country name"
              value={newCountry}
              onChange={(e) => setNewCountry(e.target.value)}
              className="flex-1"
            />
            <Input
              type="number"
              step="0.01"
              placeholder="Rate"
              value={newRate}
              onChange={(e) => setNewRate(e.target.value)}
              className="w-24"
            />
            <Button onClick={addRate} disabled={!newCountry || !newRate}>
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface TaxDivisorsEditorProps {
  divisors: Record<string, number>;
  onChange: (divisors: Record<string, number>) => void;
}

function TaxDivisorsEditor({ divisors, onChange }: TaxDivisorsEditorProps) {
  const [newCountry, setNewCountry] = useState('');
  const [newDivisor, setNewDivisor] = useState('');

  const addDivisor = () => {
    if (newCountry && newDivisor) {
      onChange({ ...divisors, [newCountry]: parseFloat(newDivisor) });
      setNewCountry('');
      setNewDivisor('');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tax Divisors</CardTitle>
        <p className="text-sm text-slate-500">Divide gross amount by divisor to get net amount (e.g., 1.05 for 5% VAT)</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Object.entries(divisors).map(([country, divisor]) => (
            <div key={country} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <div className="flex-1">
                <span className="font-medium text-slate-900">{country}</span>
                <span className="text-sm text-slate-500 ml-2">
                  ({((divisor - 1) * 100).toFixed(0)}% VAT)
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">÷</span>
                <Input
                  type="number"
                  step="0.01"
                  value={divisor}
                  onChange={(e) => onChange({ ...divisors, [country]: parseFloat(e.target.value) })}
                  className="w-24 text-right"
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const newDivisors = { ...divisors };
                  delete newDivisors[country];
                  onChange(newDivisors);
                }}
                className="text-slate-400 hover:text-red-500"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}

          <div className="flex items-center gap-3 pt-3 border-t border-slate-200">
            <Input
              placeholder="Country name"
              value={newCountry}
              onChange={(e) => setNewCountry(e.target.value)}
              className="flex-1"
            />
            <Input
              type="number"
              step="0.01"
              placeholder="Divisor"
              value={newDivisor}
              onChange={(e) => setNewDivisor(e.target.value)}
              className="w-24"
            />
            <Button onClick={addDivisor} disabled={!newCountry || !newDivisor}>
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface PhoneCodesEditorProps {
  codes: PhoneCodeConfig[];
  onChange: (codes: PhoneCodeConfig[]) => void;
}

function PhoneCodesEditor({ codes, onChange }: PhoneCodesEditorProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingCode, setEditingCode] = useState<PhoneCodeConfig | null>(null);

  const startEdit = (index: number) => {
    setEditingIndex(index);
    setEditingCode({ ...codes[index] });
  };

  const saveEdit = () => {
    if (editingIndex !== null && editingCode) {
      const newCodes = [...codes];
      newCodes[editingIndex] = editingCode;
      onChange(newCodes);
      setEditingIndex(null);
      setEditingCode(null);
    }
  };

  const addNew = () => {
    const newCode: PhoneCodeConfig = {
      patterns: ['New Country'],
      code: '+1',
      digits_to_keep: 9,
    };
    onChange([...codes, newCode]);
    setEditingIndex(codes.length);
    setEditingCode(newCode);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Phone Country Codes</CardTitle>
          <p className="text-sm text-slate-500">Format phone numbers with country codes</p>
        </div>
        <Button variant="outline" onClick={addNew}>
          <Plus className="h-4 w-4 mr-1" />
          Add Code
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {codes.map((config, index) => (
            <div key={index} className="p-4 bg-slate-50 rounded-lg">
              {editingIndex === index && editingCode ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label="Country Code"
                      value={editingCode.code}
                      onChange={(e) => setEditingCode({ ...editingCode, code: e.target.value })}
                      placeholder="+971"
                    />
                    <Input
                      label="Digits to Keep"
                      type="number"
                      value={editingCode.digits_to_keep}
                      onChange={(e) => setEditingCode({ ...editingCode, digits_to_keep: parseInt(e.target.value) })}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Country Name Patterns (one per line)
                    </label>
                    <textarea
                      value={editingCode.patterns.join('\n')}
                      onChange={(e) => setEditingCode({
                        ...editingCode,
                        patterns: e.target.value.split('\n').filter(Boolean)
                      })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                      rows={3}
                      placeholder="United Arab Emirates&#10;UAE&#10;Dubai"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => { setEditingIndex(null); setEditingCode(null); }}
                    >
                      Cancel
                    </Button>
                    <Button size="sm" onClick={saveEdit}>
                      Save
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="font-mono">{config.code}</Badge>
                      <span className="font-medium text-slate-900">
                        {config.patterns[0]}
                      </span>
                      {config.patterns.length > 1 && (
                        <span className="text-sm text-slate-500">
                          +{config.patterns.length - 1} more
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-500 mt-1">
                      Keep last {config.digits_to_keep} digits
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => startEdit(index)}
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onChange(codes.filter((_, i) => i !== index))}
                      className="text-slate-400 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface CountriesEditorProps {
  countries: string[];
  onChange: (countries: string[]) => void;
}

function CountriesEditor({ countries, onChange }: CountriesEditorProps) {
  const [newCountry, setNewCountry] = useState('');

  const addCountry = () => {
    if (newCountry && !countries.includes(newCountry)) {
      onChange([...countries, newCountry]);
      setNewCountry('');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Supported Countries</CardTitle>
        <p className="text-sm text-slate-500">Countries that will be processed (others are filtered out)</p>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2 mb-4">
          {countries.map((country) => (
            <div
              key={country}
              className="flex items-center gap-2 bg-slate-100 rounded-lg px-3 py-2 group"
            >
              <Globe className="h-4 w-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-700">{country}</span>
              <button
                onClick={() => onChange(countries.filter(c => c !== country))}
                className="text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Input
            placeholder="Add country..."
            value={newCountry}
            onChange={(e) => setNewCountry(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addCountry()}
            className="flex-1"
          />
          <Button onClick={addCountry} disabled={!newCountry}>
            <Plus className="h-4 w-4 mr-1" />
            Add
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

interface OutputFormatEditorProps {
  output: GlobalConfig['output'];
  onChange: (output: GlobalConfig['output']) => void;
}

function OutputFormatEditor({ output, onChange }: OutputFormatEditorProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Output Format</CardTitle>
        <p className="text-sm text-slate-500">Configure the format of processed output files</p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-6">
          <Input
            label="Delimiter"
            value={output.delimiter}
            onChange={(e) => onChange({ ...output, delimiter: e.target.value })}
            placeholder=","
          />
          <Input
            label="Date Format"
            value={output.date_format}
            onChange={(e) => onChange({ ...output, date_format: e.target.value })}
            placeholder="%d/%m/%Y"
          />
          <Input
            label="Encoding"
            value={output.encoding}
            onChange={(e) => onChange({ ...output, encoding: e.target.value })}
            placeholder="utf-8-sig"
          />
          <Input
            label="Filename Template"
            value={output.filename_template}
            onChange={(e) => onChange({ ...output, filename_template: e.target.value })}
            placeholder="{brand}_{period}_processed.csv"
          />

          <div className="col-span-2 flex items-center gap-6">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={output.include_header}
                onChange={(e) => onChange({ ...output, include_header: e.target.checked })}
                className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-sm text-slate-700">Include Header Row</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={output.include_index}
                onChange={(e) => onChange({ ...output, include_index: e.target.checked })}
                className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              <span className="text-sm text-slate-700">Include Index Column</span>
            </label>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
