export default {
  common: {
    appTitle: 'CrypTax',
    logout: 'Disconnetti',
    clear: 'Pulisci',
    generate: 'Genera Rapporto Fiscale',
    loading: 'Caricamento...',
    copyright: '© {year} Yaluba. Tutti i diritti riservati.',
  },
  auth: {
    loginSuccess: 'Accesso effettuato con successo',
    loginError: 'Accesso fallito. Riprova.',
  },
  jobs: {
    title: 'Rapporti Fiscali',
    newReport: 'Crea Nuovo Rapporto Fiscale',
    table: {
      country: 'Paese',
      exchange: 'Exchange',
      year: 'Anno',
      fiat: 'Fiat',
      status: 'Stato',
      documents: 'Documenti',
    },
    status: {
      pending: 'In attesa',
      processing: 'In elaborazione',
      done: 'Completato',
      error: 'Errore',
    },
    noData: 'Nessun rapporto fiscale trovato.',
  },
  newJob: {
    title: 'Richiedi Nuovo Rapporto Fiscale',
    accountHolder: 'Email del Titolare dell\'Account',
    country: 'Paese di Residenza Fiscale',
    year: 'Anno Fiscale',
    exchange: 'Exchange',
    apiKey: 'Chiave API',
    apiSecret: 'Chiave Segreta',
    privateKey: 'Chiave Privata',
    generic: {
      longTermDays: 'Giorni per Plusvalenze a Lungo Termine',
      accountingMethod: 'Metodo Contabile',
    },
    validation: {
      required: 'Questo campo è obbligatorio',
      invalidEmail: 'Indirizzo email non valido',
      duplicateJob: 'Un rapporto fiscale per lo stesso paese, anno fiscale, exchange e fiat è già stato richiesto ed è in stato {status}.',
    },
    success: 'Rapporto fiscale richiesto con successo',
  },
};
