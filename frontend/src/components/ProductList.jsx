import { useState } from 'react';
import {
  Trash2, Pause, Play, ExternalLink, Clock,
  ShoppingCart, AlertTriangle, Eye, Package,
  Warehouse, Truck, ChevronDown, ChevronUp, MapPin
} from 'lucide-react';

const STATUS_CONFIG = {
  monitoring: { label: 'Monitorizando', color: 'bg-amber-500/15 text-amber-400 border-amber-500/20', icon: Eye },
  in_stock: { label: 'Disponible', color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20', icon: Package },
  reserved: { label: 'Reservado', color: 'bg-blue-500/15 text-blue-400 border-blue-500/20', icon: ShoppingCart },
  paused: { label: 'Pausado', color: 'bg-surface-500/15 text-surface-200/50 border-surface-500/20', icon: Pause },
  error: { label: 'Error', color: 'bg-red-500/15 text-red-400 border-red-500/20', icon: AlertTriangle },
};

const STOCK_TYPE_STYLES = {
  'En almacén': 'bg-emerald-500/10 text-emerald-400',
  'En tránsito': 'bg-blue-500/10 text-blue-400',
  'Esperando producción': 'bg-surface-700/50 text-surface-200/40',
};

function timeAgo(dateStr) {
  if (!dateStr) return 'Nunca';
  const utcDate = dateStr.endsWith('Z') ? dateStr : dateStr + 'Z';
  const diff = Date.now() - new Date(utcDate).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 0) return 'Ahora';
  if (secs < 60) return `Hace ${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `Hace ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `Hace ${hours}h`;
  return `Hace ${Math.floor(hours / 24)}d`;
}


function PickupPoints({ warehouses }) {
  if (!warehouses || warehouses.length === 0) return null;

  return (
    <div className="space-y-1 animate-slide-up">
      <div className="text-[10px] font-medium text-surface-200/30 uppercase tracking-wide mb-1">
        Puntos de recogida ({warehouses.length})
      </div>
      {warehouses.map((w, i) => (
        <div
          key={w.address_id || i}
          className="flex items-center gap-2 text-[11px] bg-surface-800/80 rounded-lg px-3 py-1.5
                     border border-surface-700/30"
        >
          <MapPin size={10} className="text-brand-400/60 flex-shrink-0" />
          <span className="text-surface-200/70 truncate flex-1" title={w.address}>
            {w.name}
          </span>

          {/* STOCK DISPLAY PER WAREHOUSE */}
          <div className="flex items-center gap-2 flex-shrink-0 px-2">
            {w.warehouse_stock > 0 && (
              <span className="text-emerald-400 font-semibold bg-emerald-500/10 px-1.5 py-0.5 rounded" title="Stock Físico en sitio">
                {w.warehouse_stock}U Físico
              </span>
            )}
            {w.transit_stock > 0 && (
              <span className="text-blue-400/80 font-medium bg-blue-500/10 px-1.5 py-0.5 rounded" title="Stock en Tránsito Global disponible para este punto">
                {w.transit_stock}U Tránsito
              </span>
            )}
            {(w.warehouse_stock === 0 && w.transit_stock === 0) && (
              <span className="text-surface-200/30">0 piezas</span>
            )}
          </div>

          <span className="text-[10px] text-surface-200/25 flex-shrink-0 border-l border-surface-700/50 pl-2">
            {w.area}
          </span>
        </div>
      ))}
    </div>
  );
}


