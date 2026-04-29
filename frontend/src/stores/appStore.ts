import { defineStore } from 'pinia';

/** Supported language codes */
export type SupportedLanguage = 'en' | 'es' | 'fr' | 'de' | 'it' | 'pt' | 'ja';

/** Map of browser locales to supported languages */
export const SUPPORTED_LANGUAGES: SupportedLanguage[] = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ja'];

/**
 * Gets the initial language based on browser settings.
 * @returns {SupportedLanguage} The detected language or 'en'.
 */
function getInitialLanguage(): SupportedLanguage {
  const browserLang = navigator.language.split('-')[0] as SupportedLanguage;
  if (SUPPORTED_LANGUAGES.includes(browserLang)) {
    return browserLang;
  }
  return 'en';
}

export const useAppStore = defineStore('app', {
  state: () => ({
    /** Current selected language */
    language: (localStorage.getItem('language') as SupportedLanguage) || getInitialLanguage(),
  }),

  actions: {
    /**
     * Sets the application language and persists it to local storage.
     * @param {SupportedLanguage} lang - The language code to set.
     */
    setLanguage(lang: SupportedLanguage) {
      if (SUPPORTED_LANGUAGES.includes(lang)) {
        this.language = lang;
        localStorage.setItem('language', lang);
      }
    },
  },
});
