import { useState, useEffect } from 'react';
import { Settings, Bell, Send, UserCheck, Shield, Tag, Plus, Trash2, Activity } from 'lucide-react';
import { fetchConfig, updateConfig, testNotification, fetchSettings, updateSettings, forceLogout, fetchCategories, createCategory, deleteCategory, checkSessionStatus, forceLogin } from '../utils/api';
import { toast } from 'react-hot-toast';

export default function ConfigPanel() {
  const [enabled, setEnabled] = useState(true);
  const [loading, setLoading] = useState(true);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [keepAliveEnabled, setKeepAliveEnabled] = useState(false);
  const [scanInterval, setScanInterval] = useState(10);
  const [sessionStatus, setSessionStatus] = useState({ active: false, checking: true });

  // Categorías
  const [categories, setCategories] = useState([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryColor, setNewCategoryColor] = useState('#38BDF8');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [configData, settingsData, cats, sessStat] = await Promise.all([
        fetchConfig(),
        fetchSettings(),
        fetchCategories(),
        checkSessionStatus()
      ]);
      setEnabled(configData.notifications_enabled);
      setEmail(settingsData.dofimall_email || '');
      setPassword(settingsData.dofimall_password || '');
      setKeepAliveEnabled(settingsData.keep_alive_enabled || false);
      setScanInterval(settingsData.scan_interval_seconds || 10);
      setCategories(cats);
      
      setSessionStatus({ active: sessStat.active, checking: false });
    } catch (e) {
      console.error(e);
      toast.error('Error cargando configuración o credenciales');
      setSessionStatus({ active: false, checking: false });
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async () => {
    const newVal = !enabled;
    setEnabled(newVal);
    try {
      await updateConfig({ notifications_enabled: newVal });
      toast.success(`Notificaciones ${newVal ? 'activadas' : 'desactivadas'}`);
    } catch (e) {
      setEnabled(!newVal); // revert
      toast.error('Error guardando configuración');
    }
  };

  const handleKeepAliveToggle = async () => {
    const newVal = !keepAliveEnabled;
    setKeepAliveEnabled(newVal);
    try {
      await updateSettings({ keep_alive_enabled: newVal });
      toast.success(`Anti-Desconexión ${newVal ? 'activado' : 'desactivado'}`);
    } catch (e) {
      setKeepAliveEnabled(!newVal); // revert
      toast.error('Error guardando configuración');
    }
  };

  const handleTest = async () => {
    toast.loading('Enviando notificación...', { id: 'test' });
    try {
      await testNotification();
      toast.success('Notificación de prueba enviada', { id: 'test' });
    } catch (e) {
      toast.error('Error enviando prueba: ' + e.message, { id: 'test' });
    }
  };

  const handleScanIntervalChange = async (e) => {
    let val = parseInt(e.target.value);
    if (isNaN(val) || val < 2) val = 2; // Min 2 secs
    setScanInterval(val);
  };
  
  const saveScanInterval = async () => {
    try {
      await updateSettings({ scan_interval_seconds: scanInterval });
      toast.success('Velocidad de Escaneo Guardada', { icon: '⏱️' });
    } catch(e) {
      toast.error('Error al guardar velocidad');
    }
  };

  const saveCredentials = async () => {
    const toastId = toast.loading('Guardando credenciales maestras...');
    try {
      await updateSettings({ dofimall_email: email, dofimall_password: password });
      toast.success('Credenciales guardadas y protegidas', { id: toastId });
    } catch (e) {
      toast.error('Fallo al guardar credenciales', { id: toastId });
    }
  };

  const handleLogout = async () => {
    const toastId = toast.loading('Destruyendo sesión actual de DofiMall...');
    try {
      const res = await forceLogout();
      if (res.success) {
        toast.success(res.message, { id: toastId });
        setSessionStatus({ active: false, checking: false });
      } else {
        toast.error(res.message, { id: toastId });
      }
    } catch (e) {
      toast.error('Fallo al destruir la sesión: ' + e.message, { id: toastId });
    }
  };

  const handleForceLoginTrigger = async () => {
    const toastId = toast.loading('Escanenado e Inyectando sesión en viewport oculto...');
    try {
       setSessionStatus({ ...sessionStatus, checking: true });
       const res = await forceLogin();
       if (res.success) {
           toast.success('Bot Inyectado: ' + res.message, { id: toastId });
       } else {
           toast.error(res.message || 'Fallo al iniciar sesión.', { id: toastId });
       }
       // Refrescar estado post-login
       const newStat = await checkSessionStatus();
       setSessionStatus({ active: newStat.active, checking: false });
    } catch (e) {
       toast.error('Error durante inyección: ' + e.message, { id: toastId });
       setSessionStatus({ active: false, checking: false });
    }
  };

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) return;
    const toastId = toast.loading('Añadiendo categoría...');
    try {
      const cat = await createCategory({ name: newCategoryName, color: newCategoryColor });
      setCategories([...categories, cat]);
      setNewCategoryName('');
      toast.success('Categoría añadida', { id: toastId });
    } catch (e) {
      toast.error(e.message, { id: toastId });
    }
  };

  const handleDeleteCategory = async (id) => {
    if (!window.confirm("¿Seguro que quieres borrar esta categoría? Eliminar categorías puede afectar el filtrado si tienen productos asociados, aunque por ahora la columna no está constreñida a CASCADE.")) return;
    try {
      await deleteCategory(id);
      setCategories(categories.filter(c => c.id !== id));
      toast.success('Categoría eliminada');
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  if (loading) {
    return (
      <div className="bg-surface-800 rounded-xl border border-surface-700/50 p-6 flex justify-center text-surface-400 p-10">
        Cargando configuración...
      </div>
    );
  }

  return (
    <div className="bg-surface-900 border border-surface-700 p-6 relative">
      <div className="absolute top-0 left-0 w-full h-1 bg-[linear-gradient(90deg,var(--color-brand-400)_0%,transparent_100%)] opacity-20"></div>
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-surface-700/50">
        <div className="flex items-center gap-3 text-brand-400">
          <Settings size={20} />
          <h2 className="font-bold text-white tracking-widest uppercase text-sm">Configuración del Sistema</h2>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        {/* Notificaciones globales */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 bg-surface-800 border border-surface-700 relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-1 h-full bg-brand-400 opacity-50"></div>
          <div className="flex items-start gap-4 mb-4 sm:mb-0">
            <div className={`p-3 border border-brand-400/30 ${enabled ? 'bg-brand-500/10 text-brand-400' : 'bg-surface-800 text-surface-500'}`}>
              <Bell size={18} />
            </div>
            <div>
              <h3 className="font-bold text-white text-[11px] tracking-widest uppercase">Notificaciones de Stock</h3>
              <p className="text-surface-400 text-[11px] mt-1 max-w-md font-mono">
                Activa o desactiva el envío automático de notificaciones a Telegram / Email cuando se detecta un stock mayor a cero (en tránsito o almacén).
              </p>
            </div>
          </div>
          
          <label className="relative inline-flex items-center cursor-pointer ml-auto sm:ml-0">
            <input type="checkbox" className="sr-only peer" checked={enabled} onChange={handleToggle} />
            <div className="w-14 h-7 bg-surface-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-brand-500"></div>
          </label>
        </div>

        {/* Prueba */}
        <div className="flex flex-col sm:flex-row items-center justify-between p-4 bg-surface-800 border border-surface-700 relative overflow-hidden">
             <div className="absolute top-0 left-0 w-1 h-full bg-surface-500 opacity-50"></div>
             <div>
              <h3 className="font-bold text-white text-[11px] tracking-widest uppercase ml-4">Prueba de Envío</h3>
              <p className="text-surface-400 text-[11px] mt-1 max-w-md font-mono ml-4">
                Asegúrate de que tus credenciales funcionen enviando un mensaje directo.
              </p>
            </div>
            <button
                onClick={handleTest}
                className="mt-4 sm:mt-0 flex items-center gap-2 px-6 py-2 border border-surface-600 hover:border-brand-400 bg-surface-900 hover:bg-brand-500/10 text-white font-bold tracking-widest uppercase text-[10px] transition-colors"
            >
                <Send size={14} />
                ENVIAR SEÑAL
            </button>
        </div>

        {/* Credenciales DofiMall */}
        <div className="flex flex-col p-5 bg-surface-800 border border-surface-700 relative overflow-hidden">
             <div className="absolute top-0 left-0 w-1 h-full bg-blue-500 opacity-50"></div>
             <div className="flex items-start gap-4 mb-4">
              <div className="p-3 border border-blue-500/30 bg-blue-500/10 text-blue-400 ml-2">
                <Shield size={18} />
              </div>
              <div>
                <h3 className="font-bold text-white text-[11px] tracking-widest uppercase">Credenciales Auto-Login (Sniper Bot)</h3>
                <p className="text-surface-400 text-[11px] mt-1 font-mono">
                  Introduce tu correo y contraseña maestros. El bot los usará, junto a un <b>bypasser OCR de IA</b>, para iniciar sesión por ti de forma invisible.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2 ml-2">
               <div>
                  <label className="block text-[10px] font-bold text-brand-400 mb-2 uppercase tracking-widest">Email de DofiMall</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="operativo@ejemplo.com"
                    className="w-full bg-surface-900 border border-brand-400/30 px-4 py-2 text-white placeholder:text-surface-600 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 transition-all font-mono text-xs"
                  />
               </div>
               <div>
                  <label className="block text-[10px] font-bold text-brand-400 mb-2 uppercase tracking-widest">Contraseña Maestra</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-surface-900 border border-brand-400/30 px-4 py-2 text-white placeholder:text-surface-600 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 transition-all font-mono text-xs"
                  />
               </div>
            </div>
            
            <div className="mt-5 flex justify-end gap-3 ml-2">
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-5 py-2 border border-red-500/30 text-red-500 hover:bg-red-500/10 font-bold text-[10px] uppercase tracking-widest transition-colors"
              >
                CERRAR SESIÓN
              </button>
              <button
                onClick={saveCredentials}
                className="flex items-center gap-2 px-5 py-2 bg-blue-500/10 border border-blue-500/50 hover:bg-blue-500/20 text-blue-400 font-bold text-[10px] uppercase tracking-widest transition-colors"
              >
                <UserCheck size={14} />
                GUARDAR Y ACTIVAR AUTO-SNIPE
              </button>
            </div>
        </div>

        {/* Keep-Alive */}
        <div className="flex flex-col p-4 bg-surface-800 border border-surface-700 relative overflow-hidden">
           <div className="absolute top-0 left-0 w-1 h-full bg-amber-500 opacity-50"></div>
           <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-2">
              <div className="flex items-start gap-4 mb-4 sm:mb-0">
                <div className={`relative p-3 border border-amber-500/30 ml-2 ${keepAliveEnabled ? 'bg-amber-500/10 text-amber-400' : 'bg-surface-800 text-surface-500'}`}>
                  <Shield size={18} />
                  {!sessionStatus.checking && (
                    <div className={`absolute -bottom-1 -right-1 w-3 h-3 border-2 border-surface-900 ${sessionStatus.active ? 'bg-emerald-500' : 'bg-red-500'}`} title={sessionStatus.active ? 'Sesión Viva' : 'Sesión Caducada'}></div>
                  )}
                </div>
                <div>
                  <h3 className="font-bold text-white text-[11px] tracking-widest uppercase flex items-center gap-2">
                     Keep-Alive (Anti-Cierre de Sesión)
                     {sessionStatus.checking ? (
                        <span className="text-[9px] bg-brand-500/20 border border-brand-500/50 text-brand-400 px-1.5 py-0.5 animate-pulse">COMPROBANDO</span>
                     ) : sessionStatus.active ? (
                        <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 border border-emerald-500/30">ACTIVA</span>
                     ) : (
                        <span className="text-[9px] bg-red-500/20 text-red-400 px-1.5 py-0.5 border border-red-500/30">EXPIRADA</span>
                     )}
                  </h3>
                  <p className="text-surface-400 text-[11px] mt-1 max-w-md font-mono">
                    Evita que DofiMall caduque tu sesión visitando el carrito en 2º plano silenciosamente cada 5 minutos.
                  </p>
                </div>
              </div>
              
              <label className="relative inline-flex items-center cursor-pointer ml-auto sm:ml-0">
                <input type="checkbox" className="sr-only peer" checked={keepAliveEnabled} onChange={handleKeepAliveToggle} />
                <div className="w-14 h-7 bg-surface-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-amber-500"></div>
              </label>
           </div>
           
           <div className="flex justify-end mt-2">
               <button 
                  onClick={handleForceLoginTrigger}
                  disabled={sessionStatus.checking}
                  className="px-4 py-2 border border-surface-600 bg-surface-900 hover:border-amber-400 text-[10px] tracking-widest uppercase font-bold text-white transition-colors disabled:opacity-50"
               >
                  FORZAR INYECCIÓN AHORA
               </button>
           </div>
        </div>

        {/* Frecuencia de Escaneo */}
        <div className="flex flex-col p-4 bg-surface-800 border border-surface-700 relative overflow-hidden">
           <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500 opacity-50"></div>
           <div className="flex flex-col mb-2 ml-2">
              <div className="flex items-start gap-4 mb-4">
                <div className="p-3 border border-cyan-500/30 bg-cyan-500/10 text-cyan-400">
                  <Activity size={18} />
                </div>
                <div>
                  <h3 className="font-bold text-white text-[11px] tracking-widest uppercase flex items-center gap-2">
                     Frecuencia de Escaneo
                  </h3>
                  <p className="text-surface-400 text-[11px] mt-1 max-w-md font-mono">
                    Controla cuántos segundos espera cada hilo independiente entre peticiones.
                  </p>
                </div>
              </div>
           </div>
           
           <div className="flex items-center gap-4 ml-14">
              <input 
                type="range" 
                min="3" 
                max="60" 
                value={scanInterval} 
                onChange={handleScanIntervalChange} 
                className="w-full h-1 bg-surface-700 appearance-none cursor-pointer accent-cyan-500"
              />
              <span className="text-cyan-400 font-mono font-bold w-16 text-right whitespace-nowrap">{scanInterval} seg</span>
              <button
                onClick={saveScanInterval}
                className="ml-2 px-4 py-2 border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 font-bold text-[10px] tracking-widest uppercase transition-colors whitespace-nowrap"
              >
                 APLICAR
              </button>
           </div>
        </div>

        {/* Categories */}
        <div className="flex flex-col p-5 bg-surface-800 border border-surface-700 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-purple-500 opacity-50"></div>
          <div className="flex items-start gap-4 mb-4 border-b border-surface-700/50 pb-4 ml-2">
            <div className="p-3 border border-purple-500/30 bg-purple-500/10 text-purple-400">
              <Tag size={18} />
            </div>
            <div className="flex-1">
              <div className="flex justify-between items-start">
                  <div>
                      <h3 className="font-bold text-white text-[11px] tracking-widest uppercase">Categorías de Analíticas</h3>
                      <p className="text-surface-400 text-[11px] font-mono mt-1 max-w-lg">
                        Define las familias logísticas a las que pertenecen tus enlaces (ej: "Solares").
                      </p>
                  </div>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row items-end gap-3 mb-5 mt-2 bg-surface-900/50 p-3 border border-surface-700 ml-2">
             <div className="flex-1 w-full">
                <label className="block text-[10px] font-bold text-brand-400 mb-1 uppercase tracking-widest">NUEVA CATEGORÍA</label>
                <input
                    type="text"
                    value={newCategoryName}
                    onChange={(e) => setNewCategoryName(e.target.value)}
                    placeholder="Baterías..."
                    className="w-full bg-surface-900 border border-brand-400/30 px-4 py-2 text-white placeholder:text-surface-600 focus:border-brand-400 focus:outline-none focus:ring-1 focus:ring-brand-400 transition-all font-mono text-xs"
                />
             </div>
             <div>
                <label className="block text-[10px] font-bold text-brand-400 mb-1 uppercase tracking-widest">COLOR_HEX</label>
                <div className="h-[34px] px-2 bg-surface-900 border border-brand-400/30 flex items-center justify-center cursor-pointer">
                    <input
                        type="color"
                        value={newCategoryColor}
                        onChange={(e) => setNewCategoryColor(e.target.value)}
                        className="w-6 h-6 shrink-0 cursor-pointer border-0 p-0 bg-transparent"
                    />
                </div>
             </div>
             <button
                 onClick={handleAddCategory}
                 disabled={!newCategoryName.trim()}
                 className="flex items-center justify-center gap-2 h-[34px] px-4 border border-brand-400/30 bg-brand-500/10 hover:bg-brand-500/20 disabled:opacity-50 disabled:cursor-not-allowed text-brand-400 font-bold tracking-widest text-[10px] uppercase transition-colors whitespace-nowrap"
             >
                 <Plus size={14} /> <span className="hidden sm:inline">AÑADIR_CAT</span>
             </button>
          </div>

          <div className="ml-2">
          {categories.length === 0 ? (
            <div className="text-center py-6 text-brand-400/30 text-xs tracking-widest uppercase border-dashed border border-surface-700">
                SIN DEFINICIÓN DE CATEGORÍAS
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {categories.map((cat) => (
                <div key={cat.id} className="flex items-center justify-between p-2 bg-surface-900 border border-surface-700 hover:border-brand-400 transition-colors group">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3" style={{ backgroundColor: cat.color }}></div>
                        <span className="text-[11px] font-bold text-surface-200 tracking-wider uppercase">{cat.name}</span>
                    </div>
                    <button 
                        onClick={() => handleDeleteCategory(cat.id)}
                        className="text-surface-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all p-1"
                        title="Eliminar Categoría"
                    >
                        <Trash2 size={12} />
                    </button>
                </div>
              ))}
            </div>
          )}
          </div>
        </div>

      </div>
    </div>
  );
}
