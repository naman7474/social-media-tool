'use client';

import { useState } from 'react';
import { InputField } from '@/components/ui/FormField';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SectionCard } from '@/components/ui/SectionCard';
import { apiFetch, getErrorMessage } from '@/lib/api-client';

export default function CredentialsForm({ brandId }: { brandId: number }) {
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

    const [formData, setFormData] = useState({
        meta_app_id: '',
        meta_app_secret: '',
        meta_page_access_token: '',
        instagram_business_account_id: '',
        meta_graph_api_version: 'v25.0'
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMessage(null);

        try {
            await apiFetch(`/admin/brands/${brandId}/credentials`, {
                method: 'POST',
                body: JSON.stringify(formData),
            });

            setMessage({ text: 'Credentials saved successfully!', type: 'success' });
            setFormData({
                meta_app_id: '',
                meta_app_secret: '',
                meta_page_access_token: '',
                instagram_business_account_id: '',
                meta_graph_api_version: 'v25.0'
            });
        } catch (err: unknown) {
            setMessage({ text: getErrorMessage(err, 'Failed to save credentials'), type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <SectionCard title="Meta Credentials" description="Configure your Instagram and Meta API access.">
            {message && <Alert message={message.text} type={message.type} className="mb-6" />}

            <form onSubmit={handleSubmit} className="flex flex-col gap-1">
                <InputField
                    label="Meta App ID"
                    type="text"
                    name="meta_app_id"
                    value={formData.meta_app_id}
                    onChange={handleChange}
                    required
                    placeholder="e.g. 1234567890"
                />
                <InputField
                    label="Meta App Secret"
                    type="password"
                    name="meta_app_secret"
                    value={formData.meta_app_secret}
                    onChange={handleChange}
                    required
                    placeholder="••••••••••••••••"
                />
                <InputField
                    label="Page Access Token"
                    type="password"
                    name="meta_page_access_token"
                    value={formData.meta_page_access_token}
                    onChange={handleChange}
                    required
                    placeholder="EAA..."
                />
                <InputField
                    label="Instagram Business Account ID"
                    type="text"
                    name="instagram_business_account_id"
                    value={formData.instagram_business_account_id}
                    onChange={handleChange}
                    required
                    placeholder="e.g. 17841412345"
                />
                <InputField
                    label="Graph API Version"
                    type="text"
                    name="meta_graph_api_version"
                    value={formData.meta_graph_api_version}
                    onChange={handleChange}
                    required
                />

                <div className="mt-4 pt-4 border-t border-wabi-text/5">
                    <Button type="submit" loading={loading} loadingText="Saving...">
                        Save Credentials
                    </Button>
                </div>
            </form>
        </SectionCard>
    );
}
