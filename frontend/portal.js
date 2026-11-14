(function () {
  const TOKEN_KEY = 'smartroute_session';
  const USER_KEY = 'smartroute_user';

  function token() { return sessionStorage.getItem(TOKEN_KEY); }
  function user() {
    try { return JSON.parse(sessionStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  }
  function saveSession(data, targetWindow = window) {
    targetWindow.sessionStorage.setItem(TOKEN_KEY, data.token);
    targetWindow.sessionStorage.setItem(USER_KEY, JSON.stringify(data.user));
  }
  function clearSession() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  }
  function escape(value) {
    return String(value ?? '').replace(/[&<>'"]/g, character => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    })[character]);
  }
  function label(value) {
    return String(value || '').replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
  }
  function time(value) {
    if (!value) return 'Not reported';
    return new Date(value).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }
  async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token()) headers.Authorization = `Bearer ${token()}`;
    const response = await fetch(path, { ...options, headers });
    const body = await response.json().catch(() => ({}));
    if (response.status === 401 && path !== '/api/v1/auth/login') {
      clearSession();
      location.replace('/login?expired=1');
      throw new Error('Your session expired');
    }
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Request failed');
    return body;
  }
  async function requireRole(expectedRole) {
    if (!token()) {
      location.replace(`/login?role=${expectedRole}`);
      return null;
    }
    const current = await api('/api/v1/auth/me');
    sessionStorage.setItem(USER_KEY, JSON.stringify(current));
    if (current.role !== expectedRole) {
      location.replace(`/portal/${current.role}`);
      return null;
    }
    document.querySelectorAll('[data-user-name]').forEach(node => { node.textContent = current.display_name; });
    document.querySelectorAll('[data-user-role]').forEach(node => { node.textContent = label(current.role); });
    return current;
  }
  async function logout() {
    try { await api('/api/v1/auth/logout', { method: 'POST' }); } catch (_) { /* Clear locally regardless. */ }
    clearSession();
    location.replace('/login');
  }
  function setMessage(message, type = 'info') {
    const node = document.querySelector('[data-message]');
    if (!node) return;
    node.textContent = message;
    node.className = `portal-message ${type}`;
    node.hidden = !message;
  }

  window.Portal = { api, clearSession, escape, label, logout, requireRole, saveSession, setMessage, time, token, user };
})();
