import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api, ApiError } from "@/lib/api";
import type { LoginInput, ProfileUpdate, RegisterInput, User } from "@/types/auth";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "authenticated"; user: User }
  | { status: "anonymous"; user: null };

type AuthContextValue = AuthState & {
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (input: ProfileUpdate) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });

  useEffect(() => {
    api
      .me()
      .then(({ user }) => setState({ status: "authenticated", user }))
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) {
          setState({ status: "anonymous", user: null });
          return;
        }
        setState({ status: "anonymous", user: null });
      });
  }, []);

  const login = useCallback(async (input: LoginInput) => {
    const { user } = await api.login(input);
    setState({ status: "authenticated", user });
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    const { user } = await api.register(input);
    setState({ status: "authenticated", user });
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setState({ status: "anonymous", user: null });
  }, []);

  const updateProfile = useCallback(async (input: ProfileUpdate) => {
    const { user } = await api.updateProfile(input);
    setState({ status: "authenticated", user });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, register, logout, updateProfile }),
    [state, login, register, logout, updateProfile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
