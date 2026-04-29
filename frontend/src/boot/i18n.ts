import { boot } from 'quasar/wrappers';
import i18n from 'src/i18n';
import { useAppStore } from 'src/stores/appStore';

export default boot(({ app }) => {
  // Set i18n instance on app
  app.use(i18n);

  // Sync i18n locale with appStore
  const appStore = useAppStore();
  
  // Set the initial locale
  i18n.global.locale.value = appStore.language;

  // Watch for changes in the store to update i18n locale
  // Note: In a boot file, you might want to use a watcher or just let the components handle it.
  // But setting it here ensures it's ready on boot.
});
