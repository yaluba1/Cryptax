export default {
  common: {
    appTitle: 'CrypTax',
    logout: 'Abmelden',
    clear: 'Leeren',
    generate: 'Steuerbericht generieren',
    loading: 'Laden...',
    copyright: '© {year} Yaluba. Alle Rechte vorbehalten.',
  },
  auth: {
    loginSuccess: 'Anmeldung erfolgreich',
    loginError: 'Anmeldung fehlgeschlagen. Bitte versuchen Sie es erneut.',
  },
  jobs: {
    title: 'Steuerberichte',
    newReport: 'Neuen Steuerbericht erstellen',
    table: {
      country: 'Land',
      exchange: 'Börse',
      year: 'Jahr',
      fiat: 'Fiat',
      status: 'Status',
      documents: 'Dokumente',
    },
    status: {
      pending: 'Ausstehend',
      processing: 'Wird verarbeitet',
      done: 'Abgeschlossen',
      error: 'Fehler',
    },
    noData: 'Keine Steuerberichte gefunden.',
  },
  newJob: {
    title: 'Neuen Steuerbericht anfordern',
    accountHolder: 'E-Mail des Kontoinhabers',
    country: 'Land des steuerlichen Wohnsitzes',
    year: 'Steuerjahr',
    exchange: 'Börse',
    apiKey: 'API-Schlüssel',
    apiSecret: 'Geheimer Schlüssel',
    privateKey: 'Privater Schlüssel',
    generic: {
      longTermDays: 'Tage für langfristige Kapitalerträge',
      accountingMethod: 'Buchhaltungsmethode',
    },
    validation: {
      required: 'Dieses Feld ist obligatorisch',
      invalidEmail: 'Ungültige E-Mail-Adresse',
      duplicateJob: 'Ein Steuerbericht für dasselbe Land, dasselbe Steuerjahr, dieselbe Börse und dasselbe Fiat wurde bereits angefordert und befindet sich im Status {status}.',
    },
    success: 'Steuerbericht erfolgreich angefordert',
  },
};
