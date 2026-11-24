import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry && localStorage.getItem('refresh')) {
      original._retry = true;
      try {
        const { data } = await axios.post(`${API_BASE}/auth/refresh/`, { refresh: localStorage.getItem('refresh') });
        localStorage.setItem('access', data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch {
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
        localStorage.removeItem('user');
        window.location.reload();
      }
    }
    return Promise.reject(error);
  }
);

export const auth = {
  async login(username, password) {
    const { data } = await api.post('/auth/login/', { username, password });
    localStorage.setItem('access', data.access);
    localStorage.setItem('refresh', data.refresh);
    const meRes = await api.get('/me/');
    localStorage.setItem('user', JSON.stringify(meRes.data));
    return meRes.data;
  },
  async register(username, password, batch) {
    const { data } = await api.post('/auth/register/', { username, password, batch });
    localStorage.setItem('access', data.access);
    localStorage.setItem('refresh', data.refresh);
    const userPayload = data.user || (await api.get('/me/')).data;
    localStorage.setItem('user', JSON.stringify(userPayload));
    return userPayload;
  },
  logout() {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    localStorage.removeItem('user');
  },
  getUser() {
    try {
      return JSON.parse(localStorage.getItem('user'));
    } catch {
      return null;
    }
  }
};

export const unwrap = (data) => (data && data.results ? data.results : data || []);
export default api;
export { API_BASE };
