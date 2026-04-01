import { useState, useEffect } from 'react';
import { Settings, Bell, Send } from 'lucide-react';
import { fetchConfig, updateConfig, testNotification } from '../utils/api';
import { toast } from 'react-hot-toast';

export default function ConfigPanel() {
  const [enabled, setEnabled] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await fetchConfig();
      setEnabled(data.notifications_enabled);
    } catch (e) {
      console.error(e);
      toast.error('Error cargando configuración');
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

  const handleTest = async () => {
    toast.loading('Enviando notificación...', { id: 'test' });
    try {
      await testNotification();
      toast.success('Notificación de prueba enviada', { id: 'test' });
    } catch (e) {
      toast.error('Error enviando prueba: ' + e.message, { id: 'test' });
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

      </div>
    </div>
  );
}
