'use client';

import { useState } from 'react';
import { InputField } from '@/components/ui/FormField';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { apiFetch, getErrorMessage } from '@/lib/api-client';

type TelegramConfig = {
    telegram_bot_token?: string | null;
    telegram_webhook_secret?: string | null;
    allowed_user_ids?: string | null;
};

export default function TelegramConfigForm({ brandId, initialConfig }: { brandId: number, initialConfig: TelegramConfig }) {
    const [loading, setLoading] = useState(false);
    const [webhookLoading, setWebhookLoading] = useState(false);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

    const [formData, setFormData] = useState({
        telegram_bot_token: initialConfig.telegram_bot_token ? '***' : '',
        telegram_webhook_secret: initialConfig.telegram_webhook_secret ? '***' : '',
        allowed_user_ids: initialConfig.allowed_user_ids || ''
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMessage(null);

        // Filter out untouched masked inputs
        const payload: Record<string, string> = {};
        if (formData.telegram_bot_token && formData.telegram_bot_token !== '***') {
            payload.telegram_bot_token = formData.telegram_bot_token;
        }
        if (formData.telegram_webhook_secret && formData.telegram_webhook_secret !== '***') {
            payload.telegram_webhook_secret = formData.telegram_webhook_secret;
        }
        payload.allowed_user_ids = formData.allowed_user_ids;

        try {
            await apiFetch(`/admin/brands/${brandId}`, {
                method: 'PUT',
                body: JSON.stringify(payload),
            });

            setMessage({ text: 'Telegram configuration saved successfully!', type: 'success' });
            setFormData(prev => ({
                ...prev,
                telegram_bot_token: prev.telegram_bot_token ? '***' : '',
                telegram_webhook_secret: prev.telegram_webhook_secret ? '***' : '',
            }));
        } catch (err: unknown) {
            setMessage({ text: getErrorMessage(err, 'Failed to update configuration'), type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleSetWebhook = async () => {
        setWebhookLoading(true);
        setMessage(null);

        try {
            const result = await apiFetch<{ message: string }>(`/admin/brands/${brandId}/telegram/webhook/set`, {
                method: 'POST',
            });
            setMessage({ text: `Success: ${result.message}`, type: 'success' });
        } catch (err: unknown) {
            setMessage({ text: getErrorMessage(err, 'Failed to validate webhook'), type: 'error' });
        } finally {
            setWebhookLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="flex flex-col gap-1">
            {message && <Alert message={message.text} type={message.type} className="mb-4" />}

            <InputField
                label="Telegram Bot Token"
                type="password"
                name="telegram_bot_token"
                value={formData.telegram_bot_token}
                onChange={handleChange}
                placeholder="123456789:ABCDefghIJKLmnopQRSTuvwxYZ123456789"
                hint="Leave starting with *** to remain unchanged."
            />
            <InputField
                label="Webhook Secret"
                type="password"
                name="telegram_webhook_secret"
                value={formData.telegram_webhook_secret}
                onChange={handleChange}
                placeholder="super-secret-webhook-key"
            />
            <InputField
                label="Allowed User IDs"
                type="text"
                name="allowed_user_ids"
                value={formData.allowed_user_ids}
                onChange={handleChange}
                placeholder="111222333,444555666"
                hint="Comma-separated Telegram User IDs."
            />

            <div className="flex flex-wrap gap-2 mt-2">
                <Button type="submit" loading={loading} loadingText="Saving..." className="w-fit">
                    Save Configuration
                </Button>

                {(initialConfig.telegram_bot_token) && (
                    <Button
                        type="button"
                        variant="secondary"
                        onClick={handleSetWebhook}
                        loading={webhookLoading}
                        loadingText="Validating..."
                        className="w-fit"
                    >
                        Validate & Set Webhook
                    </Button>
                )}
            </div>
        </form>
    );
}
