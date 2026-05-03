<template>
  <q-page class="q-pa-xl">
    <div class="column items-center q-gutter-y-lg">
      <h1 class="text-h4 text-primary text-weight-bold">{{ $t('jobs.title') }}</h1>

      <q-table
        :rows="jobStore.jobs"
        :columns="columns"
        row-key="job_id"
        :loading="jobStore.isLoading"
        flat
        bordered
        class="jobs-table full-width"
        :no-data-label="$t('jobs.noData')"
      >
        <template v-slot:body-cell-country="props">
          <q-td :props="props">
            <div v-if="props.row.country !== 'GENERIC'">
              {{ getCountryName(props.row.country) }} ({{ props.row.country }})
            </div>
            <div v-else>
              <div>Generic</div>
              <div class="text-caption text-grey">
                {{ props.row.generic?.accounting_method }}, L[{{ props.row.generic?.long_term_capital_gains_days }}]
              </div>
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-exchange="props">
          <q-td :props="props" class="text-capitalize">
            {{ props.row.exchange }}
          </q-td>
        </template>

        <template v-slot:body-cell-status="props">
          <q-td :props="props">
            <q-badge :color="getStatusColor(props.row.status)" class="q-pa-xs">
              {{ $t(`jobs.status.${props.row.status}`) }}
            </q-badge>
          </q-td>
        </template>

        <template v-slot:body-cell-documents="props">
          <q-td :props="props">
            <div class="row q-gutter-xs">
              <q-btn
                v-for="doc in props.row.documents"
                :key="doc.document_id"
                flat
                dense
                color="primary"
                :label="doc.document_type"
                icon="download"
                @click="downloadDocument(doc.document_id)"
              >
                <q-tooltip>Download {{ doc.document_type }}</q-tooltip>
              </q-btn>
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-actions="props">
          <q-td :props="props" class="text-right">
            <q-btn
              flat
              round
              color="negative"
              icon="delete"
              @click="openDeleteDialog(props.row.job_id)"
            >
              <q-tooltip>{{ $t('jobs.delete.button') }}</q-tooltip>
            </q-btn>
          </q-td>
        </template>
      </q-table>

      <q-dialog v-model="confirmDialog" persistent>
        <q-card style="min-width: 400px">
          <q-card-section class="row items-center">
            <q-avatar icon="warning" color="negative" text-color="white" />
            <span class="q-ml-sm text-h6">{{ $t('jobs.delete.title') }}</span>
          </q-card-section>

          <q-card-section class="q-pt-none">
            <div class="text-subtitle2 text-negative q-mb-md">
              {{ $t('jobs.delete.warning') }}
            </div>
            <q-input
              v-model="confirmWord"
              :label="$t('jobs.delete.confirmText')"
              outlined
              dense
              autofocus
              @keyup.enter="confirmWord === 'DELETE' && confirmDelete()"
            />
          </q-card-section>

          <q-card-actions align="right">
            <q-btn flat :label="$t('jobs.delete.cancel')" color="primary" v-close-popup />
            <q-btn
              :label="$t('jobs.delete.button')"
              color="negative"
              :disabled="confirmWord !== 'DELETE'"
              @click="confirmDelete"
            />
          </q-card-actions>
        </q-card>
      </q-dialog>

      <q-btn
        color="primary"
        size="lg"
        :label="$t('jobs.newReport')"
        icon="add"
        :to="{ name: 'new-job' }"
        class="q-mt-md"
      />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useJobStore, type JobStatus } from 'stores/jobStore';
import { useAuthSessionStore } from 'stores/authSessionStore';
import { api } from 'boot/axios';
import axios from 'axios';
import { useQuasar, type QTableColumn } from 'quasar';

const { t } = useI18n();
const $q = useQuasar();
const jobStore = useJobStore();
const authStore = useAuthSessionStore();

const columns = computed<QTableColumn[]>(() => [
  { name: 'country', label: t('jobs.table.country'), field: 'country', align: 'left', sortable: true },
  { name: 'exchange', label: t('jobs.table.exchange'), field: 'exchange', align: 'left', sortable: true },
  { name: 'year', label: t('jobs.table.year'), field: 'year', align: 'center', sortable: true },
  { name: 'fiat', label: t('jobs.table.fiat'), field: 'fiat', align: 'center', sortable: true },
  { name: 'status', label: t('jobs.table.status'), field: 'status', align: 'center', sortable: true },
  { name: 'documents', label: t('jobs.table.documents'), field: 'documents', align: 'left' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
]);

const confirmDialog = ref(false);
const confirmWord = ref('');
const jobToDelete = ref<string | null>(null);

function openDeleteDialog(jobId: string) {
  jobToDelete.value = jobId;
  confirmWord.value = '';
  confirmDialog.value = true;
}

async function confirmDelete() {
  if (!jobToDelete.value || confirmWord.value !== 'DELETE') return;
  
  try {
    await api.delete(`/jobs/${jobToDelete.value}`);
    $q.notify({ type: 'positive', message: t('jobs.delete.success') });
    await fetchJobs();
  } catch (error: unknown) {
    console.error('Delete failed:', error);
    let message = t('jobs.delete.error');
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 401 || error.response?.status === 403) {
        message = t('jobs.delete.unauthorized');
      } else if (error.response?.status === 404) {
        message = t('jobs.delete.notFound');
      }
    }
    $q.notify({ type: 'negative', message });
  } finally {
    confirmDialog.value = false;
    jobToDelete.value = null;
  }
}

async function fetchJobs() {
  if (!authStore.email) return;
  jobStore.setLoading(true);
  try {
    const response = await api.get(`/jobs?acc=${authStore.email}`);
    jobStore.setJobs(response.data);
  } catch (error) {
    console.error('Failed to fetch jobs:', error);
    $q.notify({ type: 'negative', message: 'Failed to retrieve jobs list' });
  } finally {
    jobStore.setLoading(false);
  }
}

function getStatusColor(status: JobStatus): string {
  switch (status) {
    case 'done': return 'positive';
    case 'error': return 'negative';
    case 'pending': return 'warning';
    case 'processing': return 'info';
    default: return 'grey';
  }
}

function getCountryName(code: string): string {
  const names: Record<string, string> = {
    IE: 'Ireland',
    JP: 'Japan',
    ES: 'Spain',
    US: 'United States',
  };
  return names[code] || code;
}

async function downloadDocument(docId: string) {
  try {
    // Open download in new tab or handle as blob
    // We can use a direct link if the backend supports it with the token in query or just handle via axios
    const response = await api.get(`/documents/${docId}/download`, { responseType: 'blob' });
    
    // Create a temporary link to trigger download
    const blob = new Blob([response.data], { type: response.headers['content-type'] as string });
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    
    // Extract filename from content-disposition if available
    const contentDisposition = response.headers['content-disposition'];
    let fileName = 'document';
    if (contentDisposition) {
      const fileNameMatch = contentDisposition.match(/filename=(.+)/);
      if (fileNameMatch) fileName = fileNameMatch[1];
    }
    
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error('Download failed:', error);
    $q.notify({ type: 'negative', message: 'Failed to download document' });
  }
}

onMounted(async () => {
  await fetchJobs();
});
</script>

<style scoped>
.jobs-table {
  max-width: 1000px;
}
.text-decoration-none {
  text-decoration: none;
}
</style>
