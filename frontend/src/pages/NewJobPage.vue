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
        >
          <template v-if="form.exchange === 'binance' || form.exchange === 'kraken'" v-slot:append>
            <q-icon
              name="help_outline"
              class="cursor-pointer text-primary"
              @click="showApiHelp"
            >
              <q-tooltip>{{ $t('newJob.apiHelp.title', { exchange: exchangeDisplayName }) }}</q-tooltip>
            </q-icon>
          </template>
        </q-input>

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

        <!-- Binance Bot CSV Upload -->
        <q-slide-transition>
          <div v-if="form.exchange === 'binance'" class="q-mb-md">
            <q-file
              v-model="botFiles"
              label="Upload Binance Bot CSV File(s) (Optional)"
              outlined
              multiple
              append
              use-chips
              accept=".csv"
            >
              <template v-slot:prepend>
                <q-icon name="attach_file" />
              </template>
              <template v-slot:append>
                <q-icon
                  name="help_outline"
                  class="cursor-pointer text-primary"
                  @click="showBotHelp"
                >
                  <q-tooltip>{{ $t('newJob.botHelp.title') }}</q-tooltip>
                </q-icon>
              </template>
            </q-file>
            <div class="text-caption text-grey q-mt-xs">
              Upload your exported Binance Bot/Grid Trading history CSV files to include them in your consolidated tax report.
            </div>
          </div>
        </q-slide-transition>

        <div v-if="duplicateJobMessage" class="text-negative q-mb-md">
          {{ duplicateJobMessage }}
        </div>

        <div class="row justify-end q-gutter-sm q-mt-md">
          <q-btn :label="$t('common.cancel')" color="grey" flat @click="onCancel" />
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

    <q-dialog v-model="apiHelpDialog">
      <q-card style="width: 500px; max-width: 90vw;" class="api-help-card rounded-borders">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6 text-weight-bold text-primary">{{ $t('newJob.apiHelp.title', { exchange: exchangeDisplayName }) }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-md">
          <div class="text-subtitle2 text-weight-bold q-mb-xs text-negative flex items-center">
            <q-icon name="gpp_maybe" class="q-mr-xs" size="sm" />
            {{ $t('newJob.apiHelp.important') }}
          </div>
          <q-banner dense class="bg-red-1 text-negative border-red rounded-borders q-mb-md">
            <span class="text-weight-medium">
              {{ $t('newJob.apiHelp.readOnlyWarning') }}
            </span>
          </q-banner>

          <div v-if="form.exchange === 'binance'">
            <p class="text-weight-bold q-mb-sm">{{ $t('newJob.apiHelp.binance.intro') }}</p>
            <ol class="q-pl-md q-gutter-y-xs text-body2">
              <li>{{ $t('newJob.apiHelp.binance.step1') }}</li>
              <li>{{ $t('newJob.apiHelp.binance.step2') }}</li>
              <li>{{ $t('newJob.apiHelp.binance.step3') }}</li>
              <li>{{ $t('newJob.apiHelp.binance.step4') }}</li>
              <li>{{ $t('newJob.apiHelp.binance.step5') }}</li>
            </ol>
          </div>
          <div v-else-if="form.exchange === 'kraken'">
            <p class="text-weight-bold q-mb-sm">{{ $t('newJob.apiHelp.kraken.intro') }}</p>
            <ol class="q-pl-md q-gutter-y-xs text-body2">
              <li>{{ $t('newJob.apiHelp.kraken.step1') }}</li>
              <li>{{ $t('newJob.apiHelp.kraken.step2') }}</li>
              <li>{{ $t('newJob.apiHelp.kraken.step3') }}</li>
              <li>{{ $t('newJob.apiHelp.kraken.step4') }}</li>
              <li>{{ $t('newJob.apiHelp.kraken.step5') }}</li>
            </ol>
          </div>

          <div class="q-mt-lg q-pt-md border-top text-caption text-grey-7">
            <div class="text-weight-bold q-mb-xs text-grey-9 flex items-center">
              <q-icon name="info" class="q-mr-xs" />
              {{ $t('newJob.apiHelp.disclaimerTitle') }}
            </div>
            <div>{{ $t('newJob.apiHelp.disclaimerText') }}</div>
          </div>
        </q-card-section>

        <q-card-actions align="right" class="q-pb-md q-pr-md">
          <q-btn flat :label="$t('newJob.apiHelp.close')" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="botHelpDialog">
      <q-card style="width: 500px; max-width: 90vw;" class="api-help-card rounded-borders">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6 text-weight-bold text-primary">{{ $t('newJob.botHelp.title') }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section class="q-pt-md">
          <p class="text-subtitle2 text-weight-bold text-primary q-mb-sm">
            {{ $t('newJob.botHelp.whenNeededTitle') }}
          </p>
          <p class="text-body2 q-mb-md">
            {{ $t('newJob.botHelp.whenNeededText') }}
          </p>

          <p class="text-subtitle2 text-weight-bold text-primary q-mb-sm">
            {{ $t('newJob.botHelp.howToGetTitle') }}
          </p>
          <ol class="q-pl-md q-gutter-y-xs text-body2 q-mb-md">
            <li>{{ $t('newJob.botHelp.step1') }}</li>
            <li>{{ $t('newJob.botHelp.step2') }}</li>
            <li>{{ $t('newJob.botHelp.step3') }}</li>
            <li>{{ $t('newJob.botHelp.step4') }}</li>
            <li>{{ $t('newJob.botHelp.step5') }}</li>
          </ol>

          <q-banner dense class="bg-blue-1 text-primary rounded-borders q-mb-md">
            <template v-slot:avatar>
              <q-icon name="lightbulb" color="primary" />
            </template>
            <span class="text-body2 text-weight-medium">
              {{ $t('newJob.botHelp.exportLimitNote') }}
            </span>
          </q-banner>

          <div class="q-mt-lg q-pt-md border-top text-caption text-grey-7">
            <div class="text-weight-bold q-mb-xs text-grey-9 flex items-center">
              <q-icon name="info" class="q-mr-xs" />
              {{ $t('newJob.apiHelp.disclaimerTitle') }}
            </div>
            <div>{{ $t('newJob.botHelp.disclaimerText') }}</div>
          </div>
        </q-card-section>

        <q-card-actions align="right" class="q-pb-md q-pr-md">
          <q-btn flat :label="$t('newJob.apiHelp.close')" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
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
const botFiles = ref<File[]>([]);
const apiHelpDialog = ref(false);
const botHelpDialog = ref(false);

