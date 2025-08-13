'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { HomeIcon, QuestIcon, UsersIcon, UserIcon } from '@/components/ui/icons';

interface NavigationItem {
  id: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: {
    en: string;
    ru: string;
  };
}

const navigationItems: NavigationItem[] = [
  {
    id: 'home',
    href: '/',
    icon: HomeIcon,
    label: { en: 'Home', ru: 'Главная' },
  },
  {
    id: 'quests',
    href: '/quests',
    icon: QuestIcon,
    label: { en: 'Quests', ru: 'Задания' },
  },
  {
    id: 'referrals',
    href: '/referrals',
    icon: UsersIcon,
    label: { en: 'Referrals', ru: 'Рефералы' },
  },
  {
    id: 'profile',
    href: '/profile',
    icon: UserIcon,
    label: { en: 'Profile', ru: 'Профиль' },
  },
];

interface BottomNavigationProps {
  language?: 'en' | 'ru';
}

export const BottomNavigation: React.FC<BottomNavigationProps> = ({
  language = 'en',
}) => {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-background/95 backdrop-blur border-t border-border supports-[backdrop-filter]:bg-background/80">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-around py-2">
          {navigationItems.map((item) => {
            const isActive = pathname === item.href;
            const IconComponent = item.icon;
            
            return (
              <Link
                key={item.id}
                href={item.href}
                className={`flex flex-col items-center justify-center px-3 py-2 rounded-lg transition-all duration-200 ease-in-out min-w-0 flex-1 ${
                  isActive
                    ? 'text-primary bg-primary/10 scale-105'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
                }`}
              >
                <IconComponent className={`w-6 h-6 mb-1 transition-transform duration-200 ${
                  isActive ? 'scale-110' : ''
                }`} />
                <span className="text-xs font-medium truncate">
                  {item.label[language]}
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
};