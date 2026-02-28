'use client';

import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/api-client';

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();

    const handleLogout = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await apiFetch('/admin/auth/logout', { method: 'POST' });
            router.push('/login');
        } catch (err) {
            console.error('Logout failed', err);
        }
    };

    return (
        <div className="min-h-screen bg-wabi-bg text-wabi-text font-sans flex flex-col selection:bg-wabi-text selection:text-wabi-bg">
            <header className="sticky top-0 z-40 bg-white/70 backdrop-blur-xl border-b border-wabi-text/5 px-8 py-5 flex items-center justify-between">
                <div>
                    <h1 className="font-serif text-2xl tracking-tight">Agency Control Room</h1>
                </div>
                <div className="flex items-center gap-6">
                    <form onSubmit={handleLogout}>
                        <button type="submit" className="text-sm font-medium hover:opacity-60 transition-opacity">
                            Log out
                        </button>
                    </form>
                </div>
            </header>

            <div className="flex-1 flex px-6 py-8 max-w-[1600px] w-full mx-auto">
                {children}
            </div>
        </div>
    );
}
