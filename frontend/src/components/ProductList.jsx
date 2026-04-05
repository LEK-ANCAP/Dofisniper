import { useState, useEffect, useRef } from 'react';
import {
  Trash2, Pause, Play, ExternalLink, Clock,
  ShoppingCart, AlertTriangle, Eye, Package,
  Warehouse, Truck, ChevronDown, ChevronUp, MapPin, Target, Zap, X, Terminal, Camera, Activity
} from 'lucide-react';
import toast from 'react-hot-toast';
import { updateProduct, manualCheckout, fetchLogs, fetchLiveView } from '../utils/api';

const STATUS_CONFIG = {
  monitoring: { label: 'Monitorizando', color: 'bg-amber-500/15 text-amber-400 border-amber-500/20', icon: Eye },
  in_stock: { label: 'Disponible', color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20', icon: Package },
  purchasing: { label: 'Atacando', color: 'bg-orange-500/15 text-orange-400 border-orange-500/50 animate-pulse', icon: Zap },
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

function ProductSnipeModal({ product, onClose, onToggle }) {
  const [targetQty, setTargetQty] = useState(product.target_quantity || 1);
  const [minTrigger, setMinTrigger] = useState(product.min_stock_to_trigger || 1);
  const [logOutput, setLogOutput] = useState('');
  const [isExecuting, setIsExecuting] = useState(product.status === 'purchasing');
  const [liveFrame, setLiveFrame] = useState(null);
  const terminalRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    async function loadLogHistory() {
      try {
        const logs = await fetchLogs(100);
        if (!mounted) return;
        const myLogs = (Array.isArray(logs) ? logs : []).filter(l => 
          l.product_id === product.id && (l.action.includes('purchase') || l.action.includes('checkout'))
        ).reverse(); // Order chronically

        if (myLogs.length > 0) {
          const historyText = myLogs.map(l => {
              const time = new Date(l.created_at).toLocaleTimeString('es-ES');
              return `[${time}] ${l.action.toUpperCase()}\n${l.message || "Sin detalles"}`;
          }).join('\n\n' + '='.repeat(40) + '\n\n');
          
          setLogOutput(`>> RECUPERANDO HISTORIAL TÁCTICO...\n\n${historyText}\n\n>> Sistema listo. Esperando nuevas instrucciones...`);
        }
      } catch (err) {
         // Silently ignore log fetch failure
      }
    }
    loadLogHistory();
    return () => { mounted = false; };
  }, [product.id]);

  // Live view polling loop
  useEffect(() => {
    let timer;
    if (isExecuting) {
      timer = setInterval(async () => {
        try {
          const res = await fetchLiveView(product.id);
          if (res.frame) setLiveFrame(res.frame);
        } catch (e) {
          // ignore
        }
      }, 1000);
    } else {
      setLiveFrame(null);
    }
    return () => clearInterval(timer);
  }, [isExecuting, product.id]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logOutput]);

  const handleSaveConfig = async () => {
    try {
       await updateProduct(product.id, { target_quantity: Number(targetQty), min_stock_to_trigger: Number(minTrigger) });
       toast.success('Configuración Snipe guardada', { icon: '🎯' });
    } catch(e) {
       toast.error('Error guardando configuración');
    }
  };

  const handleManualSnipe = async () => {
    setIsExecuting(true);
    setLogOutput(">> Inicializando hilo de Playwright...\n>> Solicitando bypass de Dofimall...\n>> Cifrando credenciales maestras y arrancando motor...");
    
    try {
      const res = await manualCheckout(product.id);
      setLogOutput(prev => prev + "\n\n[" + (res.success ? "SUCCESS" : "ERROR") + "] \n" + (res.message || "Proceso de compra concluido sin logs"));
      if(res.success) {
         toast.success("Reserva lograda exitosamente!", { icon: '🎉' });
      } else {
         toast.error("La compra falló", { icon: '❌' });
      }
    } catch(e) {
      setLogOutput(prev => prev + "\n\n[FATAL SYSTEM CRASH]\n" + e.message);
    } finally {
      setIsExecuting(false);
    }
  };

  const hasWarehouses = product.warehouse_breakdown && product.warehouse_breakdown.length > 0;
  const totalStock = (product.warehouse_stock || 0) + (product.transit_stock || 0);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface-900 border border-surface-700 w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        
        {/* Header */}
        <div className="px-6 py-4 flex items-center justify-between border-b border-surface-700/50 bg-surface-800/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <Target size={20} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight">Panel de Francotirador</h2>
              <div className="text-xs text-brand-400 font-mono truncate max-w-[300px]">ID: {product.id}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
             <button onClick={onClose} className="p-2 text-surface-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all border border-transparent hover:border-red-500/20">
               <X size={20} />
             </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Metadata Compacta */}
          <div className="bg-surface-800/50 p-4 rounded-xl border border-surface-700/50">
            <h3 className="text-white font-semibold text-sm mb-1">{product.name}</h3>
            <div className="text-xs text-surface-400 mb-3 block truncate">{product.url}</div>
            <div className="flex gap-4 text-xs">
               <div className="bg-surface-900 px-3 py-1.5 rounded-lg border border-surface-700">Stock Total: <span className="text-white font-bold">{totalStock}U</span></div>
               <div className="bg-surface-900 px-3 py-1.5 rounded-lg border border-surface-700">Precio: <span className="text-emerald-400 font-bold">{product.price || '-'}</span></div>
               <div className="bg-surface-900 px-3 py-1.5 rounded-lg border border-surface-700">Comprobaciones: <span className="text-brand-400">{product.check_count}</span></div>
            </div>
          </div>

          {/* Configuración */}
          <div>
             <div className="text-xs font-semibold text-surface-400 mb-3 uppercase tracking-wide">Ajustes de Misión</div>
             
             {/* Two independent toggles */}
             <div className="grid grid-cols-2 gap-3 mb-4">
               <label className={`flex items-center gap-2.5 cursor-pointer p-3 rounded-xl border transition-all ${
                 product.is_active 
                   ? 'bg-emerald-500/10 border-emerald-500/30 shadow-sm shadow-emerald-500/5' 
                   : 'bg-surface-800/60 border-surface-700/50 hover:bg-surface-800'
               }`}>
                 <input 
                   type="checkbox"
                   className="w-4 h-4 accent-emerald-500 rounded"
                   checked={product.is_active}
                   onChange={() => onToggle(product.id)}
                 />
                 <div>
                   <div className={`text-[11px] font-bold ${product.is_active ? 'text-emerald-400' : 'text-surface-400'}`}>
                     MONITORIZAR
                   </div>
                   <div className="text-[9px] text-surface-500">Notificaciones de stock</div>
                 </div>
               </label>
               
               <label className={`flex items-center gap-2.5 cursor-pointer p-3 rounded-xl border transition-all ${
                 product.auto_buy 
                   ? 'bg-orange-500/10 border-orange-500/30 shadow-sm shadow-orange-500/5' 
                   : 'bg-surface-800/60 border-surface-700/50 hover:bg-surface-800'
               }`}>
                 <input 
                   type="checkbox"
                   className="w-4 h-4 accent-orange-500 rounded"
                   checked={product.auto_buy || false}
                   onChange={async () => {
                     try {
                       const newState = !product.auto_buy;
                       await updateProduct(product.id, { auto_buy: newState });
                       product.auto_buy = newState;
                       onToggle(product.id, { preventBackend: true }); // Usar onToggle como trigger de renderizado local
                       toast.success(newState ? 'Compra automática ACTIVADA' : 'Compra automática DESACTIVADA', { icon: newState ? '⚡' : '⏸️' });
                     } catch(e) {
                       toast.error('Error al cambiar modo de compra');
                     }
                   }}
                 />
                 <div>
                   <div className={`text-[11px] font-bold ${product.auto_buy ? 'text-orange-400' : 'text-surface-400'}`}>
                     COMPRA AUTO
                   </div>
                   <div className="text-[9px] text-surface-500">Reservar cuando haya stock</div>
                 </div>
               </label>
             </div>
             
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div>
                  <label className="block text-xs text-surface-400 mb-1">Cantidad a Comprar</label>
                  <div className="flex items-center gap-2">
                     <input
                        type={targetQty === -1 ? "text" : "number"}
                        min="1" max="999"
                        disabled={targetQty === -1}
                        value={targetQty === -1 ? "MÁXIMA" : targetQty}
                        onChange={e => setTargetQty(e.target.value === "MÁXIMA" ? -1 : Number(e.target.value))}
                        onBlur={() => { if(targetQty !== -1) handleSaveConfig() }}
                        className="w-full bg-surface-800 border border-surface-700 rounded-lg p-2.5 text-white font-mono text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-60 disabled:text-emerald-400 disabled:font-bold"
                     />
                     <label className="flex items-center gap-2 text-xs text-brand-400 cursor-pointer whitespace-nowrap bg-brand-500/10 hover:bg-brand-500/20 px-3 py-2.5 rounded-lg border border-brand-500/30 transition-colors">
                        <input 
                           type="checkbox" 
                           checked={targetQty === -1} 
                           onChange={async (e) => {
                              const newVal = e.target.checked ? -1 : 1;
                              setTargetQty(newVal);
                              try {
                                 await updateProduct(product.id, { target_quantity: newVal, min_stock_to_trigger: Number(minTrigger) });
                                 toast.success(newVal === -1 ? 'Modo MÁXIMO activado' : 'Modo unitario activado', { icon: '🎯' });
                              } catch(err) {
                                 toast.error('Error al guardar configuración');
                              }
                           }}
                           className="w-3.5 h-3.5 accent-brand-500 rounded border-brand-500"
                        />
                        MAX
                     </label>
                  </div>
               </div>
               <div>
                  <label className="block text-xs text-surface-400 mb-1">Stock Mín. para Auto-Snipe</label>
                  <input
                     type="number" min="1" max="999"
                     value={minTrigger}
                     onChange={e => setMinTrigger(Number(e.target.value))}
                     onBlur={handleSaveConfig}
                     className="w-full bg-surface-800 border border-surface-700 rounded-lg p-2.5 text-white font-mono text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
               </div>
             </div>
          </div>

          {/* Boton de Disparo Manual */}
          <button
             onClick={handleManualSnipe}
             disabled={isExecuting}
             className="w-full flex items-center justify-center gap-2 py-3 bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-400 hover:to-red-500 disabled:opacity-50 text-white rounded-lg font-bold shadow-lg shadow-orange-500/20 transition-all uppercase tracking-wide"
          >
             <Zap size={18} className={isExecuting ? "animate-pulse" : ""} />
             {isExecuting ? `EJECUTANDO COMPRA SEGURA (${targetQty} ud)...` : `FORZAR COMPRA MANUAL (${targetQty} ud)`}
          </button>

          {/* Terminal & Cámara Táctica */}
          <div className="space-y-4">
             {/* Live Web View (Cámara Táctica) con efecto de Mirilla */}
             <div className="relative rounded-xl overflow-hidden bg-black border border-surface-700 shadow-2xl aspect-video flex items-center justify-center group">
                {/* Capas Estéticas de Mirilla */}
                <div className="absolute inset-0 pointer-events-none z-10 border-[30px] border-black/20 rounded-xl"></div>
                <div className="absolute inset-x-0 top-1/2 h-px bg-emerald-500/10 z-10"></div>
                <div className="absolute inset-y-0 left-1/2 w-px bg-emerald-500/10 z-10"></div>
                
                {/* Corner Accents */}
                <div className="absolute top-4 left-4 w-4 h-px bg-emerald-500/40 z-10"></div>
                <div className="absolute top-4 left-4 w-px h-4 bg-emerald-500/40 z-10"></div>
                
                <div className="absolute top-4 right-4 w-4 h-px bg-emerald-500/40 z-10"></div>
                <div className="absolute top-4 right-4 w-px h-4 bg-emerald-500/40 z-10"></div>
                
                <div className="absolute bottom-4 left-4 w-4 h-px bg-emerald-500/40 z-10"></div>
                <div className="absolute bottom-4 left-4 w-px h-4 bg-emerald-500/40 z-10"></div>
                
                <div className="absolute bottom-4 right-4 w-4 h-px bg-emerald-500/40 z-10"></div>
                <div className="absolute bottom-4 right-4 w-px h-4 bg-emerald-500/40 z-10"></div>

                {/* Central Scope Circle */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                   <div className="w-1/2 aspect-square rounded-full border border-emerald-500/5 shadow-[0_0_80px_rgba(16,185,129,0.05)] flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-red-500/40 animate-pulse"></div>
                   </div>
                </div>

                {liveFrame ? (
                   <img 
                      src={`data:image/jpeg;base64,${liveFrame}`} 
                      className="w-full h-full object-contain filter contrast-125 brightness-90 saturate-50" 
                      alt="Tactical Cam" 
                   />
                ) : (
                   <div className="text-center space-y-2 opacity-30">
                      <Camera size={48} className="mx-auto text-surface-500" />
                      <div className="text-[10px] font-mono tracking-widest text-surface-400 uppercase">
                         {isExecuting ? 'LOCKING TARGET...' : 'SENSOR OFFLINE'}
                      </div>
                   </div>
                )}
                
                {/* Overlay status */}
                <div className="absolute top-3 left-3 flex items-center gap-2 z-20">
                   <div className={`w-1.5 h-1.5 rounded-full ${isExecuting ? 'bg-red-500 animate-pulse' : 'bg-surface-600'}`}></div>
                   <span className="text-[9px] font-bold text-white/50 tracking-[0.2em] font-mono">SC-V1 // LIVE FEED</span>
                </div>
                
                {/* Scan effect */}
                {isExecuting && (
                   <div className="absolute inset-0 pointer-events-none z-20 overflow-hidden opacity-5">
                      <div className="w-full h-1 bg-white animate-scan"></div>
                   </div>
                )}
             </div>

             {/* Terminal */}
             <div className="bg-surface-950 rounded-xl border border-surface-700 p-4 font-mono text-xs leading-relaxed shadow-inner shadow-black/50">
                <div className="flex items-center gap-2 mb-3 pb-2 border-b border-surface-800 text-surface-500">
                   <Activity size={12} />
                   <span className="uppercase tracking-widest font-bold text-[9px]">Terminal Operativo Local - PID: {product.id}</span>
                </div>
                <pre 
                   ref={terminalRef}
                   className="text-emerald-400 h-48 overflow-y-auto custom-scrollbar whitespace-pre-wrap selection:bg-emerald-500/30"
                >
                   {logOutput || ">> Sistema en espera de órdenes..."}
                </pre>
             </div>
          </div>

          {hasWarehouses && (
             <div>
                <PickupPoints warehouses={product.warehouse_breakdown} />
             </div>
          )}

        </div>
      </div>
    </div>
  );
}

