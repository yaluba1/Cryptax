export default {
  common: {
    appTitle: 'CrypTax',
    logout: 'Logout',
    clear: 'Clear',
    generate: 'Generate Tax Report',
    loading: 'Loading...',
    copyright: '© {year} Yaluba. All rights reserved.',
  },
  auth: {
    loginSuccess: 'Login successful',
    loginError: 'Login failed. Please try again.',
  },
  jobs: {
    title: 'Tax Reports',
    newReport: 'Create New Tax Report',
    table: {
      country: 'Country',
      exchange: 'Exchange',
      year: 'Year',
      fiat: 'Fiat',
      status: 'Status',
      documents: 'Documents',
    },
    status: {
      pending: 'Pending',
      processing: 'Processing',
      done: 'Done',
      error: 'Error',
    },
    noData: 'No tax reports found.',
  },
  newJob: {
    title: 'Request New Tax Report',
    accountHolder: 'Account Holder Email',
    country: 'Country of Tax Residence',
    year: 'Tax Year',
    exchange: 'Exchange',
    apiKey: 'API Key',
    apiSecret: 'Secret Key',
    privateKey: 'Private Key',
    generic: {
      longTermDays: 'Long Term Capital Gains Days',
      accountingMethod: 'Accounting Method',
    },
    validation: {
      required: 'This field is required',
      invalidEmail: 'Invalid email address',
      duplicateJob: 'A tax report for the same country, tax year, exchange and fiat has already been requested and is in state {status}.',
    },
    success: 'Tax report requested successfully',
  },
};
