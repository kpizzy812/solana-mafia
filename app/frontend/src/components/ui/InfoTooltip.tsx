'use client';

import React, { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface InfoTooltipProps {
  content: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
  iconClassName?: string;
}

export const InfoTooltip: React.FC<InfoTooltipProps> = ({
  content,
  position = 'top',
  className,
  iconClassName
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const iconRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const handleClick = () => {
    setIsVisible(!isVisible);
  };

  const handleClickOutside = (event: MouseEvent) => {
    if (
      iconRef.current &&
      tooltipRef.current &&
      !iconRef.current.contains(event.target as Node) &&
      !tooltipRef.current.contains(event.target as Node)
    ) {
      setIsVisible(false);
    }
  };

  useEffect(() => {
    if (isVisible) {
      document.addEventListener('mousedown', handleClickOutside);
    } else {
      document.removeEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isVisible]);

  useEffect(() => {
    if (isVisible && iconRef.current && tooltipRef.current) {
      const iconRect = iconRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();
      
      let top = 0;
      let left = 0;

      switch (position) {
        case 'top':
          top = iconRect.top - tooltipRect.height - 8;
          left = iconRect.left + (iconRect.width / 2) - (tooltipRect.width / 2);
          break;
        case 'bottom':
          top = iconRect.bottom + 8;
          left = iconRect.left + (iconRect.width / 2) - (tooltipRect.width / 2);
          break;
        case 'left':
          top = iconRect.top + (iconRect.height / 2) - (tooltipRect.height / 2);
          left = iconRect.left - tooltipRect.width - 8;
          break;
        case 'right':
          top = iconRect.top + (iconRect.height / 2) - (tooltipRect.height / 2);
          left = iconRect.right + 8;
          break;
      }

      // Keep tooltip within viewport
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      
      if (left < 8) left = 8;
      if (left + tooltipRect.width > viewportWidth - 8) {
        left = viewportWidth - tooltipRect.width - 8;
      }
      if (top < 8) top = 8;
      if (top + tooltipRect.height > viewportHeight - 8) {
        top = viewportHeight - tooltipRect.height - 8;
      }

      setTooltipPosition({ top, left });
    }
  }, [isVisible, position]);

  return (
    <>
      <button
        ref={iconRef}
        onClick={handleClick}
        className={cn(
          'inline-flex items-center justify-center w-5 h-5 rounded-full',
          'hover:bg-muted/80 transition-all duration-200',
          'text-muted-foreground hover:text-foreground',
          'animate-pulse hover:animate-none',
          iconClassName
        )}
        type="button"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="animate-bounce"
          style={{ animationDuration: '2s' }}
        >
          <circle cx="12" cy="12" r="10"/>
          <path d="M9.09,9a3,3,0,0,1,5.83,1c0,2-3,3-3,3"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </button>

      {isVisible && (
        <div
          ref={tooltipRef}
          className={cn(
            'fixed z-50 max-w-xs bg-popover border border-border rounded-lg shadow-lg p-3',
            'text-sm text-popover-foreground',
            'animate-in fade-in-0 zoom-in-95',
            className
          )}
          style={{
            top: tooltipPosition.top,
            left: tooltipPosition.left,
          }}
        >
          {/* Arrow */}
          <div
            className={cn(
              'absolute w-2 h-2 bg-popover border rotate-45',
              position === 'top' && 'bottom-[-5px] left-1/2 transform -translate-x-1/2 border-t-0 border-l-0',
              position === 'bottom' && 'top-[-5px] left-1/2 transform -translate-x-1/2 border-b-0 border-r-0',
              position === 'left' && 'right-[-5px] top-1/2 transform -translate-y-1/2 border-l-0 border-b-0',
              position === 'right' && 'left-[-5px] top-1/2 transform -translate-y-1/2 border-r-0 border-t-0'
            )}
          />
          
          {content}
        </div>
      )}
    </>
  );
};