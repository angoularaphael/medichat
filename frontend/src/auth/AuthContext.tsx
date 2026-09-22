import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { api, AuthUser, session } from "../api/client";

type AuthContextValue = {
  user: AuthUser | null;
  booting: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    const token = session.getToken();
    if (!token) {
      setBooting(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => session.clear())
      .finally(() => setBooting(false));
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => setUser(null);
    window.addEventListener("eir:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("eir:unauthorized", handleUnauthorized);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      booting,
      login: async (username, password) => {
        const response = await api.login(username, password);
        session.setToken(response.access_token);
        setUser(response.user);
      },
      logout: () => {
        session.clear();
        setUser(null);
      },
    }),
    [user, booting]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit etre utilise dans AuthProvider");
  return context;
}
