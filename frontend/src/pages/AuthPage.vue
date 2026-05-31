<template>
  <q-page class="flex flex-center">
    <div class="auth-container q-pa-md shadow-2 rounded-borders">
      <hanko-login
        :api="hankoApiUrl"
        :lang="hankoLang"
        @onAuthFlowCompleted="onSessionReady"
        @onSessionCreated="onSessionReady"
        @onError="onHankoError"
      />
    </div>
  </q-page>
</template>

<script setup lang="ts">
/**
 * @file pages/AuthPage.vue
 * @description Authentication page using Hanko Elements.
 */
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useI18n } from 'vue-i18n';
import { register } from '@teamhanko/hanko-elements';
import { all } from '@teamhanko/hanko-elements/i18n/all';
import { useAuthSessionStore } from 'stores/authSessionStore';
import { useAppStore } from 'stores/appStore';
import { es } from '../i18n/hanko/es-ES';
import { ja } from '../i18n/hanko/ja';

const { t } = useI18n();
const router = useRouter();
const $q = useQuasar();
const authStore = useAuthSessionStore();
const appStore = useAppStore();

const hankoApiUrl = process.env.HANKO_API_URL || '';

/** Map current app language to Hanko supported codes */
const hankoLang = computed(() => {
  const lang = appStore.language.substring(0, 2);
  return lang === 'pt' ? 'ptBR' : lang;
});

async function onSessionReady() {
  console.info('[AuthPage] Hanko session ready');
  try {
    // Hanko sets a 'hanko' cookie with the JWT
    const token = $q.cookies.get('hanko');

    if (!token) {
      throw new Error('No JWT found in cookies');
    }

    authStore.setSession(token);

    $q.notify({
      type: 'positive',
      message: t('auth.loginSuccess'),
    });

    await router.push({ name: 'main' });
  } catch (error) {
    console.error('[AuthPage] Failed to process session:', error);
    $q.notify({
      type: 'negative',
      message: t('auth.loginError'),
    });
  }
}

function onHankoError(error: unknown) {
  console.error('[AuthPage] Hanko error:', error);
  $q.notify({
    type: 'negative',
    message: t('auth.loginError'),
  });
}

onMounted(async () => {
  try {
    await register(hankoApiUrl, {
      fallbackLanguage: 'en',
      enablePasskeys: false,
      hidePasskeyButtonOnLogin: true,
      // Provide all built-in translations plus our custom Spanish overrides
      translations: { ...all, es, ja },
      // Re-validate the session cookie every 60 seconds in the background
      sessionCheckInterval: 60_000,
    });
    console.info('[AuthPage] Hanko elements registered');
  } catch (e) {
    console.error('[AuthPage] Failed to register Hanko:', e);
  }
});
</script>

<style scoped>
.auth-container {
  width: 100%;
  max-width: 450px;
  background: white;
}
.body--dark .auth-container {
  background: #1d1d1d;
}
</style>
