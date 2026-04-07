import { Package, Eye, ShoppingCart, AlertTriangle, Hash } from 'lucide-react';

const statCards = [
  { key: 'total_products', label: 'Total', icon: Package, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  { key: 'monitoring', label: 'Monitorizando', icon: Eye, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  { key: 'reserved', label: 'Reservados', icon: ShoppingCart, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { key: 'errors', label: 'Errores', icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
];

export default function StatsBar({ stats, loading }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {statCards.map(({ key, label, icon: Icon, color, bg }) => (
        <div
          key={key}
          className="bg-surface-800/60 border border-surface-700/40 rounded-xl p-4 animate-slide-up"
        >
          <div className="flex items-center gap-2 mb-2">
            <div className={`w-7 h-7 rounded-lg ${bg} flex items-center justify-center`}>
              <Icon size={14} className={color} />
            </div>
            <span className="text-xs text-surface-200/50 font-medium">{label}</span>
          </div>
          <p className="text-2xl font-bold text-white" style={{ fontFamily: 'var(--font-mono)' }}>
            {loading ? '—' : (stats?.[key] ?? 0)}
          </p>
        </div>
      ))}
    </div>
  );
}
