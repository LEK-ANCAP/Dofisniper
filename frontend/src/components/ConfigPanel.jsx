import { useState, useEffect } from 'react';
import { Settings, Bell, Send, UserCheck, Shield } from 'lucide-react';
import { fetchConfig, updateConfig, testNotification, fetchSettings, updateSettings, forceLogout } from '../utils/api';
import { toast } from 'react-hot-toast';

export default function ConfigPanel() {
  const [enabled, setEnabled] = useState(true);
  const [loading, setLoading] = useState(true);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [keepAliveEnabled, setKeepAliveEnabled] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [configData, settingsData] = await Promise.all([
        fetchConfig(),
        fetchSettings()
      ]);
      setEnabled(configData.notifications_enabled);
      setEmail(settingsData.dofimall_email || '');
      setPassword(settingsData.dofimall_password || '');
      setKeepAliveEnabled(settingsData.keep_alive_enabled || false);
    } catch (e) {
      console.error(e);
      toast.error('Error cargando configuración o credenciales');
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
      } else {
        toast.error(res.message, { id: toastId });
      }
    } catch (e) {
      toast.error('Fallo al destruir la sesión: ' + e.message, { id: toastId });
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
    <div className="bg-surface-800 rounded-xl border border-surface-700/50 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3 text-brand-400">
          <Settings size={20} />
          <h2 className="font-semibold text-white tracking-wide">Configuración del Sistema</h2>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        {/* Notificaciones globales */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 bg-surface-900 rounded-lg border border-surface-700">
          <div className="flex items-start gap-4 mb-4 sm:mb-0">
            <div className={`p-3 rounded-full ${enabled ? 'bg-brand-500/20 text-brand-400' : 'bg-surface-700 text-surface-400'}`}>
              <Bell size={24} />
            </div>
            <div>
              <h3 className="font-medium text-white text-md">Notificaciones de Stock</h3>
              <p className="text-surface-400 text-sm mt-1 max-w-md">
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
        <div className="flex flex-col sm:flex-row items-center justify-between p-4 bg-surface-900 rounded-lg border border-surface-700">
             <div>
              <h3 className="font-medium text-white text-md">Prueba de Envío</h3>
              <p className="text-surface-400 text-sm mt-1 max-w-md">
                Asegúrate de que tus credenciales funcionen enviando un mensaje directo.
              </p>
            </div>
            <button
                onClick={handleTest}
                className="mt-4 sm:mt-0 flex items-center gap-2 px-6 py-2 rounded-lg bg-surface-700 hover:bg-surface-600 text-white font-medium transition-colors"
            >
                <Send size={16} />
                Mandar notificación de prueba
            </button>
        </div>

        {/* Credenciales DofiMall */}
        <div className="flex flex-col p-5 bg-surface-900 rounded-lg border border-surface-700">
             <div className="flex items-start gap-4 mb-4">
              <div className="p-3 rounded-full bg-indigo-500/20 text-indigo-400">
                <Shield size={24} />
              </div>
              <div>
                <h3 className="font-medium text-white text-md">Credenciales Auto-Login (Sniper Bot)</h3>
                <p className="text-surface-400 text-sm mt-1">
                  Introduce tu correo y contraseña maestros. El bot los usará, junto a un <b>bypasser OCR de IA</b>, para iniciar sesión por ti si detecta que DofiMall intenta bloquearlo con Captchas mientras caza stock de noche.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
               <div>
                  <label className="block text-xs font-semibold text-surface-400 mb-2 uppercase tracking-wide">Email de DofiMall</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="delavegadeus@gmail.com"
                    className="w-full bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-white placeholder:text-surface-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all font-mono text-sm"
                  />
               </div>
               <div>
                  <label className="block text-xs font-semibold text-surface-400 mb-2 uppercase tracking-wide">Contraseña Maestra</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-surface-800 border border-surface-700 rounded-lg px-4 py-2.5 text-white placeholder:text-surface-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all font-mono text-sm"
                  />
               </div>
            </div>
            
            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg border border-red-500/30 text-red-500 hover:bg-red-500/10 font-semibold transition-colors shadow-sm"
              >
                Cerrar Sesión Actual
              </button>
              <button
                onClick={saveCredentials}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-colors shadow-lg shadow-indigo-900/20"
              >
                <UserCheck size={16} />
                Guardar y Activar Auto-Snipe en Ciegos
              </button>
            </div>
        </div>

        {/* Keep-Alive */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 bg-surface-900 rounded-lg border border-surface-700">
          <div className="flex items-start gap-4 mb-4 sm:mb-0">
            <div className={`p-3 rounded-full ${keepAliveEnabled ? 'bg-amber-500/20 text-amber-400' : 'bg-surface-700 text-surface-400'}`}>
              <Shield size={24} />
            </div>
            <div>
              <h3 className="font-medium text-white text-md">Keep-Alive (Anti-Cierre de Sesión)</h3>
              <p className="text-surface-400 text-sm mt-1 max-w-md">
                Evita que DofiMall caduque tu sesión visitando el carrito en 2º plano silenciosamente cada 5 minutos.
              </p>
            </div>
          </div>
          
          <label className="relative inline-flex items-center cursor-pointer ml-auto sm:ml-0">
            <input type="checkbox" className="sr-only peer" checked={keepAliveEnabled} onChange={handleKeepAliveToggle} />
            <div className="w-14 h-7 bg-surface-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-amber-500"></div>
          </label>
        </div>

      </div>
    </div>
  );
}
