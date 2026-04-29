<template>
  <q-page class="q-pa-xl">
    <div class="column items-center q-gutter-y-lg">
      <h1 class="text-h4 text-primary text-weight-bold">{{ $t('newJob.title') }}</h1>

      <q-form @submit="onSubmit" @reset="onReset" class="new-job-form shadow-2 q-pa-lg rounded-borders">
        <q-input
          v-model="form.account_holder"
          :label="$t('newJob.accountHolder')"
          type="email"
          outlined
          lazy-rules
          :rules="[val => !!val || $t('newJob.validation.required')]"
        />

        <div class="row q-col-gutter-md">
          <q-select
            v-model="form.country"
            :options="countryOptions"
            :label="$t('newJob.country')"
            outlined
            class="col-12 col-sm-6"
            emit-value
            map-options
            lazy-rules
            :rules="[val => !!val || $t('newJob.validation.required')]"
          />

          <q-input
            v-model.number="form.year"
            type="number"
            :label="$t('newJob.year')"
            outlined
            class="col-12 col-sm-6"
            lazy-rules
            :rules="[
              val => !!val || $t('newJob.validation.required'),
              val => val <= new Date().getFullYear() || 'Year cannot be in the future'
            ]"
          />
        </div>

        <!-- Generic specific options -->
        <q-slide-transition>
          <div v-if="form.country === 'GENERIC'" class="row q-col-gutter-md q-mb-md">
            <q-input
              v-model.number="form.generic.long_term_capital_gains_days"
              type="number"
              :label="$t('newJob.generic.longTermDays')"
              outlined
              class="col-12 col-sm-6"
            />
            <q-select
              v-model="form.generic.accounting_method"
              :options="['FIFO', 'LIFO', 'HIFO', 'LOFO']"
              :label="$t('newJob.generic.accountingMethod')"
              outlined
              class="col-12 col-sm-6"
            />
          </div>
        </q-slide-transition>

        <q-select
          v-model="form.exchange"
          :options="exchangeOptions"
          :label="$t('newJob.exchange')"
          outlined
          emit-value
          map-options
          lazy-rules
          :rules="[val => !!val || $t('newJob.validation.required')]"
        />

        <q-input
          v-model="form.api_key"
          :label="$t('newJob.apiKey')"
          outlined
          lazy-rules
          :rules="[val => !!val || $t('newJob.validation.required')]"
        />

        <q-input
          v-model="form.api_secret"
          :label="form.exchange === 'binance' ? $t('newJob.apiSecret') : $t('newJob.privateKey')"
          outlined
          type="password"
          lazy-rules
          :rules="[val => !!val || $t('newJob.validation.required')]"
        />

        <q-select
          v-model="form.fiat"
          :options="['EUR', 'USD', 'JPY', 'GBP']"
          label="Fiat Currency"
          outlined
          lazy-rules
          :rules="[val => !!val || $t('newJob.validation.required')]"
        />

        <div v-if="duplicateJobMessage" class="text-negative q-mb-md">
          {{ duplicateJobMessage }}
        </div>

        <div class="row justify-end q-gutter-sm q-mt-md">
          <q-btn :label="$t('common.clear')" type="reset" color="primary" flat class="q-ml-sm" />
          <q-btn 
            :label="$t('common.generate')" 
            type="submit" 
            color="primary" 
            :loading="isSubmitting"
            :disabled="!!duplicateJobMessage"
          />
        </div>
      </q-form>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useI18n } from 'vue-i18n';
import { useAuthSessionStore } from 'stores/authSessionStore';
import { useJobStore } from 'stores/jobStore';
import axios from 'axios';
import { api } from 'boot/axios';

const { t } = useI18n();
const $q = useQuasar();
const router = useRouter();
const authStore = useAuthSessionStore();
const jobStore = useJobStore();

const isSubmitting = ref(false);

const initialForm = {
  account_holder: authStore.email || '',
  country: null as string | null,
  year: new Date().getFullYear() - 1,
  exchange: null as string | null,
  api_key: '',
  api_secret: '',
  fiat: 'EUR',
  generic: {
    long_term_capital_gains_days: 365,
    accounting_method: 'FIFO'
  }
};

const form = reactive({ ...initialForm });

const countryOptions = [
  { label: 'Ireland (IE)', value: 'IE' },
  { label: 'Japan (JP)', value: 'JP' },
  { label: 'Spain (ES)', value: 'ES' },
  { label: 'United States (US)', value: 'US' },
  { label: 'Generic', value: 'GENERIC' },
];

const exchangeOptions = [
  { label: 'Binance', value: 'binance' },
  { label: 'Kraken', value: 'kraken' },
];

const duplicateJobMessage = computed(() => {
  if (!form.country || !form.exchange || !form.year || !form.fiat) return null;

  const existing = jobStore.jobs.find(j => 
    j.country === form.country && 
    j.exchange === form.exchange && 
    j.year === form.year && 
    j.fiat === form.fiat &&
    j.status !== 'error'
  );

  if (existing) {
    return t('newJob.validation.duplicateJob', { status: existing.status.toUpperCase() });
  }
  return null;
});

async function onSubmit() {
  isSubmitting.value = true;
  try {
    const payload = {
      lang: 'en', // Should match store language
      country: form.country,
      exchange: form.exchange,
      year: form.year,
      account_holder: form.account_holder,
      uid: authStore.uid,
      api_key: form.api_key,
      api_secret: form.api_secret,
      fiat: form.fiat,
      generic: form.country === 'GENERIC' ? form.generic : null
    };

    await api.post('/jobs', payload);

    $q.notify({
      type: 'positive',
      message: t('newJob.success')
    });

    await router.push({ name: 'main' });
  } catch (error: unknown) {
    console.error('Failed to create job:', error);
    let msg = 'An error occurred while requesting the tax report';
    if (axios.isAxiosError(error)) {
      msg = error.response?.data?.detail || msg;
    }
    $q.notify({
      type: 'negative',
      message: typeof msg === 'string' ? msg : 'Validation error'
    });
  } finally {
    isSubmitting.value = false;
  }
}

function onReset() {
  Object.assign(form, initialForm);
}

// Pre-fill email if it changes in store
watch(() => authStore.email, (newEmail) => {
  if (newEmail && !form.account_holder) {
    form.account_holder = newEmail;
  }
});
</script>

<style scoped>
.new-job-form {
  width: 100%;
  max-width: 600px;
  background: white;
}
</style>
