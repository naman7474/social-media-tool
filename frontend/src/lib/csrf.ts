export function getCsrfToken(): string {
    if (typeof document === 'undefined') return '';

    // Read CSRF token from cookie only — never localStorage
    const value = `; ${document.cookie}`;
    const parts = value.split(`; admin_csrf=`);
    if (parts.length === 2) {
        const rawToken = parts.pop()?.split(';').shift() || '';
        return decodeURIComponent(rawToken);
    }
    return '';
}
