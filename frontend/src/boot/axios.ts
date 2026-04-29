import { boot } from 'quasar/wrappers';
import axios, { type AxiosInstance } from 'axios';
import { useAuthSessionStore } from 'stores/authSessionStore';

declare module 'vue' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance;
    $api: AxiosInstance;
  }
}

// Be careful when using SSR for client-side axios.
// Use process.env.CRYPTAX_API_URL directly from quasar.config.ts env
const api = axios.create({ baseURL: process.env.CRYPTAX_API_URL || '' });

// Add a request interceptor to include the JWT token in all API calls
api.interceptors.request.use((config) => {
  const authStore = useAuthSessionStore();
  if (authStore.jwt) {
    config.headers.Authorization = `Bearer ${authStore.jwt}`;
  }
  return config;
});

export default boot(({ app }) => {
  // for use inside Vue files (Options API) through this.$axios and this.$api

  app.config.globalProperties.$axios = axios;
  // ^ ^ ^ this will allow you to use this.$axios (for Vue Options API form)
  //       so you won't necessarily have to import axios in each vue file

  app.config.globalProperties.$api = api;
  // ^ ^ ^ this will allow you to use this.$api (for Vue Options API form)
  //       so you can easily perform requests against your app's API
});

export { api };
