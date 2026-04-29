export default {
  common: {
    appTitle: 'CrypTax',
    logout: 'Déconnexion',
    clear: 'Effacer',
    generate: 'Générer le rapport fiscal',
    loading: 'Chargement...',
    copyright: '© {year} Yaluba. Tous droits réservés.',
  },
  auth: {
    loginSuccess: 'Connexion réussie',
    loginError: 'Échec de la connexion. Veuillez réessayer.',
  },
  jobs: {
    title: 'Rapports Fiscaux',
    newReport: 'Créer un nouveau rapport fiscal',
    table: {
      country: 'Pays',
      exchange: 'Exchange',
      year: 'Année',
      fiat: 'Fiat',
      status: 'Statut',
      documents: 'Documents',
    },
    status: {
      pending: 'En attente',
      processing: 'Traitement en cours',
      done: 'Terminé',
      error: 'Erreur',
    },
    noData: 'Aucun rapport fiscal trouvé.',
  },
  newJob: {
    title: 'Demander un nouveau rapport fiscal',
    accountHolder: 'E-mail du titulaire du compte',
    country: 'Pays de résidence fiscale',
    year: 'Année fiscale',
    exchange: 'Exchange',
    apiKey: 'Clé API',
    apiSecret: 'Clé secrète',
    privateKey: 'Clé privée',
    generic: {
      longTermDays: 'Jours pour gains en capital à long terme',
      accountingMethod: 'Méthode comptable',
    },
    validation: {
      required: 'Ce champ est obligatoire',
      invalidEmail: 'Adresse e-mail invalide',
      duplicateJob: 'Un rapport fiscal pour le même pays, la même année fiscale, le même exchange et le même fiat a déjà été demandé et est en état {status}.',
    },
    success: 'Rapport fiscal demandé avec succès',
  },
};
