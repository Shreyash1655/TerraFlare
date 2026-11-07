import type { ReactNode } from 'react';

interface PageHeaderProps {
  badge?: string;
  subsystem?: string;
  title: string;
  description: string;
  metadata?: string[];
  actions?: ReactNode;
  className?: string;
}

export default function PageHeader({
  badge = 'NASA SPACE APPS 2026',
  subsystem,
  title,
  description,
  metadata = [],
  actions,
  className = '',
}: PageHeaderProps) {
  return (
    <section className={`w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937] ${className}`}>
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div className="space-y-1.5 max-w-4xl">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
              {badge}
            </span>
            {subsystem && (
              <>
                <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
                <span className="font-caption-mono text-xs text-[#7bd0ff] font-semibold">{subsystem}</span>
              </>
            )}
            {metadata.map((item, idx) => (
              <span key={idx} className="flex items-center gap-2">
                <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
                <span className="font-caption-mono text-xs text-[#d8c3ad]">{item}</span>
              </span>
            ))}
          </div>
          <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
            {title}
          </h1>
          <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
            {description}
          </p>
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </section>
  );
}
