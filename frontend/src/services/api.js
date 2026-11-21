import axios from "axios";

const TOKEN_KEY = "iitsm_token";
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

const api = axios.create({ baseURL: "/api", timeout: 20000 });

api.interceptors.request.use((config) => {
  const t = tokenStore.get();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

let onUnauthorized = null;
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

api.interceptors.response.use(
  (r) => r,
  (error) => {
    const url = error.config?.url || "";
    if (error.response?.status === 401 && !url.includes("/auth/login") && onUnauthorized) onUnauthorized();
    return Promise.reject(error);
  }
);

// errMsg lives in errors.js so that it can be unit tested without a browser.
export { errMsg } from "./errors.js";

export const get = (url, params) => api.get(url, { params }).then((r) => r.data);
export const post = (url, body) => api.post(url, body).then((r) => r.data);
export const patch = (url, body) => api.patch(url, body).then((r) => r.data);
export const put = (url, body) => api.put(url, body).then((r) => r.data);
export default api;
