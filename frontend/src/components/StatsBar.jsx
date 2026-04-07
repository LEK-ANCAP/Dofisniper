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
          className={`bg-surface-900 border border-surface-700 p-4 animate-slide-up relative group overflow-hidden`}
        >
          {/* Subtle Top-Left Corner Accent */}
          <div className={`absolute top-0 left-0 w-1 h-full opacity-50 ${bg.replace('/10', '')}`} />

          <div className="flex items-center gap-2 mb-2">
            <div className={`w-6 h-6 border ${color.replace('text', 'border')}/30 flex items-center justify-center ${bg}`}>
              <Icon size={12} className={color} />
            </div>
            <span className="text-[10px] uppercase text-surface-400 font-bold tracking-widest">{label}</span>
          </div>
          <p className="text-2xl font-bold text-white tracking-widest mt-1 ml-1" style={{ textShadow: '0 0 10px rgba(255,255,255,0.1)' }}>
            {loading ? '—' : (stats?.[key] ?? 0)}
          </p>
        </div>
      ))}
    </div>
  );
}
