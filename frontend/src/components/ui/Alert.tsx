'use client';

import { cn } from '@/lib/utils';

interface AlertProps {
    message: string;
    type: 'success' | 'error';
    className?: string;
}

export function Alert({ message, type, className }: AlertProps) {
    return (
        <div
            className={cn(
                'px-4 py-3 rounded-lg text-sm font-medium border',
                type === 'success'
                    ? 'bg-green-50 text-green-700 border-green-200'
                    : 'bg-red-50 text-red-600 border-red-200',
                className,
            )}
        >
            {message}
        </div>
    );
}
