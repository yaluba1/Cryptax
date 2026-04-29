import { defineStore } from 'pinia';
import { jwtDecode } from 'jwt-decode';

/** Hanko JWT payload structure */
interface HankoJWTPayload {
  sub: string;
  email?: {
    address: string;
    is_primary: boolean;
    is_verified: boolean;
  };
  exp: number;
}

export const useAuthSessionStore = defineStore('authSession', {
  state: () => ({
    /** Authentication JWT token */
    jwt: (localStorage.getItem('jwt') as string) || null,
    /** User ID (extracted from JWT 'sub') */
    uid: (localStorage.getItem('uid') as string) || null,
    /** User email address (extracted from JWT 'email.address') */
    email: (localStorage.getItem('email') as string) || null,
  }),

  getters: {
    /** Whether the user is currently authenticated */
    isAuthenticated: (state) => !!state.jwt,
  },

  actions: {
    /**
     * Stores the session data and extracts info from JWT.
     * @param {string} token - The JWT token from Hanko.
     */
    setSession(token: string) {
      try {
        const decoded = jwtDecode<HankoJWTPayload>(token);
        this.jwt = token;
        this.uid = decoded.sub;
        this.email = decoded.email?.address || null;

        localStorage.setItem('jwt', token);
        localStorage.setItem('uid', this.uid);
        if (this.email) {
          localStorage.setItem('email', this.email);
        }
      } catch (error) {
        console.error('[AuthSessionStore] Failed to decode JWT:', error);
        this.clearSession();
      }
    },

    /**
     * Clears the session data from state and local storage.
     */
    clearSession() {
      this.jwt = null;
      this.uid = null;
      this.email = null;
      localStorage.removeItem('jwt');
      localStorage.removeItem('uid');
      localStorage.removeItem('email');
    },
  },
});
