import { en } from './en';
import { ru } from './ru';

export type Language = 'en' | 'ru';
export type TranslationKeys = typeof en;

export const translations: Record<Language, TranslationKeys> = {
  en,
  ru,
};

export const useTranslation = (language: Language) => {
  return translations[language];
};