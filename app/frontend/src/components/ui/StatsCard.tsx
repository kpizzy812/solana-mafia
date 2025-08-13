import React from 'react';
import { Card, CardContent } from './Card';

interface StatsCardProps {
  icon: string;
  label: string;
  value: string | number;
  subtitle?: string;
  loading?: boolean;
}

export const StatsCard: React.FC<StatsCardProps> = ({
  icon,
  label,
  value,
  subtitle,
  loading = false,
}) => {
  if (loading) {
    return (
      <Card className="animate-pulse">
        <CardContent className="flex items-center space-x-3 p-4">
          <div className="w-10 h-10 bg-muted rounded-lg"></div>
          <div className="flex-1">
            <div className="h-4 bg-muted rounded mb-2"></div>
            <div className="h-6 bg-muted/60 rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="flex items-center space-x-3 p-4">
        <div className="flex-shrink-0 w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center">
          <span className="text-lg">{icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-muted-foreground truncate">
            {label}
          </p>
          <p className="text-lg font-semibold text-card-foreground">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-muted-foreground">
              {subtitle}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
};