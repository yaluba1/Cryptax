export default {
  common: {
    appTitle: 'CrypTax',
    logout: 'ログアウト',
    clear: 'クリア',
    generate: '税務レポートを生成',
    loading: '読み込み中...',
    copyright: '© {year} Yaluba. All rights reserved.',
  },
  auth: {
    loginSuccess: 'ログインに成功しました',
    loginError: 'ログインに失敗しました。もう一度お試しください。',
  },
  jobs: {
    title: '税務レポート',
    newReport: '新規税務レポート作成',
    table: {
      country: '国',
      exchange: '取引所',
      year: '年度',
      fiat: '法定通貨',
      status: 'ステータス',
      documents: 'ドキュメント',
    },
    status: {
      pending: '保留中',
      processing: '処理中',
      done: '完了',
      error: 'エラー',
    },
    noData: '税務レポートが見つかりません。',
  },
  newJob: {
    title: '新規税務レポートのリクエスト',
    accountHolder: 'アカウント所有者のメールアドレス',
    country: '居住国',
    year: '課税年度',
    exchange: '取引所',
    apiKey: 'APIキー',
    apiSecret: 'シークレットキー',
    privateKey: 'プライベートキー',
    generic: {
      longTermDays: '長期譲渡所得の対象期間（日）',
      accountingMethod: '会計方法',
    },
    validation: {
      required: 'このフィールドは必須です',
      invalidEmail: '無効なメールアドレスです',
      duplicateJob: '同じ国、年度、取引所、法定通貨の税務レポートは既にリクエストされており、ステータスは {status} です。',
    },
    success: '税務レポートのリクエストに成功しました',
  },
};
