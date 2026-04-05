import { useState, useEffect } from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, 
  BarElement, ArcElement, Title, Tooltip as ChartTooltip, Legend, Filler
} from 'chart.js';
import { Line, Doughnut, Bar } from 'react-chartjs-2';
import { Activity, Target, TrendingDown, TrendingUp, AlertTriangle, Package, Warehouse, Truck, RefreshCw } from 'lucide-react';
import { 
  fetchIntelligenceDashboard, 
  fetchProductHistory, 
  fetchDemandRanking, 
  fetchDistribution,
  fetchProducts
} from '../utils/api';

// Register Chart.js models
ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, 
  BarElement, ArcElement, Title, ChartTooltip, Legend, Filler
);

// CSS Helpers
const glass = "bg-surface-800/40 backdrop-blur-md border border-surface-700/50 rounded-xl p-5 shadow-lg relative overflow-hidden";

export default function IntelligenceDashboard() {
  const [kpis, setKpis] = useState(null);
  const [ranking, setRanking] = useState([]);
  const [products, setProducts] = useState([]);
  const [distribution, setDistribution] = useState(null);
  const [history, setHistory] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initial Load Main Data
  useEffect(() => {
    async function loadDash() {
      try {
        const [dashRes, rankRes, distRes, prodRes] = await Promise.all([
          fetchIntelligenceDashboard(),
          fetchDemandRanking(),
          fetchDistribution(),
          fetchProducts()
        ]);
        setKpis(dashRes);
        setRanking(rankRes);
        setDistribution(distRes);
        setProducts(prodRes);
        
        if (prodRes && prodRes.length > 0 && !selectedProduct) {
           setSelectedProduct(prodRes[0].id);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadDash();
    const interval = setInterval(loadDash, 60000); // 1 min sync
    return () => clearInterval(interval);
  }, []);

  // Load TimeSeries When selected product changes
  useEffect(() => {
    if (!selectedProduct) return;
    async function loadTimeSeries() {
       try {
          const hist = await fetchProductHistory(selectedProduct);
          setHistory(hist);
       } catch(e) {
          console.error(e);
       }
    }
    loadTimeSeries();
    const interval = setInterval(loadTimeSeries, 60000);
    return () => clearInterval(interval);
  }, [selectedProduct]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
         <RefreshCw className="animate-spin text-brand-500" size={32} />
      </div>
    );
  }

  // --- CHART CONFIGURATIONS ---
  const lineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    color: '#94a3b8',
    scales: {
      x: { grid: { color: '#334155', tickColor: 'transparent' }, ticks: { color: '#94a3b8' } },
      y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } }
    },
    plugins: {
      legend: { position: 'top', labels: { color: '#f8fafc' } }
    },
    elements: { line: { tension: 0.4 } }
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { stacked: true, grid: { display: false } },
      y: { stacked: true, grid: { color: '#1e293b' } }
    },
    plugins: { legend: { position: 'bottom', labels: { color: '#f8fafc' } } }
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '75%',
    plugins: { legend: { position: 'bottom', labels: { color: '#f8fafc' } } }
  };

  return (
    <div className="space-y-6">
       
       <div className="flex items-center gap-3 mb-2">
         <Activity size={24} className="text-brand-500" />
         <h2 className="text-xl font-bold text-white tracking-tight">Market Intelligence</h2>
       </div>

       {/* KPIs (8 Cards Grid) */}
       <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
         <div className={glass}>
            <div className="text-xs text-surface-400 font-semibold uppercase tracking-wider mb-1">Demand Score</div>
            <div className="text-3xl font-bold text-white">{kpis?.global_demand_score}%</div>
            <div className="absolute -bottom-4 -right-4 opacity-5"><Target size={64}/></div>
         </div>
         <div className={glass}>
            <div className="text-xs text-surface-400 font-semibold uppercase tracking-wider mb-1">Velocidad Flujo</div>
            <div className="text-3xl font-bold text-emerald-400">{kpis?.total_velocity}U</div>
            <div className="text-[10px] text-surface-500 mt-1">UDS MOVIMIENTOS/H</div>
         </div>
         <div className={glass}>
            <div className="text-xs text-surface-400 font-semibold uppercase tracking-wider mb-1">Stock Total</div>
            <div className="text-3xl font-bold text-white flex items-baseline gap-2">
               {kpis?.total_warehouse + kpis?.total_transit}
               <span className="text-xs text-surface-400 font-mono">({kpis?.total_warehouse}W / {kpis?.total_transit}T)</span>
            </div>
         </div>
         <div className={glass}>
            <div className="text-xs text-surface-400 font-semibold uppercase tracking-wider mb-1">Tasa Disponibilidad</div>
            <div className="text-3xl font-bold text-brand-400">{kpis?.availability_rate}%</div>
         </div>

         <div className={glass}>
            <div className="text-xs text-surface-400 font-semibold uppercase tracking-wider mb-1">Items Bearish</div>
            <div className="text-3xl font-bold text-red-400 flex items-center gap-2">
               {kpis?.bearish_products} <TrendingDown size={20} />
            </div>
         </div>
         <div className={glass}>
            <div className="text-xs text-surface-400 font-semibold uppercase tracking-wider mb-1">Ciclo Cero (&gt;95%)</div>
            <div className="text-3xl font-bold text-orange-400 flex items-center gap-2">
               {kpis?.zero_cycle_count} <AlertTriangle size={20} />
            </div>
         </div>
         <div className={`${glass} col-span-2`}>
            <div className="text-xs text-surface-400 font-semibold uppercase tracking-wider mb-1">Agotamiento Crítico (Riesgo #1)</div>
            <div className="text-xl font-bold text-white truncate text-ellipsis">{kpis?.fastest_depletion}</div>
         </div>
       </div>

       <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
         {/* Main TimeSeries Graph */}
         <div className={`lg:col-span-2 ${glass} h-[450px] flex flex-col`}>
             <div className="flex justify-between items-center mb-4">
                 <h3 className="font-semibold text-white">Curva de Flujo (12 Hrs)</h3>
                 <select 
                    value={selectedProduct || ''} 
                    onChange={e => setSelectedProduct(parseInt(e.target.value))}
                    className="bg-surface-900 border border-surface-700 text-xs text-surface-200 rounded px-2 py-1 max-w-[250px]"
                 >
                    {products.map((p) => (
                       <option key={p.id} value={p.id}>
                         {p.name !== 'Sin nombre' ? p.name.substring(0,40) : p.url.split('/').pop().substring(0,20)}
                       </option>
                    ))}
                 </select>
             </div>
             
             <div className="flex-1 w-full relative">
                {history && history.labels && (
                    <Line 
                      options={lineOptions}
                      data={{
                         labels: history.labels,
                         datasets: [
                            {
                               label: 'Warehouse (Almacén)',
                               data: history.datasets.warehouse,
                               borderColor: '#10b981',
                               backgroundColor: 'rgba(16, 185, 129, 0.1)',
                               fill: true,
                            },
                            {
                               label: 'Transit (Gap)',
                               data: history.datasets.transit,
                               borderColor: '#0ea5e9',
                               backgroundColor: 'rgba(14, 165, 233, 0.1)',
                               fill: true,
                            }
                         ]
                      }} 
                    />
                )}
             </div>
         </div>

         {/* Right Column: Doughnut and Ranking */}
         <div className="flex flex-col gap-6">
            <div className={`${glass} h-[213px]`}>
               <h3 className="font-semibold text-white mb-2 text-sm text-center">Distribución Global</h3>
               <div className="relative h-[130px] w-full">
                  {distribution && distribution.labels && (
                     <Doughnut 
                        options={doughnutOptions}
                        data={{
                           labels: distribution.labels,
                           datasets: [{
                              data: distribution.datasets.warehouse.map((w, i) => w + distribution.datasets.transit[i]),
                              backgroundColor: distribution.colors,
                              borderWidth: 0,
                           }]
                        }}
                     />
                  )}
               </div>
            </div>

            <div className={`${glass} flex-1 overflow-auto custom-scrollbar p-0`}>
               <div className="sticky top-0 bg-surface-800/90 backdrop-blur px-4 py-3 border-b border-surface-700 font-semibold text-sm">
                  Trending Ranking
               </div>
               {ranking.length === 0 ? (
                  <div className="px-4 py-6 text-center text-xs text-surface-400">
                    Recopilando históricos...<br/>El ranking aparecerá pronto.
                  </div>
               ) : (
                  <div className="divide-y divide-surface-700/50">
                     {ranking.map((item, idx) => (
                        <div key={item.id} className="px-4 py-3 flex items-center justify-between hover:bg-surface-700/30 transition-colors cursor-pointer" onClick={() => setSelectedProduct(item.id)}>
                           <div className="flex items-center gap-3 overflow-hidden">
                              <span className="text-surface-500 font-mono text-xs w-4">{idx + 1}</span>
                              <span className="truncate text-sm text-surface-200">{item.name}</span>
                           </div>
                           <div className="flex items-center gap-2">
                              {item.trend === 'bullish' && <TrendingUp size={14} className="text-emerald-400" />}
                              {item.trend === 'bearish' && <TrendingDown size={14} className="text-red-400" />}
                              {item.trend === 'neutral' && <span className="w-2 h-2 rounded-full bg-surface-500"></span>}
                              <span className="text-brand-400 font-bold font-mono text-sm">{item.score}</span>
                           </div>
                        </div>
                     ))}
                  </div>
               )}
            </div>
         </div>
       </div>

       {/* Stacked Category Breakdown */}
       <div className={`${glass} h-[300px]`}>
          <h3 className="font-semibold text-white mb-4">Stock de Categorías por Tipo (Almacén vs Tránsito)</h3>
          <div className="w-full h-[200px]">
             {distribution && distribution.labels && (
                <Bar 
                   options={barOptions}
                   data={{
                      labels: distribution.labels,
                      datasets: [
                         {
                            label: 'Warehouse (Físico)',
                            data: distribution.datasets.warehouse,
                            backgroundColor: '#10b981',
                         },
                         {
                            label: 'Transit (Estimado)',
                            data: distribution.datasets.transit,
                            backgroundColor: '#0ea5e9',
                         }
                      ]
                   }}
                />
             )}
          </div>
       </div>

    </div>
  );
}
