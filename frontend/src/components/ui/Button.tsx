'use client';

import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary';
    loading?: boolean;
    loadingText?: string;
}

export function Button({
    variant = 'primary',
    loading = false,
    loadingText,
    children,
    className,
    disabled,
    ...props
}: ButtonProps) {
    return (
        <button
            className={cn(
                'px-5 py-2.5 rounded-lg font-medium text-sm transition-colors shadow-sm disabled:opacity-50',
                variant === 'primary'
                    ? 'bg-wabi-text text-wabi-bg hover:bg-wabi-text/90'
                    : 'bg-white border border-wabi-text/10 text-wabi-text hover:bg-wabi-text/5',
                className,
            )}
            disabled={disabled || loading}
            {...props}
        >
            {loading ? (loadingText || 'Saving...') : children}
        </button>
    );
}
