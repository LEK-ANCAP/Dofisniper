const BASE = '/api';

function getAuthHeader() {
  const token = localStorage.getItem('sniper_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const headers = { 
    'Content-Type': 'application/json', 
    ...getAuthHeader(),
    ...options.headers 
  };

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    localStorage.removeItem('sniper_token');
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/login';
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Error en la petición');
  }
  return res.json();
}

// Auth
export const login = (email, password) => 
  request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
export const fetchMe = () => request('/auth/me');

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

export const forceLogout = () =>
  request('/settings/logout', { method: 'POST' });

// Analytics
export const fetchProductAnalytics = (id) => request(`/analytics/product/${id}`);

// Intelligence
export const fetchIntelligenceDashboard = () => request('/market-intelligence/dashboard');
export const fetchProductHistory = (id) => request(`/market-intelligence/history/${id}`);
export const fetchDemandRanking = () => request('/market-intelligence/demand-ranking');
export const fetchDistribution = () => request('/market-intelligence/distribution');

// Categories
export const fetchCategories = () => request('/categories');
export const createCategory = (data) => request('/categories', { method: 'POST', body: JSON.stringify(data) });
export const updateCategory = (id, data) => request(`/categories/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
export const deleteCategory = (id) => request(`/categories/${id}`, { method: 'DELETE' });