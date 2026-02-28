'use client';

import { useState } from 'react';
import { InputField } from '@/components/ui/FormField';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { apiFetch, getErrorMessage } from '@/lib/api-client';

export default function CreateBrandForm({ onSuccess }: { onSuccess: () => void }) {
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

    const [formData, setFormData] = useState({
        name: '',
        slug: '',
        category: 'general',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMessage(null);

        try {
            await apiFetch('/admin/brands', {
                method: 'POST',
                body: JSON.stringify(formData),
            });

            setMessage({ text: 'Brand created successfully!', type: 'success' });
            setFormData({ name: '', slug: '', category: 'general' });
            onSuccess();
        } catch (err: unknown) {
            setMessage({ text: getErrorMessage(err, 'Failed to create brand'), type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="flex flex-col gap-1">
            {message && <Alert message={message.text} type={message.type} className="mb-4" />}

            <InputField
                label="Brand Name"
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Acme Beauty"
                required
            />
            <InputField
                label="Brand Slug"
                type="text"
                name="slug"
                value={formData.slug}
                onChange={handleChange}
                placeholder="acme-beauty"
                required
                pattern="[a-z0-9-]+"
                title="Lowercase letters, numbers, and hyphens only"
            />
            <div className="mb-4">
                <label className="block mb-1.5 text-sm font-medium text-wabi-text/60">Category</label>
                <input
                    type="text"
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    required
                    list="brand-category-suggestions"
                    placeholder="general"
                    className="w-full px-3 py-2.5 border border-wabi-text/10 rounded-lg bg-wabi-bg/50 text-wabi-text text-sm focus:outline-none focus:ring-2 focus:ring-wabi-text/15 transition-all placeholder:text-wabi-text/30"
                />
                <datalist id="brand-category-suggestions">
                    <option value="general" />
                    <option value="fashion" />
                    <option value="beauty" />
                    <option value="furniture" />
                    <option value="food" />
                </datalist>
                <p className="mt-1 text-xs text-wabi-text/40">Use any category label; templates are available for common categories.</p>
            </div>

            <Button type="submit" loading={loading} loadingText="Creating..." className="self-start">
                Create Brand
            </Button>
        </form>
    );
}
