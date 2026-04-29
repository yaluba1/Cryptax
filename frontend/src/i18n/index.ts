import { createI18n } from 'vue-i18n';
import en from './en';
import es from './es';
import fr from './fr';
import de from './de';
import it from './it';
import pt from './pt';
import ja from './ja';

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en,
    es,
    fr,
    de,
    it,
    pt,
    ja,
  },
});

export default i18n;
