export default {
  common: {
    appTitle: 'CrypTax',
    logout: 'Cerrar sesión',
    clear: 'Limpiar',
    generate: 'Generar Informe Fiscal',
    loading: 'Cargando...',
    copyright: '© {year} Yaluba. Todos los derechos reservados.',
  },
  auth: {
    loginSuccess: 'Inicio de sesión exitoso',
    loginError: 'Error al iniciar sesión. Por favor, inténtelo de nuevo.',
  },
  jobs: {
    title: 'Informes Fiscales',
    newReport: 'Crear Nuevo Informe Fiscal',
    table: {
      country: 'País',
      exchange: 'Exchange',
      year: 'Año',
      fiat: 'Fiat',
      status: 'Estado',
      documents: 'Documentos',
    },
    status: {
      pending: 'Pendiente',
      processing: 'Procesando',
      done: 'Completado',
      error: 'Error',
    },
    noData: 'No se encontraron informes fiscales.',
  },
  newJob: {
    title: 'Solicitar Nuevo Informe Fiscal',
    accountHolder: 'Correo del Titular de la Cuenta',
    country: 'País de Residencia Fiscal',
    year: 'Año Fiscal',
    exchange: 'Exchange',
    apiKey: 'Clave API',
    apiSecret: 'Clave Secreta',
    privateKey: 'Clave Privada',
    generic: {
      longTermDays: 'Días para Ganancias de Capital a Largo Plazo',
      accountingMethod: 'Método Contable',
    },
    validation: {
      required: 'Este campo es obligatorio',
      invalidEmail: 'Dirección de correo no válida',
      duplicateJob: 'Ya se ha solicitado un informe fiscal para el mismo país, año fiscal, exchange y fiat, y se encuentra en estado {status}.',
    },
    success: 'Informe fiscal solicitado con éxito',
  },
};
