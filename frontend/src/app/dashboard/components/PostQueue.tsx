'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { SectionCard } from '@/components/ui/SectionCard';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { apiFetch, getErrorMessage } from '@/lib/api-client';

type VariantRow = {
    variant_index: number;
    preview_url: string;
};

type PostRow = {
    id: number;
    status: string;
    media_type: string;
    created_at: string;
    scheduled_for?: string | null;
    caption?: string | null;
    error_code?: string | null;
    error_message?: string | null;
    variants?: VariantRow[];
};

type PostResponse = {
    posts?: PostRow[];
};

function StatusBadge({ status }: { status: string }) {
    const s = status.toLowerCase();
    const colors =
        s === 'posted'
            ? 'bg-green-50 text-green-700 border-green-200'
            : s === 'failed'
                ? 'bg-red-50 text-red-600 border-red-200'
                : 'bg-blue-50 text-blue-700 border-blue-200';

    return (
        <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors}`}>
            {status || '-'}
        </span>
    );
}

export default function PostQueue({ brandId }: { brandId: number }) {
    const [posts, setPosts] = useState<PostRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [actionError, setActionError] = useState<string | null>(null);
    const [scheduleInput, setScheduleInput] = useState<Record<number, string>>({});

    const fetchPosts = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const json = await apiFetch<PostResponse>(`/admin/posts?brand_id=${brandId}`);
            setPosts(json.posts || []);
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to fetch posts'));
        } finally {
            setLoading(false);
        }
    }, [brandId]);

    useEffect(() => {
        fetchPosts();
    }, [fetchPosts]);

    const timezone = useMemo(
        () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
        [],
    );

    const handlePublish = async (postId: number) => {
        setActionError(null);
        try {
            await apiFetch(`/admin/posts/${postId}/publish`, {
                method: 'POST',
                body: JSON.stringify({}),
            });
            await fetchPosts();
        } catch (err) {
            setActionError(getErrorMessage(err, 'Failed to publish'));
        }
    };

    const handleSchedule = async (postId: number) => {
        setActionError(null);
        const rawValue = scheduleInput[postId];
        if (!rawValue) {
            setActionError('Pick a date/time first.');
            return;
        }
        const asIso = new Date(rawValue).toISOString();
        try {
            await apiFetch(`/admin/posts/${postId}/schedule`, {
                method: 'POST',
                body: JSON.stringify({ scheduled_for: asIso, scheduled_timezone: timezone }),
            });
            await fetchPosts();
        } catch (err) {
            setActionError(getErrorMessage(err, 'Failed to schedule'));
        }
    };

    if (loading) {
        return <div className="mt-6 text-wabi-text/40 animate-pulse">Loading posts...</div>;
    }
    if (error) {
        return <Alert message={error} type="error" className="mt-6" />;
    }

    return (
        <SectionCard
            title="Post Queue"
            description="Review, schedule, and publish generated content."
            headerRight={
                <Button variant="secondary" onClick={fetchPosts} className="text-xs px-3 py-1.5">
                    Refresh
                </Button>
            }
        >
            {actionError && <Alert message={actionError} type="error" className="mb-4" />}

            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead>
                        <tr className="border-b border-wabi-text/10 text-wabi-text/60">
                            <th className="px-3 py-2 font-semibold">ID</th>
                            <th className="px-3 py-2 font-semibold">Status</th>
                            <th className="px-3 py-2 font-semibold">Type</th>
                            <th className="px-3 py-2 font-semibold">Summary</th>
                            <th className="px-3 py-2 font-semibold">Created</th>
                            <th className="px-3 py-2 font-semibold">Scheduled</th>
                            <th className="px-3 py-2 font-semibold text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {posts.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="text-center py-8 text-wabi-text/40">
                                    No posts found for this brand.
                                </td>
                            </tr>
                        ) : (
                            posts.map((post) => {
                                const status = (post.status || '').toLowerCase();
                                const canPublish = ['review_ready', 'approved', 'scheduled'].includes(status);
                                const canSchedule = ['review_ready', 'approved'].includes(status);
                                const captionPreview = (post.caption || '').trim().slice(0, 80);
                                return (
                                    <tr key={post.id} className="border-b border-wabi-text/5">
                                        <td className="px-3 py-3">#{post.id}</td>
                                        <td className="px-3 py-3">
                                            <StatusBadge status={status} />
                                        </td>
                                        <td className="px-3 py-3">{post.media_type || 'single'}</td>
                                        <td className="px-3 py-3 max-w-[260px]">
                                            {status === 'failed' ? (
                                                <span className="text-red-600">
                                                    {post.error_code || 'failed'}: {post.error_message || 'Unknown error'}
                                                </span>
                                            ) : captionPreview ? (
                                                <span className="text-wabi-text/60">
                                                    {captionPreview}{(post.caption || '').length > 80 ? '…' : ''}
                                                </span>
                                            ) : (
                                                <span className="text-wabi-text/40">No caption yet</span>
                                            )}
                                            {post.variants && post.variants.length > 0 && (
                                                <div className="mt-1 text-xs text-wabi-text/40">
                                                    {post.variants.length} option{post.variants.length > 1 ? 's' : ''}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-3 py-3 text-wabi-text/60 text-xs">
                                            {new Date(post.created_at).toLocaleString()}
                                        </td>
                                        <td className="px-3 py-3 text-xs">
                                            {post.scheduled_for ? new Date(post.scheduled_for).toLocaleString() : '-'}
                                        </td>
                                        <td className="px-3 py-3 text-right min-w-[220px]">
                                            <div className="flex flex-col gap-2 items-end">
                                                {canPublish && (
                                                    <Button
                                                        onClick={() => handlePublish(post.id)}
                                                        className="text-xs px-3 py-1.5"
                                                    >
                                                        Publish Now
                                                    </Button>
                                                )}
                                                {canSchedule && (
                                                    <div className="flex gap-2 items-center">
                                                        <input
                                                            type="datetime-local"
                                                            value={scheduleInput[post.id] || ''}
                                                            onChange={(event) =>
                                                                setScheduleInput((prev) => ({ ...prev, [post.id]: event.target.value }))
                                                            }
                                                            className="border border-wabi-text/10 rounded-lg px-2 py-1 bg-white text-sm"
                                                        />
                                                        <Button
                                                            variant="secondary"
                                                            onClick={() => handleSchedule(post.id)}
                                                            className="text-xs px-3 py-1.5"
                                                        >
                                                            Schedule
                                                        </Button>
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>
        </SectionCard>
    );
}