const exchangeDisplayName = computed(() => {
  if (form.exchange === 'binance') return 'Binance';
  if (form.exchange === 'kraken') return 'Kraken';
  return '';
});

function showApiHelp() {
  apiHelpDialog.value = true;
}

function showBotHelp() {
  botHelpDialog.value = true;
}

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

const countryOptions = computed(() => [
  { label: t('newJob.countries.IE'), value: 'IE' },
  { label: t('newJob.countries.JP'), value: 'JP' },
  { label: t('newJob.countries.ES'), value: 'ES' },
  { label: t('newJob.countries.US'), value: 'US' },
  { label: t('newJob.countries.GENERIC'), value: 'GENERIC' },
]);

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
    const hasBotActivity = form.exchange === 'binance' && botFiles.value && botFiles.value.length > 0;
    
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
      generic: form.country === 'GENERIC' ? form.generic : null,
      has_bot_activity: hasBotActivity
    };

    const response = await api.post('/jobs', payload);
    const job_id = response.data.job_id;

    if (hasBotActivity) {
      const formData = new FormData();
      formData.append("api_key", form.api_key);
      formData.append("api_secret", form.api_secret);
      botFiles.value.forEach((file) => {
        formData.append("files", file);
      });
      
      await api.post(`/jobs/${job_id}/bot-activity`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
    }

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
  botFiles.value = [];
}

async function onCancel() {
  onReset();
  await router.push({ name: 'main' });
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
.body--dark .new-job-form {
  background: #1d1d1d;
}
.border-red {
  border: 1px solid var(--q-negative);
}
.border-top {
  border-top: 1px solid rgba(0, 0, 0, 0.12);
}
.body--dark .border-top {
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}
.body--dark .api-help-card {
  background: #1d1d1d;
}
</style>