function ProductItem({ product, i, onOpenModal, onDelete, onToggle, onCheckout }) {
  const statusConf = STATUS_CONFIG[product.status] || STATUS_CONFIG.monitoring;
  const StatusIcon = statusConf.icon;
  const totalStock = (product.warehouse_stock || 0) + (product.transit_stock || 0);

  return (
    <div
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

                  {/* Configuration toggle */}
                  <button
                    onClick={() => onOpenModal(product)}
                    className={`flex items-center gap-1 text-[10px] transition-colors ml-1 px-1.5 py-0.5 rounded border ${
                      product.auto_buy
                        ? 'text-orange-400 border-orange-500/20 bg-orange-500/10 hover:bg-orange-500/20 font-semibold'
                        : 'text-brand-400/60 border-brand-500/20 hover:bg-brand-500/10 hover:text-brand-400'
                    }`}
                  >
                    {product.auto_buy ? <Zap size={10} /> : <Target size={9} />}
                    {product.auto_buy ? 'Auto-Snipe ON' : 'Configurar Snipe'}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 flex-shrink-0">
            {product.status === 'purchasing' ? (
              <button
                onClick={() => onOpenModal(product)}
                className="p-2 rounded-lg bg-orange-500/20 hover:bg-orange-500/40 transition-colors border border-orange-500 animate-pulse group"
                title="Monitorear ataque automático en directo"
              >
                <Activity size={14} className="text-orange-400" />
              </button>
            ) : (
              <button
                onClick={() => onOpenModal(product)}
                className="p-2 rounded-lg bg-orange-500/10 hover:bg-orange-500/20 transition-colors border border-orange-500/20 group"
                title="Snipe / Checkout Manual"
              >
                <Zap size={14} className="text-orange-400 group-hover:text-orange-300" />
              </button>
            )}
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
    </div>
  );
}

export default function ProductList({ products, loading, onDelete, onToggle, onCheckout }) {
  const [selectedProduct, setSelectedProduct] = useState(null);

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
      {products.map((product, i) => (
        <ProductItem 
          key={product.id}
          product={product}
          i={i}
          onOpenModal={setSelectedProduct}
          onDelete={onDelete}
          onToggle={onToggle}
          onCheckout={onCheckout}
        />
      ))}

      {selectedProduct && (
         <ProductSnipeModal 
            product={selectedProduct} 
            onClose={() => setSelectedProduct(null)} 
            onToggle={onToggle}
         />
      )}
    </div>
  );
}
