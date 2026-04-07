import { useState, useEffect, useRef } from 'react';
import {
  Trash2, Pause, Play, ExternalLink,
  ShoppingCart, AlertTriangle, Package, Edit3, BarChart, X, Zap, Target, Eye, Database, Crosshair, Terminal, Camera, Activity, Download, Upload, MapPin, Truck, RefreshCw
} from 'lucide-react';
import toast from 'react-hot-toast';
import { updateProduct, manualCheckout, fetchLogs, fetchLiveView, fetchProductAnalytics, fetchCategories } from '../utils/api';
import { playTacticalClick, playEngageAlarm, playMissionSuccess, playMissionFail, startMorseTransmission, stopMorseTransmission } from '../utils/tacticalAudio';

const STATUS_CONFIG = {
  monitoring: { label: 'RECON', border: 'border-brand-400/50', text: 'text-brand-400', icon: Eye },
  in_stock: { label: 'DISPONIBLE', border: 'border-emerald-400', text: 'text-emerald-400', icon: Package },
  purchasing: { label: 'INFILTRACIÓN', border: 'border-amber-500 animate-pulse', text: 'text-amber-500', icon: Crosshair },
  reserved: { label: 'ASEGURADO', border: 'border-blue-500', text: 'text-blue-400', icon: ShoppingCart },
  paused: { label: 'SUSPENDIDO', border: 'border-surface-600', text: 'text-surface-500', icon: Pause },
  error: { label: 'FALLA TÁCTICA', border: 'border-red-500', text: 'text-red-500', icon: AlertTriangle },
  waiting: { label: 'ESPERANDO DISPONIBILIDAD', border: 'border-amber-500 shadow-[0_0_15px_rgba(255,176,0,0.3)]', text: 'text-amber-500', icon: Target },
};

