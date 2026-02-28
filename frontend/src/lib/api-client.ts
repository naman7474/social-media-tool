import { apiUrl } from './api';
import { getCsrfToken } from './csrf';

export type ApiError = {
    message: string;
    status: number;
};

/**
 * Shared fetch wrapper that auto-injects CSRF headers, includes credentials,
 * parses JSON responses, and provides consistent error handling.
 */
export async function apiFetch<T = unknown>(
    path: string,
    options: RequestInit = {},
): Promise<T> {
    const { headers: customHeaders, ...rest } = options;

    const headers: Record<string, string> = {
        ...(customHeaders as Record<string, string>),
    };

    // Auto-inject CSRF for mutating methods
    const method = (rest.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        headers['X-CSRF-Token'] = getCsrfToken();
        if (!headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
    }

    const res = await fetch(apiUrl(path), {
        ...rest,
        headers,
        credentials: 'include',
    });

    const json = await res.json().catch(() => ({}));

    if (!res.ok) {
        const message = (json as { detail?: string }).detail
            || `Request failed (${res.status})`;
        const err = new Error(message) as Error & { status: number };
        err.status = res.status;
        throw err;
    }

    return json as T;
}

/**
 * Extract error message from unknown thrown value.
 */
export function getErrorMessage(err: unknown, fallback: string): string {
    return err instanceof Error ? err.message : fallback;
}
