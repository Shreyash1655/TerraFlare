import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  icon?: string;
  action?: ReactNode;
  className?: string;
  variant?: 'default' | 'metric';
}

export default function Card({
  children,
  title,
  subtitle,
  icon,
  action,
  className = '',
  variant = 'default'
}: CardProps) {
  return (
    <div className={`bg-[#1A2234] border border-[#374151] rounded p-3 flex flex-col ${className}`}>
      {(title || subtitle || icon || action) && (
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-start gap-2">
            {icon && <span className="material-symbols-outlined text-[#9CA3AF] text-sm mt-0.5">{icon}</span>}
            <div>
              {title && <h2 className="font-title-sm text-sm font-bold text-on-surface leading-tight">{title}</h2>}
              {subtitle && <div className="font-caption-mono text-[9px] text-[#9CA3AF] mt-0.5">{subtitle}</div>}
            </div>
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={`flex-1 ${variant === 'metric' ? 'flex flex-col justify-between' : ''}`}>
        {children}
      </div>
    </div>
  );
}