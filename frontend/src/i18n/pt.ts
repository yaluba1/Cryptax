export default {
  common: {
    appTitle: 'CrypTax',
    logout: 'Sair',
    clear: 'Limpar',
    generate: 'Gerar Relatório Fiscal',
    loading: 'Carregando...',
    copyright: '© {year} Yaluba. Todos os direitos reservados.',
  },
  auth: {
    loginSuccess: 'Login realizado com sucesso',
    loginError: 'Falha no login. Por favor, tente novamente.',
  },
  jobs: {
    title: 'Relatórios Fiscais',
    newReport: 'Criar Novo Relatório Fiscal',
    table: {
      country: 'País',
      exchange: 'Exchange',
      year: 'Ano',
      fiat: 'Fiat',
      status: 'Status',
      documents: 'Documentos',
    },
    status: {
      pending: 'Pendente',
      processing: 'Processando',
      done: 'Concluído',
      error: 'Erro',
    },
    noData: 'Nenhum relatório fiscal encontrado.',
  },
  newJob: {
    title: 'Solicitar Novo Relatório Fiscal',
    accountHolder: 'E-mail do Titular da Conta',
    country: 'País de Residência Fiscal',
    year: 'Ano Fiscal',
    exchange: 'Exchange',
    apiKey: 'Chave API',
    apiSecret: 'Chave Secreta',
    privateKey: 'Chave Privada',
    generic: {
      longTermDays: 'Dias para Ganhos de Capital a Longo Prazo',
      accountingMethod: 'Método Contábil',
    },
    validation: {
      required: 'Este campo é obrigatório',
      invalidEmail: 'Endereço de e-mail inválido',
      duplicateJob: 'Um relatório fiscal para o mesmo país, ano fiscal, exchange e fiat já foi solicitado e está no estado {status}.',
    },
    success: 'Relatório fiscal solicitado com sucesso',
  },
};
