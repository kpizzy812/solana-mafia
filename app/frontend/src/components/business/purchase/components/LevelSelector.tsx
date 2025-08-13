/**
 * Level selector component for purchase modal
 */

import React from 'react';
import { Button } from '@/components/ui/Button';
import { useTranslation } from '@/locales';
import { cn } from '@/lib/utils';

interface LevelSelectorProps {
  selectedLevel: number;
  onLevelSelect: (level: number) => void;
  language: 'en' | 'ru';
}

export const LevelSelector: React.FC<LevelSelectorProps> = ({
  selectedLevel,
  onLevelSelect,
  language
}) => {
  const t = useTranslation(language);
  const maxLevels = 3; // 0, 1, 2 = Level 1, 2, 3

  return (
    <div>
      <div className="text-sm font-medium text-muted-foreground mb-3">
        {t.business_level}
      </div>
      <div className="flex gap-1 p-1 bg-muted rounded-lg">
        {Array.from({ length: maxLevels }, (_, i) => (
          <button
            key={i}
            onClick={() => onLevelSelect(i)}
            className={cn(
              'flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all',
              selectedLevel === i
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {t.level} {i + 1}
          </button>
        ))}
      </div>
    </div>
  );
};