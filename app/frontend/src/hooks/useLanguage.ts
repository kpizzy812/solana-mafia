/**
 * Centralized language management hook with localStorage persistence
 * Решает проблемы с разными значениями языка по умолчанию и отсутствием кэширования
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import type { Language } from '@/locales';

const LANGUAGE_STORAGE_KEY = 'solana_mafia_language';
const DEFAULT_LANGUAGE: Language = 'en'; // Единое значение по умолчанию для всего приложения

export const useLanguage = () => {
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANGUAGE);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load language from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const savedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY) as Language;
        if (savedLanguage && (savedLanguage === 'en' || savedLanguage === 'ru')) {
          setLanguageState(savedLanguage);
        }
      } catch (error) {
        console.warn('Failed to load language from localStorage:', error);
      } finally {
        setIsLoaded(true);
      }
    } else {
      setIsLoaded(true);
    }
  }, []);

  // Save language to localStorage when it changes
  const setLanguage = useCallback((newLanguage: Language) => {
    setLanguageState(newLanguage);
    
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(LANGUAGE_STORAGE_KEY, newLanguage);
        console.log(`🌐 Language changed to: ${newLanguage}`);
      } catch (error) {
        console.warn('Failed to save language to localStorage:', error);
      }
    }
  }, []);

  return {
    language,
    setLanguage,
    isLoaded, // Use this to prevent flash of wrong language on page load
  };
};

export default useLanguage;