import { defineStore } from 'pinia';

/** Job status types */
export type JobStatus = 'pending' | 'processing' | 'done' | 'error';

/** Document information */
export interface DocumentInfo {
  document_id: string;
  document_type: string;
}

/** Job list item structure */
export interface JobListItem {
  job_id: string;
  lang: string;
  country: string;
  exchange: string;
  year: number;
  fiat: string;
  status: JobStatus;
  documents: DocumentInfo[];
  generic?: {
    long_term_capital_gains_days: number;
    accounting_method: string;
  } | null;
}

export const useJobStore = defineStore('jobs', {
  state: () => ({
    /** List of tax report jobs */
    jobs: [] as JobListItem[],
    /** Whether jobs are currently being fetched */
    isLoading: false,
  }),

  actions: {
    /**
     * Updates the jobs list with new data.
     * @param {JobListItem[]} jobs - The list of jobs from the API.
     */
    setJobs(jobs: JobListItem[]) {
      this.jobs = jobs;
    },

    /**
     * Sets the loading state.
     * @param {boolean} loading - Loading status.
     */
    setLoading(loading: boolean) {
      this.isLoading = loading;
    },
  },
});
