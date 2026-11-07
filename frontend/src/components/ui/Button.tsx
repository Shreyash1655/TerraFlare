import type { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  className = '',
  ...props
}: ButtonProps) {
  const baseStyle = "inline-flex items-center justify-center font-label-mono font-bold rounded transition-colors duration-200 gap-1.5 focus:outline-none";

  const variants = {
    primary: "bg-[#F59E0B] text-[#0B0F19] hover:bg-[#D97706] shadow-[0_0_10px_rgba(245,158,11,0.2)]",
    secondary: "bg-[#111827] border border-[#374151] text-[#F9FAFB] hover:border-[#38BDF8] hover:text-[#38BDF8]",
    outline: "bg-transparent border border-[#374151] text-[#9CA3AF] hover:text-[#F9FAFB] hover:border-[#F9FAFB]",
    ghost: "bg-transparent text-[#9CA3AF] hover:text-[#F9FAFB] hover:bg-[#1F2937]/50"
  };

  const sizes = {
    sm: "px-2 py-1 text-[10px]",
    md: "px-3 py-1.5 text-[11px]",
    lg: "px-4 py-2 text-xs"
  };

  return (
    <button
      className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {icon && <span className="material-symbols-outlined text-[1.2em]">{icon}</span>}
      {children}
    </button>
  );
}