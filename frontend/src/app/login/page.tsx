'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FadeIn } from '@/components/FadeIn';
import { apiFetch, getErrorMessage } from '@/lib/api-client';
import { SectionCard } from '@/components/ui/SectionCard';
import { InputField } from '@/components/ui/FormField';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';

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
                <div className="text-center mb-8">
                    <h1 className="font-serif text-4xl mb-2 tracking-tight">VÂK</h1>
                    <p className="text-sm font-light text-wabi-text/60 uppercase tracking-widest">Control Room Access</p>
                </div>

                <SectionCard className="p-8">
                    <div className="mb-6 space-y-3">
                        {error && <Alert type="error" message={error} />}
                        {message && <Alert type="success" message={message} />}
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <InputField
                            label="Email"
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@example.com"
                            required
                        />

                        <InputField
                            label="Password"
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            required
                            minLength={isLogin ? 8 : 10}
                        />

                        <div className="pt-2">
                            <Button
                                type="submit"
                                className="w-full"
                            >
                                {isLogin ? 'Sign In' : 'Create Super Admin'}
                            </Button>
                        </div>
                    </form>

                    <div className="mt-6 text-center">
                        <button
                            type="button"
                            className="text-xs text-wabi-text/50 hover:text-wabi-text transition-colors"
                            onClick={() => setIsLogin(!isLogin)}
                        >
                            {isLogin ? 'Need initial bootstrap?' : 'Back to login'}
                        </button>
                    </div>
                </SectionCard>
            </FadeIn>
        </main>
    );
}
