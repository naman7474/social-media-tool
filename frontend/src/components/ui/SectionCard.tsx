'use client';

import { cn } from '@/lib/utils';

interface SectionCardProps {
    title?: string;
    description?: string;
    badge?: string;
    headerRight?: React.ReactNode;
    children: React.ReactNode;
    className?: string;
}

export function SectionCard({
    title,
    description,
    badge,
    headerRight,
    children,
    className,
}: SectionCardProps) {
    return (
        <div
            className={cn(
                'bg-white/60 backdrop-blur-xl rounded-2xl border border-wabi-text/5 p-8 shadow-sm',
                className,
            )}
        >
            {(title || headerRight) && (
                <div className="mb-6 pb-4 border-b border-wabi-text/5 flex justify-between items-start">
                    <div>
                        {title && (
                            <h3 className="text-lg font-semibold tracking-tight">{title}</h3>
                        )}
                        {description && (
                            <p className="text-sm text-wabi-text/60 mt-1">{description}</p>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        {badge && (
                            <span className="px-3 py-1 bg-green-50 text-green-700 rounded-full text-xs font-medium border border-green-200">
                                {badge}
                            </span>
                        )}
                        {headerRight}
                    </div>
                </div>
            )}
            {children}
        </div>
    );
}