export default function ProductList({ products, loading, onDelete, onToggle, onCheckout }) {
  const [expandedId, setExpandedId] = useState(null);

  if (loading) {
    return (
      <div className="text-center py-16 text-surface-200/40">
        <div className="animate-spin w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full mx-auto mb-3" />
        Cargando productos...
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="text-center py-16 text-surface-200/40">
        <Package size={40} className="mx-auto mb-3 opacity-30" />
        <p className="text-sm">No hay productos. Añade URLs de DofiMall para empezar.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {products.map((product, i) => {
        const statusConf = STATUS_CONFIG[product.status] || STATUS_CONFIG.monitoring;
        const StatusIcon = statusConf.icon;
        const isExpanded = expandedId === product.id;
        const hasWarehouses = product.warehouse_breakdown && product.warehouse_breakdown.length > 0;
        const totalStock = (product.warehouse_stock || 0) + (product.transit_stock || 0);

        return (
          <div
            key={product.id}
            className="bg-surface-800/60 border border-surface-700/40 rounded-xl
                       hover:border-surface-700/70 transition-all animate-slide-up"
            style={{ animationDelay: `${i * 30}ms` }}
          >
            <div className="p-4">
              <div className="flex items-start gap-4">
                {/* Image */}
                <div className="w-12 h-12 rounded-lg bg-surface-700/50 flex-shrink-0 overflow-hidden">
                  {product.image_url ? (
                    <img src={product.image_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Package size={18} className="text-surface-200/20" />
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-semibold text-white truncate">{product.name}</h3>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px]
                                      font-medium border ${statusConf.color}`}>
                      <StatusIcon size={10} />
                      {statusConf.label}
                    </span>
                  </div>

                  <a
                    href={product.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-brand-400/70 hover:text-brand-400 truncate block transition-colors"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}
                  >
                    {product.url}
                    <ExternalLink size={10} className="inline ml-1 -mt-0.5" />
                  </a>

                  <div className="flex items-center gap-3 mt-2 text-[11px] text-surface-200/40 flex-wrap">
                    {product.price && (
                      <span className="text-emerald-400 font-semibold text-xs">{product.price}</span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      {timeAgo(product.last_checked)}
                    </span>
                    <span>#{product.check_count} checks</span>

                    {product.check_count > 0 && (
                      <>
                        <span className="w-px h-3 bg-surface-700/50" />

                        {/* Stock global */}
                        <span className="flex items-center gap-1" title="Stock en almacén">
                          <Warehouse size={10} />
                          <span className={product.warehouse_stock > 0 ? 'text-emerald-400 font-semibold' : ''}>
                            {product.warehouse_stock ?? 0}U
                          </span>
                        </span>
                        <span className="flex items-center gap-1" title="Stock en tránsito">
                          <Truck size={10} />
                          <span className={product.transit_stock > 0 ? 'text-blue-400 font-semibold' : ''}>
                            {product.transit_stock ?? 0}U
                          </span>
                        </span>

                        {/* Total bold */}
                        {totalStock > 0 && (
                          <span className="text-white font-bold text-xs">
                            = {totalStock}U
                          </span>
                        )}

                        {/* Stock type badge */}
                        {product.stock_type_label && (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium
                            ${STOCK_TYPE_STYLES[product.stock_type_label] || 'bg-surface-700/50 text-surface-200/40'}`}>
                            {product.stock_type_label}
                          </span>
                        )}

                        {/* Pickup points toggle */}
                        {hasWarehouses && (
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : product.id)}
                            className="flex items-center gap-1 text-[10px] text-brand-400/60 hover:text-brand-400
                                       transition-colors ml-1 px-1.5 py-0.5 rounded hover:bg-brand-500/10"
                          >
                            <MapPin size={9} />
                            {isExpanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                            {product.warehouse_breakdown.length} puntos de recogida
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    onClick={() => onCheckout(product.id)}
                    className="p-2 rounded-lg bg-brand-500/10 hover:bg-brand-500/20 transition-colors border border-brand-500/20"
                    title="Comprar / Checkout"
                  >
                    <ShoppingCart size={14} className="text-brand-400" />
                  </button>
                  <button
                    onClick={() => onToggle(product.id)}
                    className="p-2 rounded-lg hover:bg-surface-700/50 transition-colors"
                    title={product.is_active ? 'Pausar' : 'Activar'}
                  >
                    {product.is_active
                      ? <Pause size={14} className="text-amber-400" />
                      : <Play size={14} className="text-emerald-400" />
                    }
                  </button>
                  <button
                    onClick={() => onDelete(product.id)}
                    className="p-2 rounded-lg hover:bg-red-500/10 transition-colors"
                    title="Eliminar"
                  >
                    <Trash2 size={14} className="text-red-400/60 hover:text-red-400" />
                  </button>
                </div>
              </div>
            </div>

            {/* Pickup points (expandable) */}
            {isExpanded && hasWarehouses && (
              <div className="border-t border-surface-700/30 px-4 pb-3 pt-2 ml-16">
                <PickupPoints warehouses={product.warehouse_breakdown} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
