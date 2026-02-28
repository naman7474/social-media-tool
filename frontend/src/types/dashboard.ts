export type Brand = {
    id: number;
    name: string;
    slug: string;
    category: string;
    timezone: string;
    telegram_bot_token?: string | null;
    telegram_webhook_secret?: string | null;
    allowed_user_ids?: string | null;
};

export type BrandMetrics = {
    total_posts: number;
    review_ready: number;
    scheduled: number;
    posted: number;
    failed: number;
};

export type OnboardingChecks = {
    telegram_bot_configured: boolean;
    telegram_webhook_secret: boolean;
    meta_credentials_configured: boolean;
};

export type DashboardPayload = {
    brands: Brand[];
    selected_brand: Brand | null;
    brand_metrics?: BrandMetrics | null;
    onboarding_checks?: OnboardingChecks | null;
    is_super_admin: boolean;
    admin_email?: string;
};
