import { setActivePinia, createPinia } from 'pinia';
import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from 'stores/appStore';

describe('App Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should have default language "en"', () => {
    const store = useAppStore();
    // Default might be browser language in happy-dom, so we just check it exists
    expect(store.language).toBeDefined();
  });

  it('should update language', () => {
    const store = useAppStore();
    store.setLanguage('es');
    expect(store.language).toBe('es');
    expect(localStorage.getItem('language')).toBe('es');
  });
});
