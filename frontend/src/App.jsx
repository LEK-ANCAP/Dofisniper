import { useState, useEffect, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import StatsBar from './components/StatsBar';
import ProductList from './components/ProductList';
import AddProductForm from './components/AddProductForm';
import LogsPanel from './components/LogsPanel';
import ConfigPanel from './components/ConfigPanel';
import IntelligenceDashboard from './components/IntelligenceDashboard';
import {
  fetchDashboard, fetchProducts, fetchLogs,
  addProduct, addProductsBulk, deleteProduct,
  toggleProduct, manualCheckout, clearLogs,
  fetchMe, fetchCategories, checkSessionFastStatus, forceLogin
} from './utils/api';
import { Crosshair, RefreshCw, Activity, Settings, BarChart2, LogOut, ShieldAlert, Ghost, Terminal } from 'lucide-react';
import LoginPage from './pages/LoginPage';
import { playTacticalClick } from './utils/tacticalAudio';

export default function App() {
  const [stats, setStats] = useState(null);
  const [products, setProducts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);
  const [autoLoginTimer, setAutoLoginTimer] = useState(10);
  const [isInjecting, setIsInjecting] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [tab, setTab] = useState('products');
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('sniper_token'));
  const [sessionPaused, setSessionPaused] = useState(false); // Pausa auto-relogin cuando el usuario cierra sesión DofiMall manualmente

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

  // Listen for forced logout from API (401) or manual logout
  useEffect(() => {
    const onForceLogout = () => {
      setIsAuthenticated(false);
    };
    window.addEventListener('sniper-logout', onForceLogout);
    return () => window.removeEventListener('sniper-logout', onForceLogout);
  }, []);
  
  // Listen for DofiMall session pause/resume events from ConfigPanel
  useEffect(() => {
    const onPause = () => setSessionPaused(true);
    const onResume = () => setSessionPaused(false);
    window.addEventListener('dofimall-session-paused', onPause);
    window.addEventListener('dofimall-session-resumed', onResume);
    return () => {
      window.removeEventListener('dofimall-session-paused', onPause);
      window.removeEventListener('dofimall-session-resumed', onResume);
    };
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
      const interval = setInterval(loadData, 10000); 
      return () => clearInterval(interval);
    }
  }, [loadData, isAuthenticated]);

  const handleAutoLogin = useCallback(async () => {
     setIsInjecting(true);
     try {
         const res = await forceLogin();
         if (res && res.success) {
            toast.success("Infiltración Automática exitosa", { icon: '🕵️' });
            setSessionActive(true);
         } else {
            setAutoLoginTimer(10);
         }
     } catch (e) {
         setAutoLoginTimer(10);
     } finally {
         setIsInjecting(false);
     }
  }, []);

  useEffect(() => {
      if (isAuthenticated && !sessionActive && !checking && !isInjecting && !sessionPaused) {
          const timer = setInterval(() => {
              setAutoLoginTimer(prev => {
                  if (prev <= 1) {
                      handleAutoLogin();
                      return 0;
                  }
                  return prev - 1;
              });
          }, 1000);
          return () => clearInterval(timer);
      }
      if (sessionActive) {
          setAutoLoginTimer(10);
      }
  }, [isAuthenticated, sessionActive, isInjecting, handleAutoLogin, checking, sessionPaused]);

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
    // Reemplazado por iteradores concurrentes en backend
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

      {/* Header HUD */}
      <header className="border-b border-brand-400/30 bg-surface-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-500/10 border border-brand-400 flex items-center justify-center relative group overflow-hidden">
              <div className="absolute inset-0 bg-[linear-gradient(rgba(0,255,65,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,65,0.1)_1px,transparent_1px)] bg-[size:5px_5px]"></div>
              <Crosshair size={22} className="text-brand-400 relative z-10 animate-[radar_4s_linear_infinite]" />
            </div>
            <div>
              <h1 className="text-lg  font-bold tracking-wider text-brand-400" style={{ textShadow: '0 0 10px rgba(0,255,65,0.4)' }}>
                DOFIMALL_SNIPER
              </h1>
              <p className="text-[9px] text-brand-400/60 uppercase tracking-[0.3em] ">Control Táctico Central</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            
            {/* Session Indicator Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 border border-surface-700 bg-surface-800  text-[10px] tracking-wider uppercase">
              {sessionActive ? (
                <>
                  <Ghost size={12} className="text-brand-400 animate-pulse" />
                  <span className="hidden sm:inline text-brand-400 font-bold">[ OPERATIVO_INFILTRADO ]</span>
                </>
              ) : (
                <>
                  <ShieldAlert size={12} className={sessionPaused ? "text-amber-500" : "text-red-500"} />
                  <span className={`hidden sm:inline font-bold ${sessionPaused ? 'text-amber-500' : 'text-red-500'}`}>
                     {sessionPaused ? '[ SESIÓN_PAUSADA ]' : isInjecting ? '[ INJECTING... ]' : `[ SIGNAL_LOST: ${autoLoginTimer}s ]`}
                  </span>
                </>
              )}
            </div>
            <div className="h-6 w-px bg-brand-500/20 hidden sm:block" />

            <button
               onMouseEnter={() => playTacticalClick(0.01)}
               onClick={() => { playTacticalClick(); handleLogout(); }}
               className="flex items-center gap-2 px-3 py-1.5 border border-transparent hover:border-red-500/50 bg-surface-900 hover:bg-red-500/10
                          text-surface-500 hover:text-red-500 text-[10px]  tracking-wider uppercase transition-all"
               title="Cerrar Misión"
            >
              <LogOut size={12} />
              <span className="hidden sm:inline">ABORTAR_MISIÓN</span>
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
          <div className="flex gap-1 overflow-x-auto bg-surface-900 border border-brand-400/30 p-1 w-full sm:w-fit filter drop-shadow-[0_0_10px_rgba(0,255,65,0.05)]">
            {[
              { key: 'products', label: 'F1: BLANCOS', icon: Crosshair },
            { key: 'analytics', label: 'F2: INTEL_SYS', icon: BarChart2 },
            { key: 'logs', label: 'F3: TERMINAL', icon: Terminal },
            { key: 'config', label: 'F4: SYSTEM_OP', icon: Settings },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onMouseEnter={() => playTacticalClick(0.01)}
              onClick={() => { playTacticalClick(); setTab(key); }}
              className={`flex items-center gap-2 px-4 py-2 text-[10px] uppercase  tracking-wider font-bold transition-all border
                ${tab === key
                  ? 'bg-brand-400 text-surface-900 border-brand-400 shadow-inner shadow-transparent'
                  : 'bg-surface-900 text-brand-400/50 border-transparent hover:text-brand-400 hover:bg-brand-500/10 hover:border-brand-400/20'
                }`}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
          </div>
          
          <button 
             onMouseEnter={() => playTacticalClick(0.01)}
             onClick={() => { playTacticalClick(); setShowAddForm(!showAddForm); }}
             className={`flex items-center gap-2 px-4 py-2  font-bold text-[10px] uppercase tracking-wider transition-all border ${showAddForm ? 'bg-brand-400 text-surface-900 border-brand-400' : 'bg-surface-900 text-blue-400 border-blue-500/30 hover:bg-blue-500/10 shadow-[0_0_10px_rgba(59,130,246,0.1)]'}`}
          >
             <Crosshair size={12} />
             {showAddForm ? 'CANCEL_INPUT' : 'ASIGNAR_NUEVO_BLANCO'}
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
