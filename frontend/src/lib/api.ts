const FALLBACK_API_BASE = "http://localhost:8000";

export function getApiBaseUrl(): string {
    const raw = process.env.NEXT_PUBLIC_API_BASE_URL || FALLBACK_API_BASE;
    return raw.replace(/\/+$/, "");
}

export function apiUrl(path: string): string {
    const normalizedPath = path.startsWith("/") ? path : `/${path}`;
    return `${getApiBaseUrl()}${normalizedPath}`;
}