function TacticalBadge({ children, active, className="", onClick }) {
    return (
        <span onClick={onClick} className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] uppercase font-mono font-bold border tracking-wider ${active ? 'bg-brand-500/10 text-brand-400 border-brand-400/50 shadow-[0_0_8px_rgba(0,255,65,0.2)]' : 'bg-surface-900 border-surface-700 text-surface-500'} ${className}`}>
           {children}
        </span>
    )
}

function AutoBuyCountdown({ isActive, autoBuy, status }) {
   const [secs, setSecs] = useState(10);
   useEffect(() => {
      if (!isActive || !autoBuy) return;
      setSecs(10);
      const t = setInterval(() => {
         setSecs(s => s > 0 ? s - 1 : 10);
      }, 1000);
      return () => clearInterval(t);
   }, [isActive, autoBuy]);

   if (!isActive || !autoBuy) return null;
   
   if (status === 'purchasing') {
      return (
         <span className="flex items-center gap-1 text-[10px] text-red-400 border border-red-500/50 bg-red-500/20 px-2 py-0.5 font-mono tracking-widest uppercase ml-1 animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.3)]">
            <Crosshair size={10} className="animate-spin" /> ATACANDO...
         </span>
      );
   }
   
   return (
      <span className="flex items-center gap-1 text-[10px] text-amber-400 border border-amber-500/40 bg-amber-500/15 px-2 py-0.5 font-mono tracking-widest uppercase ml-1 shadow-[0_0_6px_rgba(245,158,11,0.15)]">
         <Target size={10} className={secs < 3 ? 'animate-pulse text-red-400' : ''} />
         <span>AUTO</span>
         <span className={`font-bold ${secs < 3 ? 'text-red-400' : ''}`}>T-{secs}s</span>
      </span>
   );
}

function ScanCountdown({ isActive }) {
   const [secs, setSecs] = useState(10);
   useEffect(() => {
      if (!isActive) return;
      const t = setInterval(() => {
         setSecs(s => s > 0 ? s - 1 : 10);
      }, 1000);
      return () => clearInterval(t);
   }, [isActive]);

   if (!isActive) return null;
   return (
      <span className="flex items-center gap-1 opacity-80 border-l border-brand-400/30 pl-1.5 ml-0.5">
         <RefreshCw size={10} className={`${secs < 3 ? 'animate-spin' : ''}`} /> T-{secs}S
      </span>
   );
}

function ProductItem({ product, i, onDelete, onToggle, onCheckout, onOpenEdit }) {
  const [expandedTab, setExpandedTab] = useState(null); 
  const [targetQty, setTargetQty] = useState(product.target_quantity || 1);
  const [minTrigger, setMinTrigger] = useState(product.min_stock_to_trigger || 1);
  
  const [logOutput, setLogOutput] = useState('');
  const [isExecuting, setIsExecuting] = useState(product.status === 'purchasing');
  const [liveFrame, setLiveFrame] = useState(null);
  const terminalRef = useRef(null);
  
  const [history, setHistory] = useState([]);
  const [analyticsLoaded, setAnalyticsLoaded] = useState(false);

  const totalStock = (product.warehouse_stock || 0) + (product.transit_stock || 0);

  // Determinamos el estado visual basado en configuración
  let activeStatus = product.status;
  if (product.auto_buy && totalStock === 0 && product.status === 'monitoring') {
      activeStatus = 'waiting';
  }

  const statusConf = STATUS_CONFIG[activeStatus] || STATUS_CONFIG.monitoring;
  const StatusIcon = statusConf.icon;

  // Auto-open terminal when attack starts
  useEffect(() => {
     if (activeStatus === 'purchasing' && expandedTab !== 'snipe') {
        setExpandedTab('snipe');
     }
  }, [activeStatus]);

  useEffect(() => {
    let interval;
    if (expandedTab === 'snipe' || expandedTab === 'auto' || activeStatus === 'purchasing') {
      interval = setInterval(async () => {
        try {
          // Filtrar por ID de producto y aumentar límite para tener margen de filtrado local
          const logs = await fetchLogs(30, product.id); 
          if (logs && logs.length > 0) {
             // Filtrar localmente para excluir ruido de stock_changed si no estamos en 'recon'
             const filtered = logs.filter(l => 
                l.action !== 'stock_changed' && 
                l.action !== 'check_error' &&
                l.action !== 'category_created'
             );
             
             if (filtered.length > 0) {
                const terminalLines = filtered.reverse().map(l => {
                   const time = new Date(l.created_at).toLocaleTimeString();
                   return `[${time}] ${l.message}`;
                }).join('\n');
                setLogOutput(terminalLines);
             }
          }

          if (activeStatus === 'purchasing' || isExecuting) {
            const data = await fetchLiveView(product.id);
            if (data && data.frame) setLiveFrame(data.frame);
          }
        } catch (e) {}
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [expandedTab, product.id, isExecuting]);

  useEffect(() => {
    if (expandedTab === 'analytics' && !analyticsLoaded) {
       fetchProductAnalytics(product.id).then(data => {
          setHistory(data.timeline || []);
          setAnalyticsLoaded(true);
       });
    }
  }, [expandedTab, product.id, analyticsLoaded]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logOutput]);

  const handleSaveConfig = async () => {
     try {
        await updateProduct(product.id, {
           target_quantity: parseInt(targetQty),
           min_stock_to_trigger: parseInt(minTrigger)
        });
        toast.success("CONFIG_SAVED", { style: { background: '#1e293b', color: '#38bdf8', border: '1px solid #0c4a6e' }});
     } catch(e) {}
  };

  const executeSnipe = async () => {
      if (isExecuting) return;
      
      setIsExecuting(true);
      playEngageAlarm();
      startMorseTransmission();
      setLogOutput("> INICIANDO SECUENCIA DE INFILTRACIÓN...\n> ESTABLECIENDO TÚNEL SEGURO...");
      
      try {
          const result = await manualCheckout(product.id);
          if (result.success) {
              setLogOutput(prev => prev + `\n\n>> [MISSION SUCCESS]\n>> REDIRECTING TO CHECKOUT: ${result.checkout_url}`);
              playMissionSuccess();
              toast.success("OBJETIVO ASEGURADO", { duration: 5000 });
              
              // Handle post-purchase action
              if (product.post_purchase_action === 'pause') {
                  await updateProduct(product.id, { is_active: false, auto_buy: false });
                  onToggle(product.id, { preventBackend: true });
              }

              if (result.checkout_url) {
                  setTimeout(() => window.open(result.checkout_url, '_blank'), 2000);
              }
          } else {
              setLogOutput(prev => prev + `\n\n>> [OP_FAILURE]\n>> REASON: ${result.message}`);
              playMissionFail();
              toast.error(`ERROR: ${result.message}`);
          }
      } catch (e) {
          setLogOutput(prev => prev + `\n\n>> [CRITICAL FAILURE]\n>> ${e.message}`);
      } finally {
          setIsExecuting(false);
          stopMorseTransmission();
      }
  };

  return (
    <div className={`bg-surface-800 border transition-all duration-300 animate-slide-up relative overflow-hidden group/card
      ${isExecuting ? 'border-red-600 shadow-[0_0_30px_rgba(220,38,38,0.4)] z-30 scale-[1.01]' : expandedTab ? 'border-brand-400/60 shadow-[0_0_20px_rgba(0,255,65,0.05)]' : 'border-surface-700'}`} 
      style={{ animationDelay: `${i * 20}ms` }}>
      
      {/* SCANLINE EFFECT during Infiltration */}
      {activeStatus === 'purchasing' && (
          <div className="absolute inset-0 pointer-events-none z-50 overflow-hidden opacity-30">
              <div className="w-full h-1 bg-red-500 shadow-[0_0_15px_red] absolute top-[-10%] left-0 animate-scanline" />
              <div className="absolute top-2 right-2 bg-red-600 text-white text-[8px] font-mono px-2 py-0.5 animate-pulse uppercase z-50">SISTEMA_EN_ATAQUE</div>
          </div>
      )}

      {/* Header Visible (Compact) */}
      <div className="p-3 sm:p-4 flex flex-col sm:flex-row gap-4 items-start sm:items-center relative z-20">
        {/* Imagen HUD */}
        <div className="relative group/img flex-shrink-0">
          <div className="w-16 h-16 sm:w-20 sm:h-20 bg-surface-900 border border-surface-700 flex items-center justify-center overflow-hidden">
            {product.image_url ? (
               <img 
                 src={`/api/products/image-proxy?url=${encodeURIComponent(product.image_url)}`} 
                 alt={product.name} 
                 className="w-full h-full object-cover filter grayscale hover:grayscale-0 transition-all duration-500" 
                 onError={(e) => {
                    e.target.onerror = null; 
                    e.target.src = ""; // Clear broken src
                    e.target.parentElement.innerHTML = '<div class="flex items-center justify-center w-full h-full bg-surface-900"><svg class="text-surface-600" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg></div>';
                 }}
               />
            ) : (
               <Package size={24} className="text-surface-600" />
            )}
            <div className="absolute inset-0 border border-brand-400/20 pointer-events-none group-hover/img:border-brand-400/50 transition-colors"></div>
            <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-brand-400"></div>
            <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-brand-400"></div>
          </div>
          {product.auto_buy && (
            <div className="absolute -top-1 -right-1 bg-amber-500 text-surface-900 p-0.5 rounded-full shadow-[0_0_8px_rgba(245,158,11,0.5)] z-10">
               <Target size={10} fill="currentColor" />
            </div>
          )}
        </div>

        {/* Data Intel Area */}
        <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
               <h3 className="text-white font-bold text-sm truncate uppercase tracking-tight" style={{ textShadow: '0 0 8px rgba(255,255,255,0.2)' }}>
                  {product.name || 'TARGET_UNKNOWN_ID'}
               </h3>
               
               <a href={product.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[10px] font-mono text-brand-400 hover:text-white transition-colors uppercase cursor-pointer border border-brand-400/30 px-2 py-0.5" title="Ver Objetivo (External)">
                  <ExternalLink size={12} /> TARGET_URL
               </a>

               {/* Badges */}
               <TacticalBadge 
                  active={product.is_active} 
                  className={`cursor-pointer hover:bg-brand-500/20 transition-colors ${activeStatus === 'purchasing' ? 'animate-pulse border-red-500 text-red-500 bg-red-500/10 shadow-[0_0_15px_rgba(239,68,68,0.3)]' : ''}`}
                  onClick={() => { playTacticalClick(); onToggle(product.id); }}
               >
                  <StatusIcon size={10} className={product.is_active ? (activeStatus === 'purchasing' ? 'text-red-500' : statusConf.text) : ''} /> 
                  {product.is_active ? (activeStatus === 'purchasing' ? 'ATACANDO OBJETIVO' : statusConf.label) : 'SUSPENDIDO'}
                  <ScanCountdown isActive={product.is_active && !product.auto_buy} />
               </TacticalBadge>
               <AutoBuyCountdown isActive={product.is_active} autoBuy={product.auto_buy} status={activeStatus} />
            </div>

            <div className="flex items-center gap-3 text-[10px] font-mono text-surface-300 mt-2">
               <span className={`font-bold px-2 py-1 border flex items-center gap-1 ${product.warehouse_stock > 0 ? 'text-emerald-400 border-emerald-400/30 bg-emerald-500/10' : 'text-surface-500 border-surface-700 bg-surface-800'}`}>
                  <MapPin size={12} /> LOCAL: {product.warehouse_stock || 0}
               </span>
               <span className={`font-bold px-2 py-1 border flex items-center gap-1 ${product.transit_stock > 0 ? 'text-emerald-400 border-emerald-400/30 bg-emerald-500/10' : 'text-surface-500 border-surface-700 bg-surface-800'}`}>
                  <Truck size={12} /> TRANSIT: {product.transit_stock || 0}
               </span>
               {(totalStock > 0) && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-surface-900 bg-emerald-500 px-2 py-1 tracking-wider">
                      <Package size={10}/> TOTAL: {totalStock}U
                  </span>
               )}
            </div>
        </div>

        {/* Actions (Derecha) */}
        <div className="flex sm:flex-col items-center sm:items-end gap-2 w-full sm:w-auto relative z-20">
           {/* Control de Tabs Navigación */}
           <div className="flex bg-surface-900 p-0.5 border border-surface-700">
              <button onMouseEnter={() => playTacticalClick(0.01)} onClick={() => { playTacticalClick(); setExpandedTab(expandedTab === 'lz' ? null : 'lz'); }} className={`p-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider transition-colors ${expandedTab === 'lz' ? 'bg-brand-400 text-surface-900 font-bold border border-brand-400' : 'text-brand-400/70 hover:bg-brand-500/20 hover:text-brand-400 border border-transparent'}`}>
                 <MapPin size={16} className={expandedTab==='lz'?'text-surface-900':'text-brand-400'} /> ALMACENES
              </button>
              <button onMouseEnter={() => playTacticalClick(0.01)} onClick={() => { playTacticalClick(); setExpandedTab(expandedTab === 'analytics' ? null : 'analytics'); }} className={`p-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider transition-colors ${expandedTab === 'analytics' ? 'bg-brand-400 text-surface-900 font-bold border border-brand-400' : 'text-brand-400/70 hover:bg-brand-500/20 hover:text-brand-400 border border-transparent'}`}>
                 <Database size={16} className={expandedTab==='analytics'?'text-surface-900':'text-brand-400'} /> INTEL
              </button>
              <button onMouseEnter={() => playTacticalClick(0.01)} onClick={() => { playTacticalClick(); setExpandedTab(expandedTab === 'auto' ? null : 'auto'); }} className={`p-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider transition-colors ${expandedTab === 'auto' ? 'bg-amber-500 text-surface-900 font-bold border border-amber-500' : 'text-amber-400/70 hover:bg-amber-500/20 hover:text-amber-400 border border-transparent'}`}>
                 <Target size={16} className={expandedTab==='auto'?'text-surface-900':'text-amber-400'} /> OPERACIÓN
              </button>
              <button onMouseEnter={() => playTacticalClick(0.01)} onClick={() => { playTacticalClick(); setExpandedTab(expandedTab === 'snipe' ? null : 'snipe'); }} className={`p-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider transition-colors ${expandedTab === 'snipe' ? 'bg-red-500 text-surface-900 font-bold border border-red-500' : 'text-red-500/70 hover:bg-red-500/20 hover:text-red-500 border border-transparent'}`}>
                 <Crosshair size={16} className={expandedTab==='snipe'?'text-surface-900':'text-red-500'} /> FORCE_CMD
              </button>
           </div>
           <div className="flex gap-2 ml-auto sm:ml-0 mt-1">
               <button onClick={() => { playTacticalClick(); onOpenEdit(product); }} className="p-2 border border-surface-600 bg-surface-800 hover:border-blue-500 hover:text-blue-400 transition-all text-surface-300" title="Editar Metadatos"><Edit3 size={16}/></button>
               <button onClick={() => { playTacticalClick(); onDelete(product.id); }} className="p-2 border border-surface-600 bg-surface-800 hover:border-red-500 hover:bg-red-500/10 transition-all text-surface-300 hover:text-red-500" title="Eliminar Objetivo"><Trash2 size={16}/></button>
           </div>
        </div>
      </div>

      {/* EXPANDED SECTIONS */}
      {expandedTab && (
         <div className="border-t border-surface-700 bg-surface-900/60 p-4 animate-slide-up ">
            
            {/* TAB: LZS (Warehouses) */}
            {expandedTab === 'lz' && (
               <div>
                  <div className="text-xs text-brand-400 mb-3 tracking-wider uppercase flex items-center gap-2"><MapPin size={16}/> Zonas de Extracción Disponibles [{product.warehouse_breakdown?.length || 0}]</div>
                  {(!product.warehouse_breakdown || product.warehouse_breakdown.length === 0) ? (
                     <div className="text-surface-400 text-sm p-6 bg-surface-800 w-full text-center border border-surface-700 border-dashed uppercase font-mono text-[10px]">NO HAY COORDENADAS ALMACENADAS DE LZ</div>
                  ) : (
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {product.warehouse_breakdown.map((w, index) => (
                           <div key={index} className="bg-surface-800 border border-surface-700 p-3 flex items-center justify-between group hover:border-brand-400">
                              <span className="text-[10px] font-mono text-surface-300 truncate w-1/2 pr-2 leading-tight uppercase group-hover:text-white transition-colors">{w.name} ({w.area})</span>
                              <div className="flex items-center gap-2 text-[10px] flex-shrink-0">
                                 <span className={`px-2 py-1 border flex items-center gap-1 font-mono ${w.warehouse_stock > 0 ? 'border-emerald-400/50 text-emerald-400 bg-emerald-500/10 font-bold' : 'border-surface-700 text-surface-500 bg-surface-900/50'}`}>
                                    <MapPin size={10} className="hidden sm:block" />LOCAL: {w.warehouse_stock}
                                 </span>
                                 <span className={`px-2 py-1 border flex items-center gap-1 font-mono ${w.transit_stock > 0 ? 'border-emerald-400/50 text-emerald-400 bg-emerald-500/10 font-bold' : 'border-surface-700 text-surface-500 bg-surface-900/50'}`}>
                                    <Truck size={10} className="hidden sm:block" />TRANS: {w.transit_stock}
                                 </span>
                              </div>
                           </div>
                        ))}
                     </div>
                  )}
               </div>
            )}

            {/* TAB: INTEL (Analytics) */}
            {expandedTab === 'analytics' && (
               <div>
                  <div className="text-[10px] font-mono text-blue-400 mb-3 tracking-wider uppercase flex items-center gap-2"><Database size={16}/> Actividad Relevante del Objetivo (Intel)</div>
                  {history.length === 0 ? (
                     <div className="text-surface-400 text-[10px] font-mono p-6 bg-surface-800 w-full text-center border border-surface-700 border-dashed uppercase text-[10px]">SIN EVENTOS SIGNIFICATIVOS REGISTRADOS</div>
                  ) : (
                     <div className="space-y-1 h-64 overflow-y-auto custom-scrollbar pr-2">
                        {history.sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp)).map((row, index) => {
                           const time = new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                           
                           // Definir icono y color según categoría
                           let Icon = Activity;
                           let color = "text-surface-400";
                           let label = "";

                           if (row.event_category === 'my_purchase') {
                              Icon = ShoppingCart; color = "text-brand-400 font-bold bg-brand-500/10 border-brand-400/30"; label = "COMPRA LOGRADA";
                           } else if (row.event_category === 'market_purchase') {
                              Icon = Truck; color = "text-amber-400/80"; label = "VENTA MERCADO";
                           } else if (row.event_category === 'failed_purchase') {
                              Icon = AlertTriangle; color = "text-red-400 bg-red-500/10 border-red-500/30"; label = "FALLO OPERACIÓN";
                           } else if (row.event_category === 'restock') {
                              Icon = Download; color = "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"; label = "RESTOCK DETECTADO";
                           }

                           return (
                              <div key={index} className={`flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[10px] font-mono p-3 bg-surface-900 border border-surface-700 hover:border-surface-600 transition-colors uppercase ${color}`}>
                                 <div className="flex items-center gap-3">
                                    <span className="text-surface-500">{time}</span>
                                    <Icon size={14} />
                                    <span className="font-bold">{label || row.type.toUpperCase()}</span>
                                 </div>
                                 <div className="flex gap-4 items-center">
                                    {row.volume_change !== undefined && (
                                       <span className={row.volume_change > 0 ? "text-emerald-400" : "text-red-400"}>
                                          {row.volume_change > 0 ? "+" : ""}{row.volume_change}U
                                       </span>
                                    )}
                                    {row.total_stock !== undefined && (
                                       <span className="text-surface-500 border-l border-surface-700 pl-3">STOCK: {row.total_stock}U</span>
                                    )}
                                    {row.message && (
                                       <span className="text-[9px] lowercase opacity-80 max-w-[200px] truncate">{row.message}</span>
                                    )}
                                 </div>
                              </div>
                           );
                        })}
                     </div>
                  )}
               </div>
            )}

             {/* TAB: AUTOPILOT (Operación) */}
             {expandedTab === 'auto' && (
                <div className="space-y-4 animate-slide-up">
                   <div className="bg-surface-800 border border-amber-500/30 p-4 shadow-inner relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-2 opacity-10"><Target size={40} className="text-amber-500" /></div>
                      <div className="text-[10px] text-amber-500 font-mono tracking-widest uppercase mb-4 flex items-center gap-2 font-bold"><Target size={14}/> Sniper Autopilot Configuration</div>
                      
                      <label className={`w-full flex items-center justify-between p-3 mb-4 cursor-pointer border transition-all ${product.auto_buy ? 'bg-amber-500/10 border-amber-500/50 shadow-[0_0_15px_rgba(255,176,0,0.1)] text-amber-500 font-bold' : 'bg-surface-900 border-surface-700 text-surface-500 hover:border-surface-600'}`}>
                         <span className="text-[10px] font-mono uppercase tracking-widest flex items-center gap-2"><Crosshair size={14}/> AUTO-ENGAGE ON RECON</span>
                         <input type="checkbox" className="hidden" checked={product.auto_buy} onChange={async ()=>{
                             const newState = !product.auto_buy;
                             try {
                                 const result = await updateProduct(product.id, { auto_buy: newState });
                                 console.log('AUTO-BUY PATCH result:', result);
                                 product.auto_buy = newState;
                                 // Small delay to ensure DB flush before loadData refreshes
                                 await new Promise(r => setTimeout(r, 300));
                                 onToggle(product.id, { preventBackend: true });
                                 toast.success(`AUTO-ENGAGE ${newState ? 'ONLINE' : 'OFFLINE'}`, { icon: newState ? '🎯' : '⏸️', style: { background: '#1e293b', color: newState?'#ffb000':'#94a3b8', border: newState?'1px solid #ffb000':'1px solid #334155' }});
                             } catch(err) {
                                 console.error('AUTO-BUY PATCH failed:', err);
                                 toast.error(`Error activando autopilot: ${err.message}`, { style: { background: '#1e293b', color: '#ff003c', border: '1px solid #ff003c' }});
                             }
                         }} />
                         <div className={`w-10 h-5 border flex items-center px-1 transition-colors ${product.auto_buy ? 'border-amber-500 bg-amber-500/20 justify-end' : 'border-surface-600 bg-surface-900 justify-start'}`}>
                            <div className={`w-4 h-4 shadow-sm ${product.auto_buy ? 'bg-amber-500 shadow-[0_0_10px_rgba(255,176,0,0.8)]' : 'bg-surface-600'}`} />
                         </div>
                      </label>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                         <div className="space-y-4">
                           <div>
                              <label className="text-[10px] font-mono text-surface-400 tracking-wider block mb-2 font-bold uppercase">Unidades a Asegurar</label>
                              <input type="number" min="1" max="999" value={targetQty} onChange={e=>setTargetQty(e.target.value)} onBlur={handleSaveConfig} className="bg-surface-900 border border-surface-700 text-brand-400 w-full p-2 focus:border-brand-400 focus:outline-none text-center font-mono text-sm shadow-inner" />
                           </div>
                           <div>
                              <label className="text-[10px] font-mono text-surface-400 tracking-wider block mb-2 font-bold uppercase">Disparar si Stock {">="}</label>
                              <input type="number" min="1" max="999" value={minTrigger} onChange={e=>setMinTrigger(e.target.value)} onBlur={handleSaveConfig} className="bg-surface-900 border border-surface-700 text-amber-500 w-full p-2 focus:border-amber-500 focus:outline-none text-center font-mono text-sm shadow-inner" />
                           </div>
                         </div>

                         <div className="space-y-4">
                            <div>
                               <label className="text-[10px] font-mono text-surface-400 tracking-wider block mb-2 font-bold uppercase">Acción Post-Compra</label>
                               <select 
                                 value={product.post_purchase_action || 'pause'} 
                                 onChange={async (e) => {
                                     const action = e.target.value;
                                     await updateProduct(product.id, { post_purchase_action: action });
                                     toast.success(`POST-COMPRA: ${action.toUpperCase()}`, { style: { background: '#1e293b', color: '#59b0ff', border: '1px solid #1e293b' } });
                                 }}
                                 className="bg-surface-900 border border-surface-700 text-blue-400 w-full p-2 focus:border-blue-500 focus:outline-none font-mono text-xs shadow-inner appearance-none cursor-pointer"
                               >
                                 <option value="pause">PAUSAR TRAS ÉXITO (Safe Mode)</option>
                                 <option value="loop">VOLVER A EJECUTAR (Loop Mode)</option>
                               </select>
                               <div className="text-[9px] text-surface-500 mt-2 italic font-mono uppercase">* Define el comportamiento del sniper tras un checkout exitoso.</div>
                            </div>
                         </div>
                      </div>
                   </div>
                </div>
             )}

             {/* TAB: FIRE CONTROL (Manual Override) */}
             {expandedTab === 'snipe' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-slide-up">
                   {/* Panel Izquierdo: Engage */}
                   <div className="space-y-6">
                      <div className="bg-surface-800 border border-red-500/30 p-4 shadow-inner">
                         <div className="text-[10px] text-red-500 tracking-widest uppercase mb-4 flex items-center gap-2 font-bold font-mono"><Crosshair size={14}/> Manual Engagement System</div>
                         <p className="text-[10px] font-mono text-surface-400 mb-4 leading-relaxed uppercase">Advertencia: El override manual ignora los parámetros del autopilot y lanza una inyección directa al servidor de Dofimall.</p>
                      </div>

                      <button onClick={executeSnipe} disabled={isExecuting} className="w-full relative overflow-hidden bg-surface-900 border border-red-500/50 hover:bg-red-500/20 hover:border-red-500 transition-all p-5 group disabled:opacity-50">
                         <div className="absolute inset-0 bg-red-500 w-0 group-hover:w-full transition-all duration-300 -z-10 opacity-10"></div>
                         <span className="text-red-500 font-bold font-mono tracking-[0.2em] uppercase flex items-center justify-center gap-3 text-sm">
                            <Crosshair size={22} className={isExecuting?'animate-spin':''}/>
                            {isExecuting ? 'EJECUTANDO INYECCIÓN...' : 'OVERRIDE MANUAL / ENGAGE'}
                         </span>
                      </button>
                   </div>

                   {/* Panel Derecho: Consola y Scanner */}
                   <div className="flex flex-col gap-2 overflow-hidden h-72 lg:h-full border border-surface-700 bg-surface-900">
                      <div className="relative w-full aspect-video flex flex-col justify-center items-center crt-overlay group border-b border-surface-700">
                         {/* Radar grid style */}
                         <div className="absolute inset-0 z-0 bg-[linear-gradient(rgba(0,255,65,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,65,0.05)_1px,transparent_1px)] bg-[size:15px_15px]"></div>
                         
                         {/* Scope cross */}
                         <div className="absolute inset-x-0 top-1/2 h-px bg-brand-400/30 z-10"></div>
                         <div className="absolute inset-y-0 left-1/2 w-px bg-brand-400/30 z-10"></div>

                         {liveFrame ? (
                            <>
                              <img src={`data:image/jpeg;base64,${liveFrame}`} className="absolute top-0 right-0 w-full h-full object-contain filter opacity-90 z-0 glitch-image pointer-events-none" alt="Scanner" />
                              <div className="absolute inset-0 bg-brand-500/10 z-10 animate-scanline border-t border-brand-400/50 pointer-events-none"></div>
                            </>
                         ) : (
                            <div className="z-10 flex items-center justify-center text-brand-400/40 flex-col gap-3">
                               <Target className="w-8 h-8 opacity-50 relative animate-[radar_4s_linear_infinite]" />
                               <span className="text-[10px] tracking-wider font-mono">{isExecuting? 'ACQUIRING UPLINK...' : 'SCANNER STANDBY'}</span>
                            </div>
                         )}
                         <div className="absolute top-1 left-1.5 z-20 text-[8px] text-brand-400/50 font-mono">OP_CAM // V_1.0.0</div>
                         <div className="absolute top-1 right-1.5 z-20 flex gap-1">
                            <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></div>
                            <div className="text-[8px] text-red-500 font-mono uppercase">REC</div>
                         </div>
                      </div>
                      
                      <div className="flex-1 p-3 overflow-hidden relative border-t border-brand-400/30 bg-surface-900">
                         <pre ref={terminalRef} className="h-full overflow-y-auto text-[10px] text-brand-400 font-mono whitespace-pre-wrap terminal-text custom-scrollbar filter brightness-125 uppercase">
                            {logOutput || "> ESTADO: EN ESPERA.\n> SISTEMA_PREPARADO."}
                         </pre>
                         {isExecuting && <div className="absolute inset-0 pointer-events-none bg-brand-400/5 animate-pulse z-10"></div>}
                      </div>
                   </div>
                </div>
             )}

         </div>
      )}
    </div>
  );
}

// === EditProductModal ===
function EditProductModal({ product, categories, onClose, onSaved }) {
    const [name, setName] = useState(product?.name || '');
    const [url, setUrl] = useState(product?.url || '');
    const [categoryId, setCategoryId] = useState(product?.category_id || '');
    const [loading, setLoading] = useState(false);
  
    const handleSave = async () => {
      setLoading(true);
      try {
        const data = { name, url };
        if (categoryId) data.category_id = parseInt(categoryId);
        else data.category_id = null;
        await updateProduct(product.id, data);
        toast.success('METADATOS ACTUALIZADOS', { style: {background:'#1e293b',color:'#59b0ff',border:'1px solid #1e293b'}});
        onSaved();
      } catch(e) {
        toast.error('FALLO EN ACTUALIZAR METADATOS');
      } finally {
        setLoading(false);
      }
    };
  
    return (
      <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-surface-900/90 backdrop-blur-sm">
        <div className="bg-surface-900 border border-brand-400/50 w-full max-w-md clip-slanted shadow-[0_0_30px_rgba(59,130,246,0.1)]">
          <div className="px-6 py-4 flex items-center justify-between border-b border-brand-400/30 bg-brand-400/5 font-mono">
            <div className="flex items-center gap-3">
               <Terminal size={16} className="text-brand-400" />
               <h2 className="text-[10px] font-bold tracking-wider text-brand-400 uppercase">SOBREESCRIBIR TARGET</h2>
            </div>
            <button onClick={onClose} className="text-surface-500 hover:text-brand-400 transition-colors"><X size={18}/></button>
          </div>
          <div className="p-6 space-y-4 font-mono">
            <div>
              <label className="text-[10px] text-brand-400/60 tracking-wider mb-1 block uppercase">Designación (Nombre)</label>
              <input type="text" value={name} onChange={e=>setName(e.target.value)} className="w-full bg-surface-900 border border-surface-700 p-2 text-xs text-white focus:border-brand-400 outline-none transition-colors uppercase font-mono" />
            </div>
            <div>
              <label className="text-[10px] text-brand-400/60 tracking-wider mb-1 block uppercase">Coordenadas (URL)</label>
              <input type="text" value={url} onChange={e=>setUrl(e.target.value)} className="w-full bg-surface-900 border border-surface-700 p-2 text-xs text-white focus:border-brand-400 outline-none transition-colors font-mono" />
            </div>
            <div>
              <label className="text-[10px] text-brand-400/60 tracking-wider mb-1 block uppercase">Tipo Blanco (Categoría)</label>
              <select value={categoryId} onChange={e=>setCategoryId(e.target.value)} className="w-full bg-surface-900 border border-surface-700 p-2 text-xs text-white focus:border-brand-400 outline-none uppercase font-mono">
                 <option value="">INDEPENDIENTE / NO_CLASS</option>
                 {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <button onClick={handleSave} disabled={loading} className="w-full bg-brand-500/20 hover:bg-brand-400/30 border border-brand-400 text-brand-400 font-bold tracking-[0.2em] py-3 mt-4 flex items-center justify-center gap-2 disabled:opacity-50 transition-colors uppercase text-xs font-mono">
                {loading ? <Activity size={14} className="animate-spin" /> : <Database size={14} />} UPLOAD DATA
            </button>
          </div>
        </div>
      </div>
    );
}

export default function ProductList({ products, loading, onDelete, onToggle, onCheckout, onAddBulk }) {
  const [editingProduct, setEditingProduct] = useState(null);
  const [categories, setCategories] = useState([]);
  const [catFilter, setCatFilter] = useState('all');
  
  useEffect(()=>{ fetchCategories().then(setCategories).catch(()=>{}); }, []);
  const fileInputRef = useRef(null);

  if (loading) return <div className="text-center py-16 font-mono text-[10px] text-brand-400/50 animate-pulse uppercase tracking-wider">ESTABLECIENDO UPLINK...</div>;

  const filteredProducts = products.filter(p => {
    if (catFilter === 'all') return true;
    if (catFilter === 'null') return p.category_id === null;
    return p.category_id === parseInt(catFilter);
  });

  if (products.length === 0) {
    return (
      <div className="text-center py-16 font-mono text-surface-500 border border-surface-800 border-dashed m-4">
        <Target size={30} className="mx-auto mb-3 opacity-30" />
        <p className="text-[10px] uppercase tracking-wider">Base de datos vacía - Asignar nuevos blancos.</p>
      </div>
    );
  }

  const handleExport = () => {
    const header = "Nombre,URL\n";
    const lines = products.map(p => `"${(p.name || '').replace(/"/g, '""')}","${p.url}"`);
    const csvContent = "data:text/csv;charset=utf-8," + header + lines.join("\n");
    const link = document.createElement("a");
    link.href = encodeURI(csvContent);
    link.download = `TACTICAL-TARGETS-${new Date().getTime()}.csv`;
    link.click();
  };

  const handleImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const lines = event.target.result.split('\n');
      const items = [];
      let startIdx = (lines.length > 0 && lines[0].toLowerCase().includes('url')) ? 1 : 0;
      for (let i = startIdx; i < lines.length; i++) {
        let line = lines[i].trim();
        if (!line) continue;
        const parts = line.split(',');
        if (parts.length >= 2) {
           const rawName = parts.slice(0, -1).join(','); 
           const name = rawName.replace(/^"|"$/g, '').replace(/""/g, '"');
           const url = parts[parts.length - 1].replace(/^"|"$/g, '').trim();
           if (url.startsWith('http')) items.push({ name, url });
        } else if (parts.length === 1 && line.includes('http')) {
           items.push({ url: line.replace(/^"|"$/g, '').trim() });
        }
      }
      if (items.length > 0 && onAddBulk) onAddBulk(items);
      else toast.error("INTEL CORRUPTA - NO URLS", { style: {background:'#1e293b',color:'#ff003c'}});
    };
    reader.readAsText(file);
    e.target.value = null; 
  };

  return (
    <div className="space-y-4 relative z-0">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 px-1 pb-2 border-b border-surface-700">
         <div className="flex items-center gap-4">
           <span className="text-[10px] font-mono font-bold text-brand-400 uppercase tracking-widest flex items-center gap-2">
              <Crosshair size={14} /> {filteredProducts.length} BLANCOS ACTIVOS
           </span>
           {categories.length > 0 && (
              <select value={catFilter} onChange={e => setCatFilter(e.target.value)} className="bg-surface-800 border border-surface-700 text-[10px] uppercase font-mono text-brand-400/80 rounded-none px-2 py-1.5 focus:border-brand-400 outline-none">
                <option value="all">TODOS LOS SECTORES</option>
                <option value="null">SIN CLASIFICAR</option>
                {categories.map(c => <option key={c.id} value={c.id}>SEC: {c.name}</option>)}
              </select>
           )}
         </div>
         
         <div className="flex items-center gap-2">
           <input type="file" accept=".csv" ref={fileInputRef} className="hidden" onChange={handleImport} />
           <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-2 text-[10px] font-mono font-bold text-blue-400 hover:bg-blue-500/10 px-3 py-2 border border-blue-500/30 uppercase tracking-wider transition-colors">
              <Upload size={12} /> CARGAR_INTEL
           </button>
           <button onClick={handleExport} className="flex items-center gap-2 text-[10px] font-mono font-bold text-amber-500 hover:bg-amber-500/10 px-3 py-2 border border-amber-500/30 uppercase tracking-wider transition-colors">
              <Download size={12} /> EXPORT_INTEL
           </button>
         </div>
      </div>

      <div className="space-y-4">
        {filteredProducts.length === 0 ? (
           <div className="text-center py-10 font-mono text-surface-500 text-[10px] tracking-wider uppercase">
             SECTOR LIMPIO - NO HAY OBJETIVOS EN ESTE FILTRO
           </div>
        ) : (
           filteredProducts.map((product, i) => (
             <ProductItem 
               key={product.id}
               product={product}
               i={i}
               onOpenEdit={setEditingProduct}
               onDelete={onDelete}
               onToggle={onToggle}
               onCheckout={onCheckout}
             />
           ))
        )}
      </div>

      {editingProduct && (
        <EditProductModal product={editingProduct} categories={categories} onClose={() => setEditingProduct(null)} onSaved={() => { setEditingProduct(null); window.dispatchEvent(new CustomEvent('refresh-products')); }} />
      )}
    </div>
  );
}
