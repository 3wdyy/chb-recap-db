import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, Button, Badge, Input, Modal } from '@/components/ui';
import { cn, getBrandColor, getPlatformInfo } from '@/lib/utils';
import {
  Plus,
  Search,
  MoreVertical,
  Edit2,
  Trash2,
  Copy,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  FileSpreadsheet,
  Zap,
} from 'lucide-react';
import { listBrands, deleteBrand } from '@/api/client';
import type { BrandSummary } from '@/types';

export function Brands() {
  const [search, setSearch] = useState('');
  const [filterEnabled, setFilterEnabled] = useState<boolean | null>(null);
  const [deleteModal, setDeleteModal] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['brands'],
    queryFn: listBrands,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBrand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      setDeleteModal(null);
    },
  });

  const brands = data?.brands || [];

  const filteredBrands = brands.filter(brand => {
    const matchesSearch = brand.name.toLowerCase().includes(search.toLowerCase()) ||
      brand.description.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filterEnabled === null || brand.enabled === filterEnabled;
    return matchesSearch && matchesFilter;
  });

  const enabledCount = brands.filter(b => b.enabled).length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Brand Configurations</h1>
          <p className="text-slate-500 mt-1">
            Manage e-commerce brand processing pipelines
          </p>
        </div>
        <Link to="/brands/new">
          <Button icon={<Plus className="h-4 w-4" />}>
            Add Brand
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card padding="none">
          <div className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center">
              <Zap className="h-6 w-6 text-brand-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{brands.length}</p>
              <p className="text-sm text-slate-500">Total Brands</p>
            </div>
          </div>
        </Card>
        <Card padding="none">
          <div className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center">
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{enabledCount}</p>
              <p className="text-sm text-slate-500">Active Brands</p>
            </div>
          </div>
        </Card>
        <Card padding="none">
          <div className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
              <FileSpreadsheet className="h-6 w-6 text-slate-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{brands.length - enabledCount}</p>
              <p className="text-sm text-slate-500">Disabled Brands</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search brands..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={filterEnabled === null ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setFilterEnabled(null)}
          >
            All
          </Button>
          <Button
            variant={filterEnabled === true ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setFilterEnabled(true)}
          >
            Active
          </Button>
          <Button
            variant={filterEnabled === false ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setFilterEnabled(false)}
          >
            Disabled
          </Button>
        </div>
      </div>

      {/* Brand Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-slate-200" />
                  <div className="flex-1">
                    <div className="h-5 bg-slate-200 rounded w-24 mb-2" />
                    <div className="h-4 bg-slate-200 rounded w-32" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredBrands.length === 0 ? (
        <Card className="text-center py-12">
          <AlertCircle className="h-12 w-12 mx-auto text-slate-300" />
          <h3 className="mt-4 font-medium text-slate-900">No brands found</h3>
          <p className="mt-2 text-sm text-slate-500">
            {search ? 'Try a different search term' : 'Add a new brand to get started'}
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredBrands.map((brand) => (
            <BrandCard
              key={brand.name}
              brand={brand}
              onDelete={() => setDeleteModal(brand.name)}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteModal}
        onClose={() => setDeleteModal(null)}
        title="Delete Brand"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-slate-600">
            Are you sure you want to delete <strong>{deleteModal}</strong>? This action cannot be undone.
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setDeleteModal(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              className="bg-red-600 hover:bg-red-700"
              onClick={() => deleteModal && deleteMutation.mutate(deleteModal)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

interface BrandCardProps {
  brand: BrandSummary;
  onDelete: () => void;
}

function BrandCard({ brand, onDelete }: BrandCardProps) {
  const [showMenu, setShowMenu] = useState(false);
  const platform = getPlatformInfo(brand.platform);

  return (
    <Card hover className="group relative">
      <CardContent>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className={cn(
              'w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg',
              getBrandColor(brand.name)
            )}>
              {brand.name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-slate-900">{brand.name}</h3>
                <Badge variant={brand.enabled ? 'success' : 'default'} size="sm">
                  {brand.enabled ? 'Active' : 'Disabled'}
                </Badge>
              </div>
              <p className="text-sm text-slate-500 mt-1 line-clamp-1">
                {brand.description}
              </p>
            </div>
          </div>

          {/* Menu Button */}
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreVertical className="h-4 w-4" />
            </button>

            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <div className="absolute right-0 top-8 z-20 w-40 bg-white rounded-lg shadow-lg border border-slate-200 py-1">
                  <Link
                    to={`/brands/${encodeURIComponent(brand.name)}`}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    <Edit2 className="h-4 w-4" />
                    Edit
                  </Link>
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      // Copy config
                    }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 w-full text-left"
                  >
                    <Copy className="h-4 w-4" />
                    Duplicate
                  </button>
                  <hr className="my-1 border-slate-100" />
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      onDelete();
                    }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Platform Badge */}
        <div className="mt-4 flex items-center gap-2">
          <Badge variant="outline" size="sm" className={platform.color}>
            {platform.label}
          </Badge>
        </div>

        {/* Quick Actions */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
          <Link
            to={`/brands/${encodeURIComponent(brand.name)}`}
            className="text-sm font-medium text-brand-600 hover:text-brand-700 flex items-center gap-1"
          >
            Configure Pipeline
            <ExternalLink className="h-3 w-3" />
          </Link>
          <Link to="/process" className="text-sm text-slate-500 hover:text-slate-700">
            Process Files →
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
