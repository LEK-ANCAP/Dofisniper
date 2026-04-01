import { RefreshCw, CheckCircle, AlertTriangle, Info, XCircle } from 'lucide-react';

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

export default function LogsPanel({ logs, onRefresh }) {
  return (
    <div className="bg-surface-800/60 border border-surface-700/40 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-surface-700/40">
        <h3 className="text-sm font-semibold text-white">Actividad reciente</h3>
        <button
          onClick={onRefresh}
          className="p-1.5 rounded-md hover:bg-surface-700/50 transition-colors"
          title="Refrescar"
        >
          <RefreshCw size={13} className="text-surface-200/40" />
        </button>
      </div>

      {logs.length === 0 ? (
        <div className="text-center py-12 text-surface-200/30 text-sm">
          Sin actividad registrada
        </div>
      ) : (
        <div className="divide-y divide-surface-700/30 max-h-[500px] overflow-y-auto">
          {logs.map((log, i) => {
            const conf = LEVEL_CONFIG[log.level] || LEVEL_CONFIG.info;
            const Icon = conf.icon;

            return (
              <div
                key={log.id}
                className="px-5 py-3 hover:bg-surface-700/20 transition-colors animate-slide-up"
                style={{ animationDelay: `${i * 20}ms` }}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 ${conf.color}`}>
                    <Icon size={14} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {log.product_name && (
                        <span className="text-xs font-semibold text-white truncate">
                          {log.product_name}
                        </span>
                      )}
                      <span className="text-[11px] text-surface-200/30 font-medium uppercase tracking-wide">
                        {log.action.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-surface-200/50 mt-0.5 leading-relaxed">
                      {log.message}
                    </p>
                  </div>
                  <span
                    className="text-[11px] text-surface-200/25 whitespace-nowrap flex-shrink-0"
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
