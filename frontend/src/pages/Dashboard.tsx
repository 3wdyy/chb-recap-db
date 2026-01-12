import { Link } from 'react-router-dom';
import { Card, CardContent, CardTitle, Button, Badge } from '@/components/ui';
import { cn, getBrandColor, getPlatformInfo } from '@/lib/utils';
import {
  Upload,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Tags,
  FileSpreadsheet,
  TrendingUp,
  Settings,
  Zap,
  ArrowUpRight,
} from 'lucide-react';

// Mock data - will be replaced with API calls
const stats = [
  { name: 'Active Brands', value: '8', change: '+2', icon: Tags, color: 'bg-blue-500' },
  { name: 'Files Processed', value: '1,234', change: '+12%', icon: FileSpreadsheet, color: 'bg-emerald-500' },
  { name: 'Success Rate', value: '99.2%', change: '+0.5%', icon: TrendingUp, color: 'bg-purple-500' },
  { name: 'Orders Transformed', value: '45.2K', change: '+8.3%', icon: Zap, color: 'bg-amber-500' },
];

const brands = [
  { name: 'Ghawali', platform: 'shopify', enabled: true, lastProcessed: '2 hours ago', orders: 1234 },
  { name: 'Tumi', platform: 'salesforce', enabled: true, lastProcessed: '5 hours ago', orders: 856 },
  { name: 'Lacoste', platform: 'custom', enabled: true, lastProcessed: '1 day ago', orders: 2341 },
  { name: 'Farm Rio', platform: 'shopify', enabled: true, lastProcessed: '3 hours ago', orders: 567 },
  { name: 'Jacquemus', platform: 'salesforce', enabled: true, lastProcessed: '6 hours ago', orders: 432 },
  { name: 'Axel Arigato', platform: 'custom', enabled: false, lastProcessed: 'Never', orders: 0 },
];

const recentActivity = [
  { type: 'success', brand: 'Ghawali', file: 'ghawali_nov_2025.csv', rows: 234, time: '2 hours ago' },
  { type: 'success', brand: 'Tumi', file: 'TUMI_export.xlsx', rows: 156, time: '5 hours ago' },
  { type: 'warning', brand: 'Lacoste', file: 'lacoste_orders.csv', rows: 89, time: '1 day ago' },
  { type: 'success', brand: 'Farm Rio', file: 'farm_rio_fulfilled.csv', rows: 312, time: '1 day ago' },
];

export function Dashboard() {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500 mt-1">
            Transform e-commerce orders into loyalty system format
          </p>
        </div>
        <Link to="/process">
          <Button icon={<Upload className="h-4 w-4" />}>
            Process Files
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <Card key={stat.name} hover className="group">
            <CardContent>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">{stat.name}</p>
                  <p className="text-2xl font-bold text-slate-900 mt-1">{stat.value}</p>
                  <div className="flex items-center gap-1 mt-2">
                    <ArrowUpRight className="h-3 w-3 text-emerald-500" />
                    <span className="text-xs font-medium text-emerald-600">{stat.change}</span>
                    <span className="text-xs text-slate-400">vs last month</span>
                  </div>
                </div>
                <div className={cn('p-3 rounded-xl', stat.color, 'bg-opacity-10 group-hover:bg-opacity-20 transition-colors')}>
                  <stat.icon className={cn('h-6 w-6', stat.color.replace('bg-', 'text-'))} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Brands Overview */}
        <div className="lg:col-span-2">
          <Card padding="none">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <div>
                <CardTitle>Brand Configurations</CardTitle>
                <p className="text-sm text-slate-500 mt-1">Manage your e-commerce brand pipelines</p>
              </div>
              <Link to="/brands">
                <Button variant="ghost" size="sm">
                  View All
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </div>
            <div className="divide-y divide-slate-100">
              {brands.slice(0, 5).map((brand) => {
                const platform = getPlatformInfo(brand.platform);
                return (
                  <div
                    key={brand.name}
                    className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center text-white font-semibold text-sm', getBrandColor(brand.name))}>
                        {brand.name.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-900">{brand.name}</span>
                          <Badge variant={brand.enabled ? 'success' : 'default'} size="sm">
                            {brand.enabled ? 'Active' : 'Disabled'}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 mt-1">
                          <Badge variant="outline" size="sm" className={platform.color}>
                            {platform.label}
                          </Badge>
                          <span className="text-xs text-slate-400">
                            Last: {brand.lastProcessed}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-slate-900">{brand.orders.toLocaleString()}</p>
                      <p className="text-xs text-slate-500">orders processed</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Recent Activity */}
        <div>
          <Card padding="none">
            <div className="p-6 border-b border-slate-100">
              <CardTitle>Recent Activity</CardTitle>
              <p className="text-sm text-slate-500 mt-1">Latest processing jobs</p>
            </div>
            <div className="divide-y divide-slate-100">
              {recentActivity.map((activity, i) => (
                <div key={i} className="p-4 flex items-start gap-3">
                  <div className={cn(
                    'p-1.5 rounded-full mt-0.5',
                    activity.type === 'success' ? 'bg-emerald-100' : 'bg-amber-100'
                  )}>
                    {activity.type === 'success' ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-amber-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {activity.file}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-slate-500">{activity.brand}</span>
                      <span className="text-xs text-slate-400">•</span>
                      <span className="text-xs text-slate-500">{activity.rows} rows</span>
                    </div>
                  </div>
                  <span className="text-xs text-slate-400 shrink-0">{activity.time}</span>
                </div>
              ))}
            </div>
            <div className="p-4 border-t border-slate-100">
              <Link to="/process" className="text-sm font-medium text-brand-600 hover:text-brand-700">
                View all activity →
              </Link>
            </div>
          </Card>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card hover className="group cursor-pointer" onClick={() => window.location.href = '/process'}>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-brand-100 text-brand-600 group-hover:bg-brand-600 group-hover:text-white transition-colors">
                <Upload className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900">Process Files</h3>
                <p className="text-sm text-slate-500">Upload and transform orders</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card hover className="group cursor-pointer" onClick={() => window.location.href = '/brands'}>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-purple-100 text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                <Tags className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900">Manage Brands</h3>
                <p className="text-sm text-slate-500">Configure processing pipelines</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card hover className="group cursor-pointer" onClick={() => window.location.href = '/settings'}>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-slate-100 text-slate-600 group-hover:bg-slate-600 group-hover:text-white transition-colors">
                <Settings className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900">Global Settings</h3>
                <p className="text-sm text-slate-500">Rates, taxes & phone codes</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
