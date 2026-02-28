'use client';

import { cn } from '@/lib/utils';

interface FormFieldProps {
    label: string;
    hint?: string;
    children: React.ReactNode;
    className?: string;
}

export function FormField({ label, hint, children, className }: FormFieldProps) {
    return (
        <div className={cn('mb-4', className)}>
            <label className="block mb-1.5 text-sm font-medium text-wabi-text/60">
                {label}
            </label>
            {children}
            {hint && (
                <p className="mt-1 text-xs text-wabi-text/40">{hint}</p>
            )}
        </div>
    );
}

interface InputFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label: string;
    hint?: string;
    fieldClassName?: string;
}

export function InputField({ label, hint, fieldClassName, className, ...props }: InputFieldProps) {
    return (
        <FormField label={label} hint={hint} className={fieldClassName}>
            <input
                className={cn(
                    'w-full px-3 py-2.5 border border-wabi-text/10 rounded-lg',
                    'bg-wabi-bg/50 text-wabi-text text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-wabi-text/15 transition-all',
                    'placeholder:text-wabi-text/30',
                    className,
                )}
                {...props}
            />
        </FormField>
    );
}

interface TextAreaFieldProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    label: string;
    hint?: string;
    fieldClassName?: string;
}

export function TextAreaField({ label, hint, fieldClassName, className, ...props }: TextAreaFieldProps) {
    return (
        <FormField label={label} hint={hint} className={fieldClassName}>
            <textarea
                className={cn(
                    'w-full px-3 py-2.5 border border-wabi-text/10 rounded-lg',
                    'bg-wabi-bg/50 text-wabi-text text-sm resize-y',
                    'focus:outline-none focus:ring-2 focus:ring-wabi-text/15 transition-all',
                    'placeholder:text-wabi-text/30',
                    className,
                )}
                rows={3}
                {...props}
            />
        </FormField>
    );
}
