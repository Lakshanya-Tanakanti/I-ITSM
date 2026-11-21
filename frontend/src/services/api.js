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

/** Turn any axios error into a readable message. */
export function errMsg(e) {
  if (!e) return "Something went wrong.";
  if (!e.response) return e.code === "ECONNABORTED" ? "The server took too long to respond." : "Cannot reach the server. Is the backend running on port 8000?";
  const d = e.response.data;
  if (d && typeof d === "object") {
    const extra = Array.isArray(d.errors) ? d.errors.map((x) => (typeof x === "string" ? x : x.message || x.msg || JSON.stringify(x))).filter(Boolean) : [];
    const base = typeof d.detail === "string" ? d.detail : "Request failed.";
    return extra.length ? `${base} ${extra.join(" ")}` : base;
  }
  return `Request failed (${e.response.status}).`;
}

export const get = (url, params) => api.get(url, { params }).then((r) => r.data);
export const post = (url, body) => api.post(url, body).then((r) => r.data);
export const patch = (url, body) => api.patch(url, body).then((r) => r.data);
export const put = (url, body) => api.put(url, body).then((r) => r.data);
export default api;
