import { store } from 'quasar/wrappers';
import { createPinia } from 'pinia';
import type { Router } from 'vue-router';

/*
 * When adding new properties to your store shapes, state or getters,
 * you can extend 'PiniaCustomProperties' interface from 'pinia'.
 * You can also'extend' the 'Store' interface to add types to the 'this' context.
 */
declare module 'pinia' {
  export interface PiniaCustomProperties {
    readonly router: Router;
  }
}

/*
 * If not building with SSR mode, you can directly export the Store instantiation;
 * the function below can be async too; either use async/await or return a Promise which resolves
 * with the Store instance.
 */

export default store((/* { ssrContext } */) => {
  const pinia = createPinia();

  // You can add Pinia plugins here
  // pinia.use(SomePiniaPlugin)

  return pinia;
});
