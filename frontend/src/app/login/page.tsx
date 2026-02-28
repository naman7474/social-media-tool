'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FadeIn } from '@/components/FadeIn';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch, getErrorMessage } from '@/lib/api-client';

export default function LoginPage() {
    const router = useRouter();
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setMessage(null);

        const endpoint = isLogin ? '/admin/auth/login' : '/admin/auth/bootstrap';

        try {
            await apiFetch(endpoint, {
                method: 'POST',
                body: JSON.stringify({ email, password }),
            });

            setMessage(isLogin ? 'Login successful!' : 'Bootstrap successful! You can now login.');

            if (isLogin) {
                setTimeout(() => router.push('/dashboard'), 500);
            } else {
                setIsLogin(true);
                setPassword('');
            }
        } catch (err: unknown) {
            setError(getErrorMessage(err, 'Authentication failed'));
        }
    };

    return (
        <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-wabi-bg text-wabi-text selection:bg-wabi-text selection:text-wabi-bg">
            <FadeIn yOffset={20} duration={0.8} className="w-full max-w-sm">
                <div className="text-center mb-10">
                    <h1 className="font-serif text-3xl mb-2 tracking-tight">VÂK</h1>
                    <p className="text-sm font-light text-wabi-text/60">Control Room Access</p>
                </div>

                <div className="bg-white/40 p-8 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] backdrop-blur-xl border border-white/60">
                    <AnimatePresence mode="wait">
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mb-6 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 text-center"
                            >
                                {error}
                            </motion.div>
                        )}
                        {message && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mb-6 p-3 bg-green-50 text-green-700 text-sm rounded-lg border border-green-100 text-center"
                            >
                                {message}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-1.5">
                            <label htmlFor="email" className="block text-xs font-medium text-wabi-text/70 uppercase tracking-wider">
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="name@example.com"
                                className="w-full px-4 py-3 bg-white/50 border border-wabi-text/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-wabi-text/20 transition-all font-light placeholder:text-wabi-text/30"
                                required
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label htmlFor="password" className="block text-xs font-medium text-wabi-text/70 uppercase tracking-wider">
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className="w-full px-4 py-3 bg-white/50 border border-wabi-text/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-wabi-text/20 transition-all font-light placeholder:text-wabi-text/30"
                                required
                                minLength={isLogin ? 8 : 10}
                            />
                        </div>

                        <button
                            type="submit"
                            className="w-full py-3.5 mt-2 bg-wabi-text text-wabi-bg rounded-lg font-medium hover:bg-wabi-text/90 transition-colors shadow-lg shadow-wabi-text/10 active:scale-[0.98]"
                        >
                            {isLogin ? 'Sign In' : 'Create Super Admin'}
                        </button>
                    </form>

                    <div className="mt-8 text-center">
                        <button
                            type="button"
                            className="text-xs text-wabi-text/50 hover:text-wabi-text transition-colors"
                            onClick={() => setIsLogin(!isLogin)}
                        >
                            {isLogin ? 'Need initial bootstrap?' : 'Back to login'}
                        </button>
                    </div>
                </div>
            </FadeIn>
        </main>
    );
}
