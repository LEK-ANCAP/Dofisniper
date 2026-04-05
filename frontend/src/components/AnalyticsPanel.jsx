import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceDot, ReferenceLine, AreaChart, Area, ComposedChart, Bar
} from 'recharts';
import { fetchProductAnalytics, fetchProducts } from '../utils/api';
import { Activity, Thermometer, BarChart2, Package, Tag, Crosshair } from 'lucide-react';
import toast from 'react-hot-toast';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const time = new Date(label).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const isEvent = payload[0].payload.is_event;
    
    return (
      <div className="bg-surface-800 border border-surface-700/50 p-3 rounded-lg shadow-xl relative z-50">
        <p className="text-surface-300 text-xs mb-2 font-medium">{time} • {new Date(label).toLocaleDateString()}</p>
        
        {isEvent ? (
          <div className="flex flex-col gap-1">
            <span className="text-xs font-bold text-brand-500 uppercase flex items-center gap-2">
              <Crosshair size={12}/> Evento del Bot
            </span>
            <span className="text-sm font-semibold text-white">{payload[0].payload.message}</span>
          </div>
        ) : (
          <div className="space-y-1">
            {payload.map((entry, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-white text-sm font-medium">{entry.name}:</span>
                <span className="text-white text-sm font-bold">{entry.value} u</span>
              </div>
            ))}
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
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(false);

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
        const data = await fetchProductAnalytics(selectedProductId);
        
        // Formatear datos para Recharts
        let lastStock = { warehouse: 0, transit: 0, total: 0 };
        
        const chartData = data.timeline.map((item, idx) => {
          if (item.type === "stock") {
            lastStock = {
               warehouse: item.warehouse_stock,
               transit: item.transit_stock,
               total: item.total_stock,
               raw_time: item.timestamp
            };
            return {
              ...lastStock,
              time: item.timestamp,
              is_event: false
            };
          } else {
             // Es un evento
            return {
              ...lastStock, // Mantiene el hilo en el YAxis donde estaba la línea
              time: item.timestamp,
              is_event: true,
              message: item.message,
              event_name: item.event_name
            };
          }
        });
        
        setAnalyticsData({
          name: data.product_name,
          chartData: chartData
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
  }, [selectedProductId]);

  return (
    <div className="bg-surface-800/20 rounded-xl border border-surface-700/50 p-6 flex flex-col h-[550px]">
      
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <div>
           <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity className="text-brand-500" />
              Pulse del Mercado (Demanda & Reabastecimiento)
           </h2>
           <p className="text-sm text-surface-400 mt-1">Monitorea la velocidad con la que los competidores vacían el inventario.</p>
        </div>
        
        <div className="w-full sm:w-auto">
          <select
            value={selectedProductId}
            onChange={(e) => setSelectedProductId(e.target.value)}
            className="w-full sm:w-64 bg-surface-900 border border-surface-700 text-sm text-white rounded-lg px-3 py-2.5 outline-none focus:border-brand-500"
          >
            {products.map(p => (
              <option key={p.id} value={p.id}>
                {p.name !== 'Sin nombre' ? p.name : p.url.split('/').pop().substring(0,20)}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {loading && !analyticsData && (
        <div className="flex-1 flex items-center justify-center">
            <div className="animate-spin text-brand-500"><Activity size={32} /></div>
        </div>
      )}
      
      {!loading && analyticsData && analyticsData.chartData.length === 0 && (
         <div className="flex-1 flex flex-col items-center justify-center text-surface-400 gap-3 bg-surface-900/30 rounded-lg">
            <BarChart2 size={40} className="opacity-50" />
            <p>Todavía no hay suficientes datos históricos recolectados para graficar.</p>
            <p className="text-xs">El bot necesita experimentar al menos 1 cambio de stock real.</p>
         </div>
      )}
      
      {analyticsData && analyticsData.chartData.length > 0 && (
        <div className="flex-1 w-full relative">
           {/* Chart Container */}
           <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={analyticsData.chartData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorWarehouse" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} vertical={false} />
                <XAxis 
                  dataKey="time" 
                  tickFormatter={(val) => new Date(val).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} 
                  stroke="#64748b" 
                  fontSize={12}
                  tickMargin={10}
                />
                <YAxis 
                  stroke="#64748b" 
                  fontSize={12}
                  tickFormatter={(val) => `${val} u`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }}/>
                
                <Area 
                    type="stepAfter" 
                    dataKey="total" 
                    name="Stock Total DofiMall" 
                    stroke="#10b981" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorTotal)" 
                    isAnimationActive={false}
                />
                <Area 
                    type="stepAfter" 
                    dataKey="warehouse" 
                    name="Stock Disponible (Almacén)" 
                    stroke="#0ea5e9" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorWarehouse)" 
                    isAnimationActive={false}
                />

                {/* Renderizar Eventos Críticos (Compras) */}
                {analyticsData.chartData.map((d, index) => {
                   if (d.is_event) {
                      return (
                         <ReferenceDot 
                            key={`event-${index}`} 
                            x={d.time} 
                            y={d.total} 
                            r={6} 
                            fill="#f43f5e" 
                            stroke="#fff" 
                            strokeWidth={2} 
                         />
                      )
                   }
                   return null;
                })}
              </ComposedChart>
           </ResponsiveContainer>
        </div>
      )}
      
    </div>
  );
}
