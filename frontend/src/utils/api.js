const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Error en la petición');
  }
  return res.json();
}

// Dashboard
export const fetchDashboard = () => request('/dashboard');

// Products
export const fetchProducts = () => request('/products/');
export const addProduct = (data) =>
  request('/products/', { method: 'POST', body: JSON.stringify(data) });
export const addProductsBulk = (products) =>
  request('/products/bulk', { method: 'POST', body: JSON.stringify(products) });
export const updateProduct = (id, data) =>
  request(`/products/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
export const deleteProduct = (id) =>
  request(`/products/${id}`, { method: 'DELETE' });
export const toggleProduct = (id) =>
  request(`/products/${id}/toggle`, { method: 'POST' });
export const manualCheckout = (id) =>
  request(`/products/${id}/checkout`, { method: 'POST' });
export const fetchLiveView = (id) =>
  request(`/products/${id}/live-view`);

// Logs
export const fetchLogs = (limit = 50) => request(`/logs/?limit=${limit}`);
export const clearLogs = () => request('/logs/', { method: 'DELETE' });

// Actions
export const triggerCheckNow = () => request('/check-now', { method: 'POST' });
export const fetchHealth = () => request('/health');

// Config
export const fetchConfig = () => request('/config');
export const updateConfig = (data) =>
  request('/config', { method: 'POST', body: JSON.stringify(data) });
export const testNotification = () =>
  request('/notifications/test', { method: 'POST' });

// Settings (DofiMall Credentials)
export const fetchSettings = () => request('/settings');
export const updateSettings = (data) =>
  request('/settings', { method: 'PATCH', body: JSON.stringify(data) });
export const forceLogout = () => request('/settings/logout', { method: 'POST' });
