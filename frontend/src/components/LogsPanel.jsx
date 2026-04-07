import { RefreshCw, CheckCircle, AlertTriangle, Info, XCircle, Trash2, Terminal } from 'lucide-react';

const LEVEL_CONFIG = {
  info: { icon: Info, color: 'text-blue-400', dot: 'bg-blue-400' },
  success: { icon: CheckCircle, color: 'text-emerald-400', dot: 'bg-emerald-400' },
  warning: { icon: AlertTriangle, color: 'text-amber-400', dot: 'bg-amber-400' },
  error: { icon: XCircle, color: 'text-red-400', dot: 'bg-red-400' },
};

function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

export default function LogsPanel({ logs, onRefresh, onClear }) {
  return (
    <div className="bg-surface-900 border border-surface-700 overflow-hidden relative">
      <div className="absolute top-0 left-0 w-full h-1 bg-[linear-gradient(90deg,var(--color-brand-400)_0%,transparent_100%)] opacity-20"></div>
      <div className="flex items-center justify-between px-5 py-3 border-b border-surface-700/40 bg-surface-800">
        <h3 className="text-[10px] font-bold text-brand-400 tracking-widest uppercase flex items-center gap-2"><Terminal size={12}/> TELEMETRÍA RECIENTE</h3>
        <div className="flex items-center gap-1">
          {onClear && logs.length > 0 && (
            <button
              onClick={onClear}
              className="p-1.5 border border-transparent hover:border-red-500 hover:bg-red-500/15 transition-all text-surface-500 hover:text-red-500"
              title="PURGAR TELEMETRÍA"
            >
              <Trash2 size={13} />
            </button>
          )}
          <button
            onClick={onRefresh}
            className="p-1.5 border border-transparent hover:border-brand-400 hover:text-brand-400 hover:bg-brand-500/10 transition-all text-surface-500"
            title="REFRESCAR"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {logs.length === 0 ? (
        <div className="text-center py-12 text-brand-400/30 text-xs tracking-widest uppercase border-dashed border border-surface-700 m-4 relative overflow-hidden">
          <div className="absolute inset-0 bg-brand-500/5 z-0 animate-pulse"></div>
          <span className="relative z-10">SIN DATOS DE ENRUTAMIENTO</span>
        </div>
      ) : (
        <div className="divide-y divide-surface-700/30 max-h-[500px] overflow-y-auto">
          {logs.map((log, i) => {
            const conf = LEVEL_CONFIG[log.level] || LEVEL_CONFIG.info;
            const Icon = conf.icon;

            return (
              <div
                key={log.id}
                className="px-5 py-3 border-l-2 border-transparent hover:border-brand-400 hover:bg-surface-800 transition-colors animate-slide-up group"
                style={{ animationDelay: `${i * 20}ms` }}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 ${conf.color}`}>
                    <Icon size={14} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {log.product_name && (
                        <span className="text-[11px] font-bold text-white uppercase tracking-wider group-hover:text-brand-300 transition-colors truncate">
                          {log.product_name}
                        </span>
                      )}
                      <span className="text-[10px] text-surface-400 font-bold uppercase tracking-widest border border-surface-700 px-1 py-0.5">
                        {log.action.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-[11px] text-surface-300 mt-1 leading-relaxed font-mono opacity-80 group-hover:opacity-100 transition-opacity">
                      {log.message}
                    </p>
                  </div>
                  <span
                    className="text-[9px] text-brand-400/40 whitespace-nowrap flex-shrink-0 pt-1"
                    style={{ fontFamily: 'var(--font-mono)' }}
                  >
                    {formatTime(log.created_at)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
