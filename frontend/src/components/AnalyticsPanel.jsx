import React, { useState, useEffect } from 'react';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceDot, Area, ComposedChart, Bar
} from 'recharts';
import { fetchProductAnalytics, fetchProducts } from '../utils/api';
import { Activity, BarChart2, Crosshair, TrendingDown, Target, Clock, CalendarDays } from 'lucide-react';
import toast from 'react-hot-toast';

// Formatters
const formatTimeLabel = (val, period) => {
  const d = new Date(val);
  if (period === '1h' || period === '24h') {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString([], { day: '2-digit', month: '2-digit' });
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const time = new Date(label).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const date = new Date(label).toLocaleDateString();
    
    return (
      <div className="bg-surface-800 border border-surface-700/50 p-4 rounded-xl shadow-2xl relative z-50 min-w-[200px]">
        <p className="text-surface-300 text-xs mb-3 font-medium border-b border-surface-700/50 pb-2">
          {date} <span className="font-mono ml-2 text-surface-200">{time}</span>
        </p>
        
        {data.is_event ? (
          <div className="flex flex-col gap-1">
            {data.event_category === 'my_purchase' && (
              <span className="text-xs font-bold text-brand-400 flex items-center gap-2">
                <Target size={14}/> MI COMPRA (SNIPE)
              </span>
            )}
            {data.event_category === 'market_purchase' && (
              <span className="text-xs font-bold text-red-400 flex items-center gap-2">
                <TrendingDown size={14}/> COMPRA DEL MERCADO
              </span>
            )}
            {data.event_category === 'failed_purchase' && (
              <span className="text-xs font-bold text-surface-400 flex items-center gap-2">
                <Crosshair size={14}/> INTENTO FALLIDO
              </span>
            )}
            <span className="text-sm font-semibold text-white mt-1">{data.message || `Descenso de stock detectado`}</span>
            {data.volume_change < 0 && (
              <span className="text-xs text-surface-400 font-mono mt-1">Volumen: {Math.abs(data.volume_change)}u</span>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex px-2 py-1 items-center justify-between">
              <span className="text-surface-400 text-xs">Stock Global Total:</span>
              <span className="text-emerald-400 font-mono font-bold text-sm tracking-wide">{data.total_stock}u</span>
            </div>
            
            <div className="bg-surface-900/50 rounded p-2 border border-surface-700/30 space-y-1">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-1.5 border-l-2 border-brand-500 pl-1">
                  <span className="text-surface-300 text-xs">En Almacén</span>
                </div>
                <span className="text-white font-mono font-semibold text-xs">{data.warehouse_stock}u</span>
              </div>
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-1.5 border-l-2 border-emerald-500 pl-1">
                  <span className="text-surface-300 text-xs">En Tránsito (Gap)</span>
                </div>
                <span className="text-white font-mono font-semibold text-xs">{(data.transit_stock || 0)}u</span>
              </div>
            </div>

            {(data.volume_change !== 0 && data.volume_change !== undefined) && (
              <div className="flex justify-between items-center px-2 py-1 mt-1 border-t border-surface-700/30">
                <span className="text-surface-400 text-xs uppercase tracking-wider">Flujo:</span>
                <span className={`font-mono font-bold text-xs px-1.5 py-0.5 rounded ${data.volume_change > 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                  {data.volume_change > 0 ? '+' : ''}{data.volume_change}u
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
  return null;
};

export default function AnalyticsPanel() {
  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [period, setPeriod] = useState('24h');
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(false);

  const periods = [
    { id: '1h', label: '1 Hora', icon: <Clock size={12}/> },
    { id: '24h', label: '24 Horas', icon: <Clock size={12}/> },
    { id: '7d', label: '7 Días', icon: <CalendarDays size={12}/> },
    { id: '30d', label: '30 Días', icon: <CalendarDays size={12}/> },
    { id: 'all', label: 'Histórico', icon: <Activity size={12}/> }
  ];

  useEffect(() => {
    const loadProducts = async () => {
      try {
        const prod = await fetchProducts();
        setProducts(prod);
        if (prod.length > 0 && !selectedProductId) {
          setSelectedProductId(prod[0].id);
        }
      } catch (e) {
        toast.error("Error al cargar productos para analíticas");
      }
    };
    loadProducts();
  }, []);

  useEffect(() => {
    if (!selectedProductId) return;
    
    const loadAnalytics = async () => {
      setLoading(true);
      try {
        const data = await fetchProductAnalytics(selectedProductId, period);
        
        let lastStock = { total_stock: 0, warehouse_stock: 0, transit_stock: 0 };
        
        const chartData = data.timeline.map((item) => {
          if (item.type === "stock") {
            lastStock = { 
               total_stock: item.total_stock,
               warehouse_stock: item.warehouse_stock || 0,
               transit_stock: item.transit_stock || 0
            };
            return {
              ...item,
              time: item.timestamp,
              is_event: false,
              chart_volume: item.volume_change ? Math.abs(item.volume_change) : 0
            };
          } else {
            return {
              ...lastStock, 
              time: item.timestamp,
              is_event: true,
              message: item.message,
              event_category: item.event_category
            };
          }
        });
        
        setAnalyticsData({
          name: data.product_name,
          chartData: chartData,
          dataPoints: data.data_points
        });
        
      } catch (error) {
        setAnalyticsData({ chartData: [] });
      } finally {
        setLoading(false);
      }
    };
    
    loadAnalytics();
    
    const interval = setInterval(loadAnalytics, 15000);
    return () => clearInterval(interval);
  }, [selectedProductId, period]);

  return (
    <div className="bg-surface-800/20 rounded-xl border border-surface-700/50 p-6 flex flex-col h-[650px]">
      
      {/* HEADER & CONTROLES */}
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center mb-6 gap-4">
        <div>
           <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity className="text-brand-500" />
              Pulse del Mercado
           </h2>
           <p className="text-sm text-surface-400 mt-1">Volumen de demanda y detección de compras tácticas.</p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3 w-full xl:w-auto">
          {/* Selector de Periodo Minimalista */}
          <div className="flex bg-surface-900 border border-surface-700/50 p-1 rounded-lg">
            {periods.map(p => (
               <button
                 key={p.id}
                 onClick={() => setPeriod(p.id)}
                 className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                    period === p.id 
                       ? 'bg-brand-500/10 border border-brand-500/30 text-brand-400 shadow-[0_0_10px_rgba(56,189,248,0.1)]' 
                       : 'text-surface-400 hover:text-surface-200 hover:bg-surface-800/50 border border-transparent'
                 }`}
               >
                 {p.icon}
                 <span className="hidden sm:inline">{p.label}</span>
               </button>
            ))}
          </div>

          <select
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="w-full sm:w-64 bg-surface-900 border border-surface-700 text-sm text-white rounded-lg px-3 py-2 outline-none focus:border-brand-500"
          >
            {products.map(p => (
              <option key={p.id} value={p.id}>
                {p.name !== 'Sin nombre' ? p.name.substring(0,40) : p.url.split('/').pop().substring(0,20)}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {/* CUERPO GRÁFICA */}
      {loading && !analyticsData && (
        <div className="flex-1 flex items-center justify-center">
            <div className="animate-spin text-brand-500"><Activity size={32} /></div>
        </div>
      )}
      
      {!loading && analyticsData && analyticsData.chartData.length === 0 && (
         <div className="flex-1 flex flex-col items-center justify-center text-surface-400 gap-3 bg-surface-900/30 rounded-lg">
            <BarChart2 size={40} className="opacity-50" />
            <p>Todavía no hay suficientes datos para graficar este periodo.</p>
         </div>
      )}
      
      {analyticsData && analyticsData.chartData.length > 0 && (
        <>
          <div className="flex justify-end mb-2 px-4 gap-4 text-[10px] uppercase font-bold tracking-wider">
             <span className="flex items-center gap-1 text-emerald-400"><div className="w-2 h-2 rounded bg-emerald-500"></div> Total / Tránsito</span>
             <span className="flex items-center gap-1 text-brand-500"><div className="w-2 h-2 rounded bg-brand-500"></div> Almacén Real</span>
             <span className="flex items-center gap-1 text-surface-500"><div className="w-2 h-2 rounded bg-surface-600"></div> Volumen (Flujo)</span>
             <span className="flex items-center gap-1 text-brand-400 ml-4"><Target size={12}/> Tus Compras</span>
             <span className="flex items-center gap-1 text-red-500"><TrendingDown size={12}/> Mercado</span>
          </div>

          <div className="flex-1 w-full relative">
             <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={analyticsData.chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorWarehouse" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} vertical={false} />
                  
                  <XAxis 
                    dataKey="time" 
                    tickFormatter={(val) => formatTimeLabel(val, period)} 
                    stroke="#64748b" 
                    fontSize={11}
                    tickMargin={10}
                    minTickGap={30}
                  />
                  
                  {/* Eje Izquierdo: Nivel Stock */}
                  <YAxis 
                    yAxisId="left"
                    stroke="#10b981" 
                    fontSize={11}
                    tickFormatter={(val) => `${val}`}
                    domain={['dataMin - 10', 'auto']}
                  />
                  
                  {/* Eje Derecho: Volumen de Cambios */}
                  <YAxis 
                    yAxisId="right" 
                    orientation="right" 
                    stroke="#475569" 
                    fontSize={11}
                    tickFormatter={(val) => `${val}u`}
                    domain={[0, 'auto']}
                  />

                  <Tooltip content={<CustomTooltip />} />
                  
                  {/* Barras de Volumen de Cambios (Eje Secundario) */}
                  <Bar 
                     yAxisId="right" 
                     dataKey="chart_volume" 
                     fill="#475569" 
                     opacity={0.4} 
                     radius={[2, 2, 0, 0]} 
                     isAnimationActive={false}
                     maxBarSize={20}
                  />

                  {/* Área Principal: Nivel de Stock (Eje Principal) */}
                  <Area 
                      yAxisId="left"
                      type="stepAfter" 
                      dataKey="total_stock" 
                      name="Stock Total" 
                      stroke="#10b981" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorTotal)" 
                      isAnimationActive={false}
                  />

                  {/* Área Secundaria Inferior: Stock Real en Almacén */}
                  <Area 
                      yAxisId="left"
                      type="stepAfter" 
                      dataKey="warehouse_stock" 
                      name="Stock Almacén" 
                      stroke="#0ea5e9" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorWarehouse)" 
                      isAnimationActive={false}
                  />

                  {/* Renderizar Eventos Inteligentes superpuestos sobre el stock total */}
                  {analyticsData.chartData.map((d, index) => {
                     if (d.event_category === 'my_purchase') {
                        return (
                           <ReferenceDot 
                              key={`event-${index}`} 
                              yAxisId="left"
                              x={d.time} 
                              y={d.total_stock} 
                              r={6} 
                              fill="#0ea5e9" 
                              stroke="#0284c7" 
                              strokeWidth={2} 
                           />
                        )
                     }
                     if (d.event_category === 'market_purchase') {
                        return (
                           <ReferenceDot 
                              key={`event-${index}`} 
                              yAxisId="left"
                              x={d.time} 
                              y={d.total_stock} 
                              r={4} 
                              fill="#ef4444" 
                              stroke="#b91c1c" 
                              strokeWidth={1} 
                           />
                        )
                     }
                     if (d.event_category === 'failed_purchase') {
                        return (
                           <ReferenceDot 
                              key={`event-${index}`} 
                              yAxisId="left"
                              x={d.time} 
                              y={d.total_stock} 
                              r={4} 
                              fill="transparent" 
                              stroke="#94a3b8" 
                              strokeWidth={2}
                              strokeDasharray="2 2"
                           />
                        )
                     }
                     return null;
                  })}
                </ComposedChart>
             </ResponsiveContainer>
          </div>
        </>
      )}
      
    </div>
  );
}
