import { useState, useEffect, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import StatsBar from './components/StatsBar';
import ProductList from './components/ProductList';
import AddProductForm from './components/AddProductForm';
import LogsPanel from './components/LogsPanel';
import CountdownTimer from './components/CountdownTimer';
import ConfigPanel from './components/ConfigPanel';
import AnalyticsPanel from './components/AnalyticsPanel';
import {
  fetchDashboard, fetchProducts, fetchLogs,
  addProduct, addProductsBulk, deleteProduct,
  toggleProduct, triggerCheckNow, manualCheckout, clearLogs,
  fetchMe
} from './utils/api';
import { Crosshair, RefreshCw, Activity, Settings, BarChart2, LogOut } from 'lucide-react';
import LoginPage from './pages/LoginPage';

export default function App() {
  const [stats, setStats] = useState(null);
  const [products, setProducts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
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
      const [s, p, l] = await Promise.all([
        fetchDashboard(), fetchProducts(), fetchLogs(30)
      ]);
      setStats(s);
      setProducts(p);
      setLogs(l);
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
    if (isAuthenticated) {
      loadData();
      const interval = setInterval(loadData, 10000); 
      return () => clearInterval(interval);
    }
  }, [loadData, isAuthenticated]);

  const handleAddProduct = async (url, name) => {
    try {
      await addProduct({ url, name: name || undefined });
      toast.success('Producto añadido');
      await loadData();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const handleAddBulk = async (items) => {
    try {
      const productsToAdd = items.map(item => {
        if (typeof item === 'string') return { url: item.trim() };
        return { url: item.url.trim(), name: item.name };
      });
      await addProductsBulk(productsToAdd);
      toast.success(`${productsToAdd.length} productos añadidos`);
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
        <AddProductForm onAdd={handleAddProduct} onAddBulk={handleAddBulk} />

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
          <AnalyticsPanel />
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
