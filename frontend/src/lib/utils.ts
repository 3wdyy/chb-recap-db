import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat().format(num);
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function slugify(str: string): string {
  return str
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '');
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 11);
}

// Brand color mapping
const brandColors: Record<string, string> = {
  'Ghawali': 'bg-amber-500',
  'Tumi': 'bg-slate-700',
  'Lacoste': 'bg-green-600',
  'Farm Rio': 'bg-pink-500',
  'Jacquemus': 'bg-orange-400',
  'Yeda': 'bg-purple-500',
  'Elemis': 'bg-teal-500',
  'Axel Arigato': 'bg-gray-800',
};

export function getBrandColor(brand: string): string {
  return brandColors[brand] || 'bg-brand-500';
}

// Platform icons/colors
export function getPlatformInfo(platform: string): { color: string; label: string } {
  const platforms: Record<string, { color: string; label: string }> = {
    shopify: { color: 'bg-green-100 text-green-700', label: 'Shopify' },
    salesforce: { color: 'bg-blue-100 text-blue-700', label: 'Salesforce' },
    custom: { color: 'bg-purple-100 text-purple-700', label: 'Custom' },
  };
  return platforms[platform.toLowerCase()] || { color: 'bg-slate-100 text-slate-700', label: platform };
}
