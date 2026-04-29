<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-avatar size="40px" class="q-mr-sm">
          <img src="~assets/logo.png" @error="handleLogoError" />
        </q-avatar>
        <q-toolbar-title class="text-weight-bold">
          {{ $t('common.appTitle') }}
        </q-toolbar-title>

        <div class="row items-center q-gutter-md">
          <div v-if="authStore.isAuthenticated" class="gt-xs">
            {{ authStore.email }}
          </div>

          <q-select
            v-model="currentLang"
            :options="langOptions"
            dense
            borderless
            emit-value
            map-options
            options-dense
            class="lang-select"
            color="white"
            dark
          >
            <template v-slot:prepend>
              <q-icon name="language" />
            </template>
          </q-select>

          <q-btn
            v-if="authStore.isAuthenticated"
            flat
            dense
            round
            icon="logout"
            @click="logout"
          >
            <q-tooltip>{{ $t('common.logout') }}</q-tooltip>
          </q-btn>
        </div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>

    <q-footer class="bg-grey-9 text-white q-pa-sm">
      <div class="text-center">
        <a href="https://www.yaluba.com" target="_blank" class="text-white text-decoration-none">
          {{ $t('common.copyright', { year: new Date().getFullYear() }) }}
        </a>
      </div>
    </q-footer>
  </q-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAppStore, type SupportedLanguage } from 'stores/appStore';
import { useAuthSessionStore } from 'stores/authSessionStore';

const { locale } = useI18n();
const router = useRouter();
const appStore = useAppStore();
const authStore = useAuthSessionStore();

const langOptions = [
  { label: 'English', value: 'en' },
  { label: 'Español', value: 'es' },
  { label: 'Français', value: 'fr' },
  { label: 'Deutsch', value: 'de' },
  { label: 'Italiano', value: 'it' },
  { label: 'Português', value: 'pt' },
  { label: '日本語', value: 'ja' },
];

const currentLang = computed({
  get: () => appStore.language,
  set: (val: SupportedLanguage) => {
    appStore.setLanguage(val);
    locale.value = val;
  },
});

async function logout() {
  authStore.clearSession();
  await router.push({ name: 'login' });
}

function handleLogoError(e: Event) {
  // If logo.png is missing, hide the image to show fallback or just nothing
  (e.target as HTMLImageElement).style.display = 'none';
}
</script>

<style scoped>
.lang-select {
  min-width: 120px;
}
.text-decoration-none {
  text-decoration: none;
}
</style>
