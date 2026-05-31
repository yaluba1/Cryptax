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

          <q-btn
            flat
            dense
            round
            :icon="appStore.isDarkMode ? 'light_mode' : 'dark_mode'"
            @click="toggleDarkMode"
            class="q-mr-sm"
          >
            <q-tooltip>{{ appStore.isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode' }}</q-tooltip>
          </q-btn>

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

    <q-footer :class="footerClass" class="q-pa-md border-top">
      <div class="row items-center full-width">
        <div class="col">
          <a href="https://github.com/yaluba1/Cryptax" target="_blank" class="row items-center q-gutter-xs text-decoration-none hover-opacity" :class="appStore.isDarkMode ? 'text-white' : 'text-grey-9'" style="width: fit-content">
            <img :src="githubLogoSrc" alt="GitHub" class="github-logo" />
            <span class="text-caption text-weight-medium">CrypTax</span>
          </a>
        </div>
        
        <div class="col text-center">
          <a href="https://www.yaluba.com" target="_blank" class="text-decoration-none hover-opacity" :class="appStore.isDarkMode ? 'text-white' : 'text-grey-9'">
            {{ $t('common.copyright', { year: new Date().getFullYear() }) }}
          </a>
        </div>
        
        <div class="col">
          <div class="row items-center justify-end q-gutter-sm">
            <span class="text-caption text-weight-medium">{{ $t('tips.buyMeADrink') }}</span>
            <img :src="btcLogo" alt="Bitcoin" class="crypto-logo cursor-pointer" @click="openTipDialog('btc')" />
            <img :src="bnbLogo" alt="BNB" class="crypto-logo cursor-pointer" @click="openTipDialog('bnb')" />
            <img :src="solLogo" alt="Solana" class="crypto-logo cursor-pointer" @click="openTipDialog('sol')" />
          </div>
        </div>
      </div>
    </q-footer>

    <q-dialog v-model="showTipDialog">
      <q-card style="min-width: 350px" :class="appStore.isDarkMode ? 'bg-grey-9 text-white' : 'bg-white text-grey-9'">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">{{ tipTitle }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="column items-center q-gutter-md">
          <template v-if="tipType === 'btc' || tipType === 'sol'">
            <q-img :src="currentQr" width="200px" height="200px" class="rounded-borders shadow-2" />
            <div class="text-center break-all text-caption q-px-md">
              {{ tipUri }}
            </div>
            <q-btn
              color="primary"
              outline
              :label="$t('tips.copyUri')"
              icon="content_copy"
              @click="copyTipInfo"
            />
          </template>

          <template v-else-if="tipType === 'bnb'">
            <div class="full-width q-px-xl q-gutter-y-sm">
              <div class="row justify-between">
                <span class="text-weight-bold">{{ $t('tips.network') }}:</span>
                <span>BNB Chain</span>
              </div>
              <div class="row justify-between">
                <span class="text-weight-bold">{{ $t('tips.chainId') }}:</span>
                <span>56</span>
              </div>
              <div class="row justify-between">
                <span class="text-weight-bold">{{ $t('tips.token') }}:</span>
                <span>BNB</span>
              </div>
              <div class="q-mt-md">
                <div class="text-weight-bold q-mb-xs">Address:</div>
                <div class="text-caption bg-grey-8 text-white q-pa-sm rounded-borders break-all" v-if="appStore.isDarkMode">
                  0x93EaC01421fe645e42F57a639F54AFa6DBc178d4
                </div>
                <div class="text-caption bg-grey-2 text-grey-9 q-pa-sm rounded-borders break-all" v-else>
                  0x93EaC01421fe645e42F57a639F54AFa6DBc178d4
                </div>
              </div>
            </div>
            <q-btn
              color="primary"
              outline
              :label="$t('tips.copyAddress')"
              icon="content_copy"
              @click="copyTipInfo"
              class="q-mt-sm"
            />
          </template>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { useAppStore, type SupportedLanguage } from 'stores/appStore';
import { useAuthSessionStore } from 'stores/authSessionStore';
import { copyToClipboard } from 'quasar';

// Import logos
import githubLogoLight from 'assets/Github_logo.svg';
import githubLogoDark from 'assets/Github_logo_white.svg';
import btcLogo from 'assets/bitcoin.svg';
import bnbLogo from 'assets/bnb.svg';
import solLogo from 'assets/solana.svg';

// QR Codes
import btcQrLight from 'assets/btc-qr.svg';
import btcQrDark from 'assets/btc-qr-dark.svg';
import solQrLight from 'assets/solana-qr.svg';
import solQrDark from 'assets/solana-qr-dark.svg';

const $q = useQuasar();
const { locale, t } = useI18n();
const router = useRouter();
const appStore = useAppStore();
const authStore = useAuthSessionStore();

// Tipping State
const showTipDialog = ref(false);
const tipType = ref<'btc' | 'sol' | 'bnb'>('btc');

const tipTitle = computed(() => {
  switch (tipType.value) {
    case 'btc': return 'Bitcoin';
    case 'sol': return 'Solana';
    case 'bnb': return 'BNB Chain';
    default: return '';
  }
});

const currentQr = computed(() => {
  if (tipType.value === 'btc') return appStore.isDarkMode ? btcQrDark : btcQrLight;
  if (tipType.value === 'sol') return appStore.isDarkMode ? solQrDark : solQrLight;
  return '';
});

const tipUri = computed(() => {
  if (tipType.value === 'btc') return 'bitcoin:bc1qhja0dm86zvwhvarqv0sgs8zed5v39g6khvjety?amount=0.00002&message=Cryptax%20tips';
  if (tipType.value === 'sol') return 'solana:4q3tmrDPhh2YzLjkAoc5mkiuXq1Dbtn5uzRH1UaZLrRR?amount=0.02&label=Cryptax%20tips';
  if (tipType.value === 'bnb') return '0x93EaC01421fe645e42F57a639F54AFa6DBc178d4';
  return '';
});

function openTipDialog(type: 'btc' | 'sol' | 'bnb') {
  tipType.value = type;
  showTipDialog.value = true;
}


// Watch for dark mode changes and update Quasar's Dark plugin
watch(() => appStore.isDarkMode, (val) => {
  $q.dark.set(val);
}, { immediate: true });

onMounted(() => {
  // Ensure the initial state is correctly set in Quasar
  $q.dark.set(appStore.isDarkMode);
});

const githubLogoSrc = computed(() => appStore.isDarkMode ? githubLogoDark : githubLogoLight);
const footerClass = computed(() => appStore.isDarkMode ? 'bg-dark text-white' : 'bg-grey-2 text-grey-9');

function toggleDarkMode() {
  appStore.setDarkMode(!appStore.isDarkMode);
}

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

async function copyTipInfo() {
  try {
    await copyToClipboard(tipUri.value);
    $q.notify({
      type: 'positive',
      message: t('tips.copied'),
    });
  } catch {
    $q.notify({
      type: 'negative',
      message: 'Failed to copy',
    });
  }
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
.github-logo {
  height: 24px;
  width: 24px;
  transition: opacity 0.3s ease;
}
.github-logo:hover {
  opacity: 0.7;
}
.hover-opacity:hover {
  opacity: 0.7;
}
.border-top {
  border-top: 1px solid rgba(0, 0, 0, 0.1);
}
.body--dark .border-top {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.crypto-logo {
  height: 24px;
  width: 24px;
  transition: transform 0.3s ease;
}
.crypto-logo:hover {
  transform: scale(1.1);
  opacity: 0.8;
}
.break-all {
  word-break: break-all;
}
</style>
