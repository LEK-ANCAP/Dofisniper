import { useState, useEffect } from 'react';
import {
  Trash2, Pause, Play, ExternalLink,
  ShoppingCart, AlertTriangle, Package, Edit3, BarChart, X, Zap, Target, Eye, Database, Crosshair, Terminal, Camera, Activity, Download, Upload, MapPin, Truck, RefreshCw
} from 'lucide-react';
import toast from 'react-hot-toast';
import { updateProduct, manualCheckout, fetchLogs, fetchLiveView, fetchProductHistory, fetchCategories } from '../utils/api';
import { playTacticalClick, playEngageAlarm, playMissionSuccess, playMissionFail, startMorseTransmission, stopMorseTransmission } from '../utils/tacticalAudio';

const STATUS_CONFIG = {
  monitoring: { label: 'RECON', border: 'border-brand-400/50', text: 'text-brand-400', icon: Eye },
  in_stock: { label: 'DISPONIBLE', border: 'border-emerald-400', text: 'text-emerald-400', icon: Package },
  purchasing: { label: 'INFILTRACIÓN', border: 'border-amber-500 animate-pulse', text: 'text-amber-500', icon: Zap },
  reserved: { label: 'ASEGURADO', border: 'border-blue-500', text: 'text-blue-400', icon: ShoppingCart },
  paused: { label: 'SUSPENDIDO', border: 'border-surface-600', text: 'text-surface-500', icon: Pause },
  error: { label: 'FALLA TÁCTICA', border: 'border-red-500', text: 'text-red-500', icon: AlertTriangle },
};

