import { useState } from 'react';
import { login } from '../utils/api';
import { toast } from 'react-hot-toast';
import { Crosshair, Lock, Mail, ShieldCheck } from 'lucide-react';

export default function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await login(email, password);
      localStorage.setItem('sniper_token', data.access_token);
      toast.success('Acceso táctico concedido');
      onLogin();
    } catch (err) {
      toast.error('Credenciales no autorizadas');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-950 px-4 relative overflow-hidden">
      {/* Background Decor */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-10">
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-brand-500 rounded-full blur-[120px]" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-brand-500 rounded-full blur-[120px]" />
      </div>

      <div className="max-w-md w-full animate-in fade-in zoom-in duration-500">
        {/* Logo Section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 shadow-lg shadow-brand-500/20 mb-4 ring-1 ring-white/10">
            <Crosshair size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">DofiMall Sniper</h1>
          <p className="text-surface-400 text-sm mt-1 uppercase tracking-widest font-medium opacity-50">
            Central de Operaciones Tácticas
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-surface-900/50 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
          {/* Card Scanline Effect */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-brand-500/50 to-transparent animate-scan" />

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-xs font-semibold text-surface-200/50 uppercase tracking-wider mb-2 block ml-1">
                Identificación de Operador
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-surface-400 group-focus-within:text-brand-400 transition-colors">
                  <Mail size={18} />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-surface-800/50 border border-white/5 rounded-xl py-3 pl-10 pr-4 text-white placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 transition-all"
                  placeholder="admin@odubasolar.com"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-surface-200/50 uppercase tracking-wider mb-2 block ml-1">
                Clave de Desbloqueo
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-surface-400 group-focus-within:text-brand-400 transition-colors">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-surface-800/50 border border-white/5 rounded-xl py-3 pl-10 pr-4 text-white placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 transition-all"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-brand-600/20 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <ShieldCheck size={20} />
                  <span>INICIAR MISIÓN</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer info */}
        <p className="mt-8 text-center text-surface-600 text-xs uppercase tracking-tighter opacity-30">
          Uso restringido para personal autorizado · v1.2.0 Tactical
        </p>
      </div>
    </div>
  );
}
