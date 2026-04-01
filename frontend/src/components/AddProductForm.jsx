import { useState } from 'react';
import { Plus, Upload, Link } from 'lucide-react';

export default function AddProductForm({ onAdd, onAddBulk }) {
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [bulkMode, setBulkMode] = useState(false);
  const [bulkUrls, setBulkUrls] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (bulkMode) {
      const urls = bulkUrls.split('\n').map(u => u.trim()).filter(Boolean);
      if (urls.length > 0) {
        onAddBulk(urls);
        setBulkUrls('');
      }
    } else {
      if (url.trim()) {
        onAdd(url.trim(), name.trim());
        setUrl('');
        setName('');
      }
    }
  };

  return (
    <div className="bg-surface-800/60 border border-surface-700/40 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Plus size={16} className="text-brand-400" />
          Añadir producto
        </h2>
        <button
          onClick={() => setBulkMode(!bulkMode)}
          className="text-xs text-surface-200/50 hover:text-brand-400 transition-colors flex items-center gap-1"
        >
          {bulkMode ? <Link size={12} /> : <Upload size={12} />}
          {bulkMode ? 'URL individual' : 'Pegar varias URLs'}
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {bulkMode ? (
          <div className="space-y-3">
            <textarea
              value={bulkUrls}
              onChange={(e) => setBulkUrls(e.target.value)}
              placeholder="Pega una URL por línea:&#10;https://www.dofimall.com/product/123&#10;https://www.dofimall.com/product/456"
              rows={5}
              className="w-full bg-surface-900/60 border border-surface-700/50 rounded-lg px-4 py-3
                         text-sm text-white placeholder-surface-200/30 focus:outline-none
                         focus:border-brand-500/50 resize-none"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}
            />
            <button
              type="submit"
              disabled={!bulkUrls.trim()}
              className="px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white
                         text-sm font-medium transition-all disabled:opacity-30"
            >
              Añadir {bulkUrls.split('\n').filter(u => u.trim()).length || 0} URLs
            </button>
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.dofimall.com/product/..."
              required
              className="flex-1 bg-surface-900/60 border border-surface-700/50 rounded-lg px-4 py-2.5
                         text-sm text-white placeholder-surface-200/30 focus:outline-none
                         focus:border-brand-500/50"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}
            />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nombre (opcional)"
              className="sm:w-48 bg-surface-900/60 border border-surface-700/50 rounded-lg px-4 py-2.5
                         text-sm text-white placeholder-surface-200/30 focus:outline-none
                         focus:border-brand-500/50"
            />
            <button
              type="submit"
              disabled={!url.trim()}
              className="px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white
                         text-sm font-medium transition-all disabled:opacity-30 whitespace-nowrap"
            >
              <Plus size={14} className="inline mr-1 -mt-0.5" />
              Añadir
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
