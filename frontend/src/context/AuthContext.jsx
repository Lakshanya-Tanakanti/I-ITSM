import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { get, post, tokenStore, setUnauthorizedHandler } from "../services/api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);

  useEffect(() => { setUnauthorizedHandler(logout); }, [logout]);

  useEffect(() => {
    if (!tokenStore.get()) return;
    get("/auth/me").then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const data = await post("/auth/login", { email, password });
    tokenStore.set(data.access_token);
    setUser(data.user);
    return data.user;
  };
  const refresh = async () => setUser(await get("/auth/me"));

  return <Ctx.Provider value={{ user, loading, login, logout, refresh, setUser }}>{children}</Ctx.Provider>;
}
