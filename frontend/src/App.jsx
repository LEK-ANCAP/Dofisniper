import { useState, useEffect, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import StatsBar from './components/StatsBar';
import ProductList from './components/ProductList';
import AddProductForm from './components/AddProductForm';
import LogsPanel from './components/LogsPanel';
import CountdownTimer from './components/CountdownTimer';
import ConfigPanel from './components/ConfigPanel';
import IntelligenceDashboard from './components/IntelligenceDashboard';
import {
  fetchDashboard, fetchProducts, fetchLogs,
  addProduct, addProductsBulk, deleteProduct,
  toggleProduct, triggerCheckNow, manualCheckout, clearLogs,
  fetchMe, fetchCategories, checkSessionFastStatus
} from './utils/api';
import { Crosshair, RefreshCw, Activity, Settings, BarChart2, LogOut, ShieldAlert, ShieldCheck } from 'lucide-react';
import LoginPage from './pages/LoginPage';

export default function App() {
  const [stats, setStats] = useState(null);
  const [products, setProducts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [tab, setTab] = useState('products');
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('sniper_token'));

  const handleLogout = useCallback(() => {
    localStorage.removeItem('sniper_token');
    setIsAuthenticated(false);
    toast.success('Misión finalizada. Sesión cerrada.');
  }, []);

  const loadData = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const [s, p, l, c, sess] = await Promise.all([
        fetchDashboard(), fetchProducts(), fetchLogs(30), fetchCategories(), checkSessionFastStatus()
      ]);
      setStats(s);
      setProducts(p);
      setLogs(l);
      setCategories(c);
      setSessionActive(sess?.active || false);
    } catch (e) {
      console.error('Error cargando datos:', e);
      if (e.message.includes('401') || e.message.includes('validar la sesión')) {
        handleLogout();
      }
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, handleLogout]);

    useEffect(() => {
    window.addEventListener('refresh-products', loadData);
    return () => window.removeEventListener('refresh-products', loadData);
  }, [loadData]);
  
  useEffect(() => {
    if (isAuthenticated) {
      loadData();
      const interval = setInterval(loadData, 10000); 
      return () => clearInterval(interval);
    }
  }, [loadData, isAuthenticated]);

  const handleAddProduct = async (url, name, category_id) => {
    try {
      await addProduct({ url, name: name || undefined, category_id });
      toast.success('Producto añadido');
      setShowAddForm(false);
      await loadData();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const handleAddBulk = async (items) => {
    try {
      const productsToAdd = items.map(item => {
        if (typeof item === 'string') return { url: item.trim(), category_id: items.category_id }; 
        return { url: item.url.trim(), name: item.name, category_id: items.category_id };
      });
      await addProductsBulk(productsToAdd);
      toast.success(`${productsToAdd.length} productos añadidos`);
      setShowAddForm(false);
      await loadData();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteProduct(id);
      toast.success('Producto eliminado');
      await loadData();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const handleToggle = async (id, options = {}) => {
    try {
      if (!options.preventBackend) {
        await toggleProduct(id);
      }
      await loadData();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const handleCheckout = async (id) => {
    toast.loading('Iniciando checkout (Playwright en segundo plano)...', { id: 'checkout' });
    try {
      const res = await manualCheckout(id);
      if (res.success) {
        toast.success(res.message || 'Checkuot completado!', { id: 'checkout' });
      } else {
        toast.error(res.message || 'Fallo el checkout', { id: 'checkout' });
      }
      await loadData();
    } catch (e) {
      toast.error(e.message, { id: 'checkout' });
    }
  };

  const handleCheckNow = async () => {
    setChecking(true);
    try {
      await triggerCheckNow();
      toast.success('Comprobación manual iniciada');
      setTimeout(loadData, 3000);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setTimeout(() => setChecking(false), 5000);
    }
  };

  if (!isAuthenticated) {
    return (
      <>
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155' },
          }}
        />
        <LoginPage onLogin={() => setIsAuthenticated(true)} />
      </>
    );
  }

  return (
    <div className="min-h-screen">
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155' },
        }}
      />

      {/* Header */}
      <header className="border-b border-surface-700/50 bg-surface-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
              <Crosshair size={22} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white">
                DofiMall Sniper
              </h1>
              <p className="text-xs text-surface-200/50 uppercase tracking-widest font-mono">Control Táctico de Suministros</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            
            {/* Session Indicator Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-surface-700 bg-surface-800" title={sessionActive ? "Sesión de bot sincronizada y conectada a DofiMall." : "Sesión de bot desconectada o expirada. (Ve a Configuración -> Forzar Inyección)"}>
              {sessionActive ? (
                <>
                  <ShieldCheck size={14} className="text-emerald-500" />
                  <span className="hidden sm:inline text-xs font-semibold text-emerald-400 uppercase tracking-widest">Activo</span>
                </>
              ) : (
                <>
                  <ShieldAlert size={14} className="text-red-500" />
                  <span className="hidden sm:inline text-xs font-semibold text-red-500 uppercase tracking-widest">Expirada</span>
                </>
              )}
            </div>
            
            <div className="h-6 w-px bg-white/10 hidden sm:block" />

            <CountdownTimer
              nextCheck={stats?.next_check}
              interval={stats?.check_interval}
              isRunning={stats?.scheduler_running}
            />

            <button
              onClick={handleCheckNow}
              disabled={checking}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500
                         text-white text-sm font-medium transition-all disabled:opacity-50"
            >
              <RefreshCw size={14} className={checking ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">{checking ? 'Sincronizando...' : 'Check de Stock'}</span>
            </button>

            <div className="h-6 w-px bg-white/10" />

            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-red-500/20
                         text-surface-200 hover:text-red-400 text-xs font-medium transition-all border border-transparent hover:border-red-500/30"
              title="Cerrar Misión"
            >
              <LogOut size={14} />
              <span className="hidden sm:inline">Finalizar Misión</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        <StatsBar stats={stats} loading={loading} />
        
        {showAddForm && (
           <AddProductForm onAdd={handleAddProduct} onAddBulk={handleAddBulk} categories={categories} />
        )}

        <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
          <div className="flex gap-1 overflow-x-auto bg-surface-800/50 rounded-lg p-1 w-full sm:w-fit">
            {[
              { key: 'products', label: 'Productos', icon: Crosshair },
            { key: 'analytics', label: 'Analíticas', icon: BarChart2 },
            { key: 'logs', label: 'Actividad', icon: Activity },
            { key: 'config', label: 'Configuración', icon: Settings },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all
                ${tab === key
                  ? 'bg-surface-700 text-white shadow-sm ring-1 ring-white/5'
                  : 'text-surface-200/60 hover:text-white'
                }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
          </div>
          
          <button 
             onClick={() => setShowAddForm(!showAddForm)}
             className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all whitespace-nowrap ${showAddForm ? 'bg-surface-700 text-white' : 'bg-brand-500/10 text-brand-400 hover:bg-brand-500/20 shadow-sm border border-brand-500/20'}`}
          >
             <Crosshair size={14} />
             {showAddForm ? 'Ocultar Formulario' : 'Añadir Producto(s)'}
          </button>
        </div>

        {tab === 'products' ? (
          <ProductList
            products={products}
            loading={loading}
            onDelete={handleDelete}
            onToggle={handleToggle}
            onCheckout={handleCheckout}
            onAddBulk={handleAddBulk}
          />
        ) : tab === 'analytics' ? (
          <IntelligenceDashboard />
        ) : tab === 'logs' ? (
          <LogsPanel logs={logs} onRefresh={loadData} onClear={async () => {
            try {
              await clearLogs();
              toast.success('Historial limpiado');
              await loadData();
            } catch(e) {
              toast.error('Error al limpiar logs');
            }
          }} />
        ) : tab === 'config' ? (
          <ConfigPanel />
        ) : null}
      </main>
    </div>
  );
}
