'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import CredentialsForm from './components/CredentialsForm';
import PostQueue from './components/PostQueue';
import AiProfileEditor from './components/AiProfileEditor';
import CreateBrandForm from './components/CreateBrandForm';
import TelegramConfigForm from './components/TelegramConfigForm';
import { FadeIn } from '@/components/FadeIn';
import { SectionCard } from '@/components/ui/SectionCard';
import { apiFetch, getErrorMessage } from '@/lib/api-client';
import type { Brand, DashboardPayload } from '@/types/dashboard';

function DashboardContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [data, setData] = useState<DashboardPayload | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const activeBrandId = searchParams.get('brand_id');

    const fetchDashboardData = useCallback(async (brandId: string | null) => {
        setLoading(true);
        setError(null);
        try {
            const queryStr = brandId ? `?brand_id=${brandId}` : '';
            const json = await apiFetch<DashboardPayload>(`/admin/api/dashboard${queryStr}`);
            setData(json);
        } catch (err: unknown) {
            if (err instanceof Error && 'status' in err && ((err as Error & { status: number }).status === 401 || (err as Error & { status: number }).status === 403)) {
                router.push('/login');
                return;
            }
            setError(getErrorMessage(err, 'Failed to view dashboard'));
        } finally {
            setLoading(false);
        }
    }, [router]);

    useEffect(() => {
        void fetchDashboardData(activeBrandId);
    }, [activeBrandId, fetchDashboardData]);

    if (loading) return <div className="p-8 text-center text-wabi-text/50 animate-pulse w-full">Loading dashboard...</div>;
    if (error) return <div className="p-8 text-red-600 bg-red-50 rounded-xl m-8 border border-red-100 w-full">{error}</div>;
    if (!data) return null;

    const {
        brands,
        selected_brand: brand,
        brand_metrics: metrics,
        onboarding_checks: checks,
    } = data;

    return (
        <div className="flex flex-col lg:flex-row gap-8 w-full">
            <aside className="w-full lg:w-80 flex-shrink-0 flex flex-col gap-6">
                <FadeIn yOffset={10} duration={0.6}>
                    <SectionCard title="Select Brand" description="Choose which client account you want to manage.">
                        <div className="flex flex-col gap-2">
                            {brands?.map((b: Brand) => (
                                <div
                                    key={b.id}
                                    onClick={() => router.push(`/dashboard?brand_id=${b.id}`)}
                                    className={`p-3 rounded-xl cursor-pointer transition-all ${brand?.id === b.id
                                        ? 'bg-wabi-text text-wabi-bg shadow-md scale-[1.02]'
                                        : 'bg-white hover:bg-white/80 border border-wabi-text/5 text-wabi-text hover:border-wabi-text/20'
                                        }`}
                                >
                                    <div className="font-semibold">{b.name}</div>
                                    <div className={`text-xs mt-1 ${brand?.id === b.id ? 'text-wabi-bg/70' : 'text-wabi-text/50'}`}>
                                        {b.slug} &bull; {b.category}
                                    </div>
                                </div>
                            ))}
                            {(!brands || brands.length === 0) && (
                                <div className="text-sm text-wabi-text/40 text-center py-4">No brands available</div>
                            )}
                        </div>
                    </SectionCard>
                </FadeIn>

                {data.is_super_admin && (
                    <FadeIn delay={0.1} yOffset={10} duration={0.6}>
                        <SectionCard title="Create New Brand" description="Use this once per client account.">
                            <CreateBrandForm onSuccess={() => fetchDashboardData(activeBrandId)} />
                        </SectionCard>
                    </FadeIn>
                )}
            </aside>

            <section className="flex-1 flex flex-col gap-8 min-w-0">
                {brand ? (
                    <>
                        <FadeIn yOffset={15} duration={0.7}>
                            <SectionCard>
                                <div className="mb-8 pb-6 border-b border-wabi-text/5">
                                    <h2 className="text-3xl font-serif font-bold tracking-tight">{brand.name}</h2>
                                    <div className="flex gap-3 items-center mt-3 text-sm text-wabi-text/60">
                                        <span className="bg-white px-2 py-1 rounded-md border border-wabi-text/5">{brand.slug}</span>
                                        <span>&bull;</span>
                                        <span>{brand.category}</span>
                                        <span>&bull;</span>
                                        <span>{brand.timezone}</span>
                                    </div>
                                </div>

                                {metrics && (
                                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                                        {[
                                            { label: 'Total Posts', value: metrics.total_posts },
                                            { label: 'Ready', value: metrics.review_ready },
                                            { label: 'Scheduled', value: metrics.scheduled },
                                            { label: 'Posted', value: metrics.posted, color: 'text-green-600' },
                                            { label: 'Failed', value: metrics.failed, color: 'text-red-600' }
                                        ].map((m, i) => (
                                            <div key={i} className="bg-white rounded-xl border border-wabi-text/5 p-5 flex flex-col items-center justify-center shadow-sm">
                                                <span className="text-xs font-medium text-wabi-text/50 uppercase tracking-wider">{m.label}</span>
                                                <span className={`text-3xl font-bold mt-2 ${m.color || 'text-wabi-text'}`}>{m.value}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </SectionCard>
                        </FadeIn>

                        <FadeIn delay={0.1} yOffset={15} duration={0.7}>
                            <SectionCard title="Onboarding Checklist">
                                <div className="flex flex-col gap-3">
                                    {[
                                        { label: 'Telegram Bot Token', status: checks?.telegram_bot_configured },
                                        { label: 'Webhook Secret', status: checks?.telegram_webhook_secret },
                                        { label: 'Meta Credentials', status: checks?.meta_credentials_configured }
                                    ].map((check, i) => (
                                        <div key={i} className={`flex justify-between items-center p-4 rounded-xl text-sm font-medium border ${check.status
                                            ? 'bg-green-50/50 text-green-700 border-green-200'
                                            : 'bg-red-50/50 text-red-600 border-red-200'
                                            }`}>
                                            <span>{check.label}</span>
                                            <span className="bg-white/50 px-3 py-1 rounded-full text-xs border border-current/10">
                                                {check.status ? 'Configured' : 'Missing'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </SectionCard>
                        </FadeIn>

                        {/* Components */}
                        <FadeIn delay={0.2} yOffset={20} duration={0.8}>
                            <div className="space-y-8">
                                <AiProfileEditor brandId={brand.id} />
                                <CredentialsForm brandId={brand.id} />
                                <SectionCard title="Telegram Configuration" description="Configure your Telegram bot integration.">
                                    <TelegramConfigForm brandId={brand.id} initialConfig={{
                                        telegram_bot_token: brand.telegram_bot_token,
                                        telegram_webhook_secret: brand.telegram_webhook_secret,
                                        allowed_user_ids: brand.allowed_user_ids
                                    }} />
                                </SectionCard>
                                <PostQueue brandId={brand.id} />
                            </div>
                        </FadeIn>
                    </>
                ) : (
                    <FadeIn>
                        <SectionCard className="p-16 text-center">
                            <h3 className="text-2xl font-serif mb-2">No Active Brand</h3>
                            <p className="text-wabi-text/50">Select a brand from the sidebar to view details.</p>
                        </SectionCard>
                    </FadeIn>
                )}
            </section>
        </div>
    );
}

export default function DashboardPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center text-wabi-text/50 animate-pulse w-full">Loading dashboard...</div>}>
            <DashboardContent />
        </Suspense>
    );
}
