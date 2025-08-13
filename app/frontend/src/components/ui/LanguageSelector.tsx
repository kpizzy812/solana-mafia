'use client';

import React, { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDownIcon } from './icons';

interface LanguageSelectorProps {
  language: 'en' | 'ru';
  onLanguageChange: (lang: 'en' | 'ru') => void;
}

const languages = [
  { code: 'en' as const, name: 'English', flag: '🇺🇸' },
  { code: 'ru' as const, name: 'Русский', flag: '🇷🇺' },
];

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  language,
  onLanguageChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLanguage = languages.find(lang => lang.code === language) || languages[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLanguageSelect = (langCode: 'en' | 'ru') => {
    onLanguageChange(langCode);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center space-x-2 px-3 py-2 rounded-lg bg-card text-card-foreground',
          'hover:bg-accent hover:text-accent-foreground transition-colors',
          'text-sm font-medium min-w-0 flex-shrink-0 h-[40px]'
        )}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="text-base">{currentLanguage.flag}</span>
        <span className="hidden xs:inline">{currentLanguage.code.toUpperCase()}</span>
        <ChevronDownIcon
          className={cn(
            'w-4 h-4 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 bg-popover border border-border rounded-lg shadow-lg z-50" style={{ width: dropdownRef.current?.offsetWidth || 'auto' }}>
          <div className="py-1" role="listbox">
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageSelect(lang.code)}
                className={cn(
                  'w-full flex items-center justify-center px-3 py-2 text-sm',
                  'hover:bg-accent hover:text-accent-foreground transition-colors',
                  language === lang.code && 'bg-accent text-accent-foreground'
                )}
                role="option"
                aria-selected={language === lang.code}
              >
                <span className="text-base">{lang.flag}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};