function TacticalBadge({ children, active, className="" }) {
    return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] uppercase  font-bold border tracking-wider ${active ? 'bg-brand-500/10 text-brand-400 border-brand-400/50 shadow-[0_0_8px_rgba(0,255,65,0.2)]' : 'bg-surface-900 border-surface-700 text-surface-500'} ${className}`}>
           {children}
        </span>
    )
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
      <span className="flex items-center gap-1 text-[9px] text-amber-400 border border-amber-500/30 bg-amber-500/10 px-1 py-0.5 font-mono tracking-widest uppercase ml-2">
         <RefreshCw size={10} className={`${secs < 3 ? 'animate-spin' : ''}`} /> T-{secs}S
      </span>
   );
}

function ProductItem({ product, i, onDelete, onToggle, onCheckout, onOpenEdit }) {
  const [expandedTab, setExpandedTab] = useState(null); // 'lz', 'analytics', 'snipe'
  const [targetQty, setTargetQty] = useState(product.target_quantity || 1);
  const [minTrigger, setMinTrigger] = useState(product.min_stock_to_trigger || 1);
  
  // Terminal / Escáner logic
  const [logOutput, setLogOutput] = useState('');
  const [isExecuting, setIsExecuting] = useState(product.status === 'purchasing');
  const [liveFrame, setLiveFrame] = useState(null);
  const terminalRef = useRef(null);
  
  // Analytics logic
  const [history, setHistory] = useState([]);
  const [analyticsLoaded, setAnalyticsLoaded] = useState(false);

  const statusConf = STATUS_CONFIG[product.status] || STATUS_CONFIG.monitoring;
  const StatusIcon = statusConf.icon;
  const totalStock = (product.warehouse_stock || 0) + (product.transit_stock || 0);

  // Focus effect
  useEffect(() => {
    if (expandedTab === 'snipe') {
        // Load initial logs
        fetchLogs(50).then(logs => {
            const myLogs = (Array.isArray(logs) ? logs : []).filter(l => 
                l.product_id === product.id && (l.action.includes('purchase') || l.action.includes('checkout'))
            ).reverse();
            if (myLogs.length > 0) {
               const hist = myLogs.map(l => `[${new Date(l.created_at).toLocaleTimeString('en-US',{hour12:false})}] ${l.action.toUpperCase()}\n${l.message}`).join('\n\n');
               setLogOutput(`>> RECUPERANDO HISTORIAL TÁCTICO...\n${hist}\n>> Sistema listo. Esperando comandos...`);
            }
        }).catch(()=>{});
    } else if (expandedTab === 'analytics' && !analyticsLoaded) {
        fetchProductHistory(product.id).then(res => {
            if (res.labels && res.datasets) {
                const mappedHistory = res.labels.map((label, idx) => ({
                    timestamp: label,
                    warehouse_stock: res.datasets.warehouse[idx],
                    transit_stock: res.datasets.transit[idx]
                })).reverse();
                setHistory(mappedHistory);
            } else {
                setHistory(Array.isArray(res) ? res : res.history || []);
            }
            setAnalyticsLoaded(true);
        }).catch(()=>{});
    }
  }, [expandedTab, product.id, analyticsLoaded]);

  // Live Frame Polling
  useEffect(() => {
    let timer;
    if (isExecuting && expandedTab === 'snipe') {
      timer = setInterval(async () => {
        try {
          const res = await fetchLiveView(product.id);
          if (res.frame) setLiveFrame(res.frame);
        } catch (e) {}
      }, 1000);
    } else {
      setLiveFrame(null);
    }
    return () => clearInterval(timer);
  }, [isExecuting, expandedTab, product.id]);

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [logOutput, expandedTab]);

  const handleSaveConfig = async () => {
    try {
       await updateProduct(product.id, { target_quantity: Number(targetQty), min_stock_to_trigger: Number(minTrigger) });
       toast.success('Parámetros actualizados', { style: { background: '#1e293b', color: '#59b0ff', border: '1px solid #1e293b' } });
    } catch(e) {
       toast.error('Error táctico');
    }
  };

  const executeSnipe = async () => {
      setIsExecuting(true);
      playEngageAlarm();
      startMorseTransmission();
      setLogOutput(">> INICIALIZANDO SECUENCIA OVERRIDE...\n>> Inyectando hilos ofensivos (Playwright)...\n>> Buscando brecha en sistema objetivo...");
      try {
          const res = await manualCheckout(product.id);
          setLogOutput(prev => prev + `\n\n>> [RESULTADO: ${res.success ? 'ASEGURADO' : 'FALLIDO'}]\n>> ${res.message}`);
          if (res.success) {
             onCheckout(product.id);
             playMissionSuccess();
          } else {
             playMissionFail();
          }
      } catch (e) {
          playMissionFail();
          setLogOutput(prev => prev + `\n\n>> [CRITICAL FAILURE]\n>> ${e.message}`);
      } finally {
          setIsExecuting(false);
          stopMorseTransmission();
      }
  };

  return (
    <div className={`bg-surface-800 border ${expandedTab ? 'border-brand-400/60 shadow-[0_0_20px_rgba(0,255,65,0.05)]' : 'border-surface-700'} mb-4 clip-slanted transition-all duration-300 animate-slide-up`} style={{ animationDelay: `${i * 20}ms` }}>
      {/* Header Visible (Compact) */}
      <div className="p-3 sm:p-4 flex flex-col sm:flex-row gap-4 items-start sm:items-center relative z-20">
        {/* Imagen HUD */}
        <div className="relative w-16 h-16 border border-brand-400/30 flex-shrink-0 overflow-hidden group">
           {product.category && (
             <div className="absolute top-0 left-0 text-[8px] bg-surface-900/90 text-brand-400 px-1 z-20 border-b border-r border-brand-400/30 uppercase tracking-widest font-bold">
               [{product.category.name}]
             </div>
           )}
           {/* Scope crosshair minimal */}
           <div className="absolute inset-0 flex items-center justify-center z-10 opacity-30 pointer-events-none">
              <div className="w-1/2 h-px bg-brand-400"></div>
              <div className="absolute h-1/2 w-px bg-brand-400"></div>
           </div>
           {product.image_url ? (
             <img src={`/api/products/image-proxy?url=${encodeURIComponent(product.image_url)}`} className="w-full h-full object-cover mix-blend-screen opacity-90" alt="Target" />
           ) : <Crosshair className="text-brand-400/50 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0 ">
           <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className="text-white font-bold text-sm truncate uppercase tracking-tight" style={{ textShadow: '0 0 8px rgba(255,255,255,0.2)' }}>
                 {product.name || 'TARGET_UNKNOWN_ID'}
              </h3>
              
              <a href={product.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-brand-400 hover:text-white transition-colors uppercase cursor-pointer border border-brand-400/30 px-2 py-0.5" title="Ver Objetivo (External)">
                 <ExternalLink size={12} /> TARGET_URL
              </a>

              {/* Badges */}
              <TacticalBadge active={product.is_active}>
                 <StatusIcon size={10} className={product.is_active ? statusConf.text : ''} /> 
                 {product.is_active ? statusConf.label : 'SUSPENDIDO'}
              </TacticalBadge>
              <ScanCountdown isActive={product.is_active} />
           </div>

           <div className="flex items-center gap-3 text-xs text-surface-300 mt-2">
              <span className={`font-bold px-2 py-1 border flex items-center gap-1 ${product.warehouse_stock > 0 ? 'text-emerald-400 border-emerald-400/30 bg-emerald-500/10' : 'text-surface-500 border-surface-700 bg-surface-800'}`}>
                 <MapPin size={12} /> LOCAL: {product.warehouse_stock || 0}
              </span>
              <span className={`font-bold px-2 py-1 border flex items-center gap-1 ${product.transit_stock > 0 ? 'text-emerald-400 border-emerald-400/30 bg-emerald-500/10' : 'text-surface-500 border-surface-700 bg-surface-800'}`}>
                 <Truck size={12} /> TRANSIT: {product.transit_stock || 0}
              </span>
              {(totalStock > 0) && (
                 <span className="inline-flex items-center gap-1 text-[10px] font-bold text-surface-900 bg-emerald-500 px-2 py-1 tracking-wider">
                     <Package size={10}/> TOTAL: {totalStock}U
                 </span>
              )}
           </div>
        </div>

        {/* Actions (Derecha) */}
        <div className="flex sm:flex-col items-center sm:items-end gap-2 w-full sm:w-auto relative z-20">
           {/* Control de Tabs Navigación */}
           <div className="flex bg-surface-900 p-0.5 border border-surface-700">
              <button onMouseEnter={() => playTacticalClick(0.01)} onClick={() => { playTacticalClick(); setExpandedTab(expandedTab === 'lz' ? null : 'lz'); }} className={`p-2 flex items-center gap-2 text-xs  uppercase tracking-wider transition-colors ${expandedTab === 'lz' ? 'bg-brand-400 text-surface-900 font-bold border border-brand-400' : 'text-brand-400/70 hover:bg-brand-500/20 hover:text-brand-400 border border-transparent'}`}>
                 <MapPin size={16} className={expandedTab==='lz'?'text-surface-900':'text-brand-400'} /> ALMACENES
              </button>
              <button onMouseEnter={() => playTacticalClick(0.01)} onClick={() => { playTacticalClick(); setExpandedTab(expandedTab === 'analytics' ? null : 'analytics'); }} className={`p-2 flex items-center gap-2 text-xs  uppercase tracking-wider transition-colors ${expandedTab === 'analytics' ? 'bg-brand-400 text-surface-900 font-bold border border-brand-400' : 'text-brand-400/70 hover:bg-brand-500/20 hover:text-brand-400 border border-transparent'}`}>
                 <Database size={16} className={expandedTab==='analytics'?'text-surface-900':'text-brand-400'} /> INTEL
              </button>
              <button onMouseEnter={() => playTacticalClick(0.01)} onClick={() => { playTacticalClick(); setExpandedTab(expandedTab === 'snipe' ? null : 'snipe'); }} className={`p-2 flex items-center gap-2 text-xs  uppercase tracking-wider transition-colors ${expandedTab === 'snipe' ? 'bg-red-500 text-surface-900 font-bold border border-red-500' : 'text-red-500/70 hover:bg-red-500/20 hover:text-red-500 border border-transparent'}`}>
                 <Target size={16} className={expandedTab==='snipe'?'text-surface-900':'text-red-500'} /> FORCE_CMD
              </button>
           </div>
           <div className="flex gap-2 ml-auto sm:ml-0 mt-1">
               <button onClick={() => { playTacticalClick(); onToggle(product.id); }} className={`p-2 border border-surface-600 hover:border-brand-400 transition-all ${product.is_active ? 'bg-brand-500/20' : 'bg-surface-800'}`} title={product.is_active ? 'SUSPENDER' : 'ACTIVAR RECON'}>
                  {product.is_active ? <Pause size={16} className="text-amber-500" /> : <Play size={16} className="text-brand-400" />}
               </button>
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
                     <div className="text-surface-400 text-sm p-6 bg-surface-800 w-full text-center border border-surface-700 border-dashed">NO HAY COORDENADAS ALMACENADAS DE LZ</div>
                  ) : (
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {product.warehouse_breakdown.map((w, index) => (
                           <div key={index} className="bg-surface-800 border border-surface-700 p-3 flex items-center justify-between group hover:border-brand-400">
                              <span className="text-xs text-surface-300 truncate w-1/2 pr-2 leading-tight uppercase group-hover:text-white transition-colors">{w.name} ({w.area})</span>
                              <div className="flex items-center gap-2 text-[10px] flex-shrink-0">
                                 <span className={`px-2 py-1 border flex items-center gap-1 ${w.warehouse_stock > 0 ? 'border-emerald-400/50 text-emerald-400 bg-emerald-500/10 font-bold' : 'border-surface-700 text-surface-500 bg-surface-900/50'}`}>
                                    <MapPin size={10} className="hidden sm:block" />LOCAL: {w.warehouse_stock}
                                 </span>
                                 <span className={`px-2 py-1 border flex items-center gap-1 ${w.transit_stock > 0 ? 'border-emerald-400/50 text-emerald-400 bg-emerald-500/10 font-bold' : 'border-surface-700 text-surface-500 bg-surface-900/50'}`}>
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
                  <div className="text-xs text-blue-400 mb-3 tracking-wider uppercase flex items-center gap-2"><Database size={16}/> Actividad Reciente del Objetivo</div>
                  {history.length === 0 ? (
                     <div className="text-surface-400 text-sm p-6 bg-surface-800 w-full text-center border border-surface-700 border-dashed">DESCARGANDO TELEMETRÍA HISTÓRICA / SIN DATOS</div>
                  ) : (
                     <div className="space-y-1 h-48 overflow-y-auto custom-scrollbar pr-2">
                        {history.map((row, index) => (
                           <div key={index} className="flex justify-between items-center text-xs p-2 bg-surface-900 border border-surface-700 text-surface-300  hover:bg-surface-800 hover:text-white transition-colors">
                             <span className="text-brand-400/70">{row.timestamp || row.created_at}</span>
                             <div className="flex gap-4">
                               <span className="text-brand-400 font-bold">{row.warehouse_stock} LOCAL</span>
                               <span className="text-blue-400 font-bold">{row.transit_stock} TRANS</span>
                             </div>
                           </div>
                        ))}
                     </div>
                  )}
               </div>
            )}

            {/* TAB: FIRE CONTROL (Config/Sniper) */}
            {expandedTab === 'snipe' && (
               <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Panel Izquierdo: Config & Engage */}
                  <div className="space-y-6">
                     <div className="bg-surface-800 border border-surface-700 p-4 shadow-inner">
                        <div className="text-xs text-amber-500 tracking-wider uppercase mb-4 flex items-center gap-2 font-bold"><Target size={16}/> Autopilot Override</div>
                        
                        <label className={`w-full flex items-center justify-between p-3 mb-4 cursor-pointer border transition-all ${product.auto_buy ? 'bg-amber-500/10 border-amber-500 shadow-[0_0_20px_rgba(255,176,0,0.2)] text-amber-500 font-bold' : 'bg-surface-900 border-surface-600 text-surface-400 hover:border-surface-400'}`}>
                           <span className="text-xs  uppercase tracking-wider flex items-center gap-2"><Zap size={16}/> AUTO-ENGAGE ON RECON</span>
                           <input type="checkbox" className="hidden" checked={product.auto_buy} onChange={async ()=>{
                               const newState = !product.auto_buy;
                               await updateProduct(product.id, { auto_buy: newState });
                               product.auto_buy = newState;
                               onToggle(product.id, { preventBackend: true });
                               toast.success(`AUTO-ENGAGE ${newState ? 'ONLINE' : 'OFFLINE'}`, { style: { background: '#1e293b', color: newState?'#ffb000':'#e2e8f0', border: newState?'1px solid #ffb000':'1px solid #334155' }});
                           }} />
                           <div className={`w-10 h-5 border flex items-center px-1 transition-colors ${product.auto_buy ? 'border-amber-500 bg-amber-500/20 justify-end' : 'border-surface-500 bg-surface-900 justify-start'}`}>
                              <div className={`w-4 h-4 shadow-sm ${product.auto_buy ? 'bg-amber-500 shadow-[0_0_10px_rgba(255,176,0,0.8)]' : 'bg-surface-500'}`} />
                           </div>
                        </label>

                        <div className="grid grid-cols-2 gap-4 mb-2 border-t border-surface-700 pt-4">
                           <div>
                              <label className="text-xs text-surface-400 tracking-wider block mb-2 font-bold">UNIDADES A ASEGURAR</label>
                              <input type="number" min="1" max="999" value={targetQty} onChange={e=>setTargetQty(e.target.value)} onBlur={handleSaveConfig} className="bg-surface-900 border border-surface-600 text-brand-400 w-full p-2 focus:border-brand-400 focus:outline-none text-center  text-sm shadow-inner" />
                           </div>
                           <div>
                              <label className="text-xs text-surface-400 tracking-wider block mb-2 font-bold">DISPARAR SI STOCK {">="}</label>
                              <input type="number" min="1" max="999" value={minTrigger} onChange={e=>setMinTrigger(e.target.value)} onBlur={handleSaveConfig} className="bg-surface-900 border border-surface-600 text-amber-500 w-full p-2 focus:border-amber-500 focus:outline-none text-center  text-sm shadow-inner" />
                           </div>
                        </div>
                     </div>

                     <button onClick={executeSnipe} disabled={isExecuting} className="w-full relative overflow-hidden bg-surface-800 border border-red-500 hover:bg-red-500/20 transition-all p-4 group disabled:opacity-50">
                        <div className="absolute inset-0 bg-red-500 w-0 group-hover:w-full transition-all duration-300 -z-10 opacity-20"></div>
                        <span className="text-red-500 font-bold  tracking-[0.2em] uppercase flex items-center justify-center gap-2 text-sm shadow-transparent">
                           <Crosshair size={20} className={isExecuting?'animate-spin':''}/>
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
                             <img src={`data:image/jpeg;base64,${liveFrame}`} className="absolute top-0 right-0 w-full h-full object-contain filter contrast-125 sepia-[0.3] hue-rotate-[-50deg] saturate-200 opacity-70 z-0" alt="Scanner" />
                             <div className="absolute inset-0 bg-brand-500/10 z-10 animate-scanline border-t border-brand-400/50 pointer-events-none"></div>
                           </>
                        ) : (
                           <div className="z-10 flex items-center justify-center text-brand-400/40 flex-col gap-3">
                              <Target className="w-8 h-8 opacity-50 relative animate-[radar_4s_linear_infinite]" />
                              <span className="text-[10px] tracking-wider">{isExecuting? 'ACQUIRING UPLINK...' : 'SCANNER STANDBY'}</span>
                           </div>
                        )}
                        <div className="absolute top-1 left-1.5 z-20 text-[8px] text-brand-400/50">OP_CAM // V_1.0.0</div>
                        <div className="absolute top-1 right-1.5 z-20 flex gap-1">
                           <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></div>
                           <div className="text-[8px] text-red-500">REC</div>
                        </div>
                     </div>
                     
                     <div className="flex-1 p-3 overflow-hidden relative border-t border-brand-400/30 bg-surface-900">
                        <pre ref={terminalRef} className="h-full overflow-y-auto text-xs text-brand-400  whitespace-pre-wrap terminal-text custom-scrollbar filter brightness-125">
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
          <div className="px-6 py-4 flex items-center justify-between border-b border-brand-400/30 bg-brand-400/5">
            <div className="flex items-center gap-3">
               <Terminal size={16} className="text-brand-400" />
               <h2 className="text-xs  font-bold tracking-wider text-brand-400">SOBREESCRIBIR TARGET</h2>
            </div>
            <button onClick={onClose} className="text-surface-500 hover:text-brand-400 transition-colors"><X size={18}/></button>
          </div>
          <div className="p-6 space-y-4 ">
            <div>
              <label className="text-[10px] text-brand-400/60 tracking-wider mb-1 block">DESIGNACIÓN (NOMBRE)</label>
              <input type="text" value={name} onChange={e=>setName(e.target.value)} className="w-full bg-surface-900 border border-surface-700 p-2 text-xs text-white focus:border-brand-400 outline-none transition-colors" />
            </div>
            <div>
              <label className="text-[10px] text-brand-400/60 tracking-wider mb-1 block">COORDENADAS (URL)</label>
              <input type="text" value={url} onChange={e=>setUrl(e.target.value)} className="w-full bg-surface-900 border border-surface-700 p-2 text-xs text-white focus:border-brand-400 outline-none transition-colors" />
            </div>
            <div>
              <label className="text-[10px] text-brand-400/60 tracking-wider mb-1 block">TIPO BLANCO (CATEGORÍA)</label>
              <select value={categoryId} onChange={e=>setCategoryId(e.target.value)} className="w-full bg-surface-900 border border-surface-700 p-2 text-xs text-white focus:border-brand-400 outline-none">
                 <option value="">INDEPENDIENTE / NO_CLASS</option>
                 {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <button onClick={handleSave} disabled={loading} className="w-full bg-brand-500/20 hover:bg-brand-400/30 border border-brand-400 text-brand-400 font-bold tracking-[0.2em] py-3 mt-4 flex items-center justify-center gap-2 disabled:opacity-50 transition-colors uppercase text-xs">
                {loading ? <Activity size={14} className="animate-spin" /> : <Database size={14} />} UPLOAD DATA
            </button>
          </div>
        </div>
      </div>
    );
}

// === ProductList MAIN COMPONENT ===
export default function ProductList({ products, loading, onDelete, onToggle, onCheckout, onAddBulk }) {
  const [editingProduct, setEditingProduct] = useState(null);
  const [categories, setCategories] = useState([]);
  const [catFilter, setCatFilter] = useState('all');
  
  useEffect(()=>{ fetchCategories().then(setCategories).catch(()=>{}); }, []);
  const fileInputRef = useRef(null);

  if (loading) return <div className="text-center py-16  text-brand-400/50 animate-pulse uppercase tracking-wider">ESTABLECIENDO UPLINK...</div>;

  const filteredProducts = products.filter(p => {
    if (catFilter === 'all') return true;
    if (catFilter === 'null') return p.category_id === null;
    return p.category_id === parseInt(catFilter);
  });

  if (products.length === 0) {
    return (
      <div className="text-center py-16  text-surface-500 border border-surface-800 border-dashed m-4">
        <Target size={30} className="mx-auto mb-3 opacity-30" />
        <p className="text-xs uppercase tracking-wider">Base de datos vacía - Asignar nuevos blancos.</p>
      </div>
    );
  }

  const handleExport = () => { /* Same standard logic */
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
           <span className="text-xs  font-bold text-brand-400 uppercase tracking-wider flex items-center gap-2">
              <Crosshair size={14} /> {filteredProducts.length} BLANCOS ACTIVOS
           </span>
           {categories.length > 0 && (
              <select value={catFilter} onChange={e => setCatFilter(e.target.value)} className="bg-surface-800 border border-surface-700 text-[10px] uppercase  text-brand-400/80 rounded-none px-2 py-1.5 focus:border-brand-400 outline-none">
                <option value="all">TODOS LOS SECTORES</option>
                <option value="null">SIN CLASIFICAR</option>
                {categories.map(c => <option key={c.id} value={c.id}>SEC: {c.name}</option>)}
              </select>
           )}
         </div>
         
         <div className="flex items-center gap-2">
           <input type="file" accept=".csv" ref={fileInputRef} className="hidden" onChange={handleImport} />
           <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-2 text-[10px]  font-bold text-blue-400 hover:bg-blue-500/10 px-3 py-2 border border-blue-500/30 uppercase tracking-wider transition-colors">
              <Upload size={12} /> CARGAR_INTEL
           </button>
           <button onClick={handleExport} className="flex items-center gap-2 text-[10px]  font-bold text-amber-500 hover:bg-amber-500/10 px-3 py-2 border border-amber-500/30 uppercase tracking-wider transition-colors">
              <Download size={12} /> EXPORT_INTEL
           </button>
         </div>
      </div>

      <div className="space-y-0">
        {filteredProducts.length === 0 ? (
           <div className="text-center py-10  text-surface-500 text-xs tracking-wider uppercase">
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
