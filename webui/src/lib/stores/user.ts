import { writable, type Readable } from "svelte/store";
import axios from "axios";
// Cookie auth only; no token storage

export interface UserInfo {
  email: string;
  [key: string]: unknown;
}

export interface UserState {
  user: UserInfo | null;
  loaded: boolean;
}

function createUserStore(): Readable<UserState> & { refresh: () => Promise<void>; logout: () => Promise<void> } {
  const { subscribe, set } = writable<UserState>({ user: null, loaded: false });

  const refresh = async (): Promise<void> => {
    try {
      const resp = await axios.get("/users/me", { withCredentials: true });
      set({ user: resp.data as UserInfo, loaded: true });
    } catch {
      set({ user: null, loaded: true });
    }
  };

  const logout = async (): Promise<void> => {
    try {
      // In cookie mode, backend should clear cookies on logout
      await axios.post("/auth/cookie/logout", undefined, { withCredentials: true });
    } finally {
      // Ensure local state is cleared and force a UI reload
      set({ user: null, loaded: true });
      if (typeof window !== "undefined" && window.location) {
        window.location.href = "/";
      }
    }
  };

  // No token capture; cookie-based session only

  // initialize
  // Cookie auth: no default Authorization header needed
  refresh();

  return { subscribe, refresh, logout };
}

export const userStore = createUserStore();
