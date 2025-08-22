import axios from 'axios';

const TOKEN_KEY = 'heimdall_token';

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {}
  axios.defaults.headers.common['Authorization'] = token ? `Bearer ${token}` : undefined;
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {}
  delete axios.defaults.headers.common['Authorization'];
}

// Initialize on module load
const existing = getToken();
if (existing) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${existing}`;
}


