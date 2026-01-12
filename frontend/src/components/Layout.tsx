import { NavLink, Outlet } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Upload,
  Settings,
  Tags,
  FileText,
  ChevronRight,
  Zap,
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Process Files', href: '/process', icon: Upload },
  { name: 'Brands', href: '/brands', icon: Tags },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Layout() {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-white border-r border-slate-200 z-30">
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-100">
          <div className="w-9 h-9 rounded-lg gradient-brand flex items-center justify-center">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-slate-900">E-Comm Processor</h1>
            <p className="text-xs text-slate-500">Order Transformer</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                )
              }
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-100">
          <div className="p-4 bg-gradient-to-br from-brand-50 to-blue-50 rounded-lg">
            <div className="flex items-center gap-2 text-brand-700 font-medium text-sm mb-2">
              <FileText className="h-4 w-4" />
              Documentation
            </div>
            <p className="text-xs text-slate-600 mb-3">
              Learn how to configure brands and process files.
            </p>
            <a
              href="#"
              className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
            >
              View Docs
              <ChevronRight className="h-3 w-3" />
            </a>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="pl-64">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
