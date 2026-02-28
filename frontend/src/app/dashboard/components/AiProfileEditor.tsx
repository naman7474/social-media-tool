'use client';

import { useCallback, useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { SectionCard } from '@/components/ui/SectionCard';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { apiFetch, getErrorMessage } from '@/lib/api-client';

// ── JSON helpers ──

type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
type JsonObject = { [key: string]: JsonValue };

function isJsonObject(value: unknown): value is JsonObject {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

// ── Inline field components (Tailwind-only) ──

const inputClasses =
    'w-full px-3 py-2.5 border border-wabi-text/10 rounded-lg bg-wabi-bg/50 text-wabi-text text-sm focus:outline-none focus:ring-2 focus:ring-wabi-text/15 transition-all placeholder:text-wabi-text/30';

const labelClasses = 'block mb-1.5 text-sm font-medium text-wabi-text/60';

function TextInput({ label, value, onChange, placeholder = '' }: {
    label: string; value?: JsonValue; onChange: (val: string) => void; placeholder?: string;
}) {
    const inputValue = typeof value === 'string' || typeof value === 'number' ? value : '';
    return (
        <div className="mb-4">
            <label className={labelClasses}>{label}</label>
            <input
                type="text"
                className={inputClasses}
                value={inputValue}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
            />
        </div>
    );
}

function TextArea({ label, value, onChange, placeholder = '', rows = 3 }: {
    label: string; value?: JsonValue; onChange: (val: string) => void; placeholder?: string; rows?: number;
}) {
    const textValue = typeof value === 'string' || typeof value === 'number' ? value : '';
    return (
        <div className="mb-4">
            <label className={labelClasses}>{label}</label>
            <textarea
                className={cn(inputClasses, 'resize-y')}
                value={textValue}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                rows={rows}
            />
        </div>
    );
}

function ArrayInput({ label, value, onChange, placeholder = 'Enter comma separated values' }: {
    label: string; value?: JsonValue; onChange: (val: string[]) => void; placeholder?: string;
}) {
    const strValue = Array.isArray(value) ? value.join(', ') : (value || '');
    const handleChange = (val: string) => {
        const arr = val.split(',').map(s => s.trim()).filter(Boolean);
        onChange(arr);
    };
    return <TextArea label={label} value={strValue} onChange={handleChange} placeholder={placeholder} rows={3} />;
}

function DictInput({ label, value, onChange, placeholder = 'key: value\nkey: value' }: {
    label: string; value?: JsonValue; onChange: (val: Record<string, string>) => void; placeholder?: string;
}) {
    const strValue = isJsonObject(value) ? Object.entries(value).map(([k, v]) => `${k}: ${String(v)}`).join('\n') : '';
    const handleChange = (val: string) => {
        const lines = val.split('\n');
        const obj: Record<string, string> = {};
        lines.forEach(line => {
            const idx = line.indexOf(':');
            if (idx > -1) {
                const k = line.slice(0, idx).trim();
                const v = line.slice(idx + 1).trim();
                if (k && v) obj[k] = v;
            }
        });
        onChange(obj);
    };
    return (
        <div className="mb-4">
            <label className={labelClasses}>
                {label} <span className="text-[11px] font-normal text-wabi-text/40">(Format as Key: Value)</span>
            </label>
            <textarea
                className={cn(inputClasses, 'resize-y font-mono')}
                value={strValue}
                onChange={(e) => handleChange(e.target.value)}
                placeholder={placeholder}
                rows={4}
            />
        </div>
    );
}

// ── Tab definitions ──

const tabs = [
    { id: 'basics', label: 'Basics & Voice' },
    { id: 'visuals', label: 'Visuals & Props' },
    { id: 'colors_typo', label: 'Colors & Typography' },
    { id: 'styles_context', label: 'Styles & Parts' },
    { id: 'occasions_cta', label: 'Occasions & Formats' },
    { id: 'captions', label: 'Captions & Tags' },
    { id: 'advanced', label: 'Advanced JSON' },
];

// ── Main component ──

export default function AiProfileEditor({ brandId }: { brandId: number }) {
    const [rawConfig, setRawConfig] = useState<string>('');
    const [configObj, setConfigObj] = useState<JsonObject>({});
    const [category, setCategory] = useState<string>('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
    const [activeTab, setActiveTab] = useState('basics');

    const fetchConfig = useCallback(async () => {
        setLoading(true);
        setMessage(null);
        try {
            const json = await apiFetch<{ category?: string; config?: unknown }>(`/admin/api/brands/${brandId}/ai-config`);
            setCategory(json.category || 'general');
            const data = isJsonObject(json.config) ? json.config : {};
            setConfigObj(data);
            setRawConfig(JSON.stringify(data, null, 2));
        } catch (err: unknown) {
            setMessage({ text: getErrorMessage(err, 'Failed to fetch AI configuration'), type: 'error' });
        } finally {
            setLoading(false);
        }
    }, [brandId]);

    useEffect(() => {
        void fetchConfig();
    }, [fetchConfig]);

    const handleSave = async () => {
        setSaving(true);
        setMessage(null);
        try {
            let payload = configObj;
            if (activeTab === 'advanced') {
                const parsed = JSON.parse(rawConfig) as unknown;
                if (!isJsonObject(parsed)) throw new Error('Invalid JSON object');
                payload = parsed;
                setConfigObj(payload);
            }

            const json = await apiFetch<{ config?: unknown }>(`/admin/api/brands/${brandId}/ai-config`, {
                method: 'PUT',
                body: JSON.stringify({ config: payload }),
            });

            if (json.config) {
                const returnedConfig = isJsonObject(json.config) ? json.config : {};
                setConfigObj(returnedConfig);
                setRawConfig(JSON.stringify(returnedConfig, null, 2));
            }

            setMessage({ text: 'AI Profile configuration saved successfully.', type: 'success' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err: unknown) {
            const rawMessage = getErrorMessage(err, 'Failed to save configuration');
            const msg = rawMessage.includes('JSON')
                ? 'Invalid JSON format. Please check for syntax errors in Advanced mode.'
                : rawMessage;
            setMessage({ text: msg, type: 'error' });
        } finally {
            setSaving(false);
        }
    };

    const updateField = (path: string[], value: JsonValue) => {
        setConfigObj((prev) => {
            const next = JSON.parse(JSON.stringify(prev)) as JsonObject;
            let current = next;
            for (let i = 0; i < path.length - 1; i++) {
                const segment = current[path[i]];
                if (!isJsonObject(segment)) current[path[i]] = {};
                current = current[path[i]] as JsonObject;
            }
            current[path[path.length - 1]] = value;
            setRawConfig(JSON.stringify(next, null, 2));
            return next;
        });
    };

    if (loading) {
        return <div className="mt-6 text-center text-wabi-text/40 py-10 animate-pulse">Loading AI Profile...</div>;
    }

    // Extract nested objects safely
    const brand = isJsonObject(configObj.brand) ? configObj.brand : {};
    const productVocabulary = isJsonObject(configObj.product_vocabulary) ? configObj.product_vocabulary : {};
    const visualIdentity = isJsonObject(configObj.visual_identity) ? configObj.visual_identity : {};
    const propsLibrary = isJsonObject(configObj.props_library) ? configObj.props_library : {};
    const captionRules = isJsonObject(configObj.caption_rules) ? configObj.caption_rules : {};
    const hashtags = isJsonObject(configObj.hashtags) ? configObj.hashtags : {};
    const colors = isJsonObject(configObj.colors) ? configObj.colors : {};
    const typography = isJsonObject(configObj.typography) ? configObj.typography : {};
    const occasions = isJsonObject(configObj.occasions) ? configObj.occasions : {};

    return (
        <SectionCard
            title="AI Profile Configuration"
            description="Fine-tune the AI instructions and brand guidelines."
            badge={`Category: ${category}`}
        >
            {/* Tab Navigation */}
            <div className="flex border-b border-wabi-text/10 mt-5 gap-1 overflow-x-auto">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={cn(
                            'px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-all rounded-t-md border-b-2',
                            activeTab === tab.id
                                ? 'border-wabi-text text-wabi-text'
                                : 'border-transparent text-wabi-text/50 hover:text-wabi-text/80 hover:bg-wabi-text/[0.03]',
                        )}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {message && <Alert message={message.text} type={message.type} className="mt-4" />}

            <div className="mt-6">
                {activeTab === 'basics' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Brand Identity</h4>
                            <TextInput label="Preferred Language" value={configObj.language} onChange={(val) => updateField(['language'], val)} placeholder="en" />
                            <TextInput label="Brand Tagline" value={brand.tagline} onChange={(val) => updateField(['brand', 'tagline'], val)} />
                            <TextInput label="Brand Website" value={brand.website} onChange={(val) => updateField(['brand', 'website'], val)} placeholder="https://example.com" />
                            <TextInput label="Brand Instagram" value={brand.instagram} onChange={(val) => updateField(['brand', 'instagram'], val)} placeholder="@example" />
                            <TextArea label="Audience Profile" value={configObj.audience_profile} onChange={(val) => updateField(['audience_profile'], val)} rows={4} />
                            <TextArea label="Brand Voice" value={configObj.brand_voice} onChange={(val) => updateField(['brand_voice'], val)} rows={4} />
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Vocabulary & Guidelines</h4>
                            <TextInput label="Product (Singular)" value={productVocabulary.singular} onChange={(val) => updateField(['product_vocabulary', 'singular'], val)} />
                            <TextInput label="Product (Plural)" value={productVocabulary.plural} onChange={(val) => updateField(['product_vocabulary', 'plural'], val)} />
                            <TextInput label="Featured Part" value={productVocabulary.featured_part} onChange={(val) => updateField(['product_vocabulary', 'featured_part'], val)} />
                            <TextArea label="LLM Guardrails" value={configObj.llm_guardrails} onChange={(val) => updateField(['llm_guardrails'], val)} rows={4} />
                        </div>
                    </div>
                )}

                {activeTab === 'visuals' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Visual Identity</h4>
                            <TextInput label="Grid Aesthetic" value={visualIdentity.grid_aesthetic} onChange={(val) => updateField(['visual_identity', 'grid_aesthetic'], val)} />
                            <TextInput label="Dominant Mood" value={visualIdentity.dominant_mood} onChange={(val) => updateField(['visual_identity', 'dominant_mood'], val)} />
                            <ArrayInput label="Prefer in Visuals" value={visualIdentity.prefer} onChange={(val) => updateField(['visual_identity', 'prefer'], val)} />
                            <ArrayInput label="Avoid in Visuals" value={visualIdentity.avoid} onChange={(val) => updateField(['visual_identity', 'avoid'], val)} />
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Props Library</h4>
                            <ArrayInput label="Warm Props" value={propsLibrary.warm} onChange={(val) => updateField(['props_library', 'warm'], val)} />
                            <ArrayInput label="Minimal Props" value={propsLibrary.minimal} onChange={(val) => updateField(['props_library', 'minimal'], val)} />
                            <ArrayInput label="Luxe Props" value={propsLibrary.luxe} onChange={(val) => updateField(['props_library', 'luxe'], val)} />
                            <ArrayInput label="Never Use Props" value={propsLibrary.never_use} onChange={(val) => updateField(['props_library', 'never_use'], val)} />
                        </div>
                    </div>
                )}

                {activeTab === 'captions' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Caption Rules</h4>
                            <TextInput label="Optimal Length (e.g., Short, Medium)" value={captionRules.optimal_length} onChange={(val) => updateField(['caption_rules', 'optimal_length'], val)} />
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <TextInput label="Max Length (Chars)" value={captionRules.max_length} onChange={(val) => updateField(['caption_rules', 'max_length'], parseInt(val) || val)} />
                                </div>
                                <div className="flex-1">
                                    <TextInput label="Emoji Limit" value={captionRules.emoji_limit} onChange={(val) => updateField(['caption_rules', 'emoji_limit'], parseInt(val) || val)} />
                                </div>
                            </div>
                            <ArrayInput label="Must Mention" value={captionRules.must_mention} onChange={(val) => updateField(['caption_rules', 'must_mention'], val)} />
                            <ArrayInput label="Banned Words" value={captionRules.banned_words} onChange={(val) => updateField(['caption_rules', 'banned_words'], val)} placeholder="E.g. buy now, click here" />
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Hashtags</h4>
                            <ArrayInput label="Brand Always (e.g. #MyBrand)" value={hashtags.brand_always} onChange={(val) => updateField(['hashtags', 'brand_always'], val)} />
                            <ArrayInput label="Product Hashtags" value={hashtags.product} onChange={(val) => updateField(['hashtags', 'product'], val)} />
                            <ArrayInput label="Discovery Hashtags" value={hashtags.discovery} onChange={(val) => updateField(['hashtags', 'discovery'], val)} />
                            <ArrayInput label="Never Use Hashtags" value={hashtags.never_use} onChange={(val) => updateField(['hashtags', 'never_use'], val)} />
                        </div>
                    </div>
                )}

                {activeTab === 'colors_typo' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Color Palette</h4>
                            <DictInput label="Primary Colors" value={colors.primary} onChange={(val) => updateField(['colors', 'primary'], val)} placeholder={"charcoal: #2C2C2C\ncream: #F5F0E8"} />
                            <DictInput label="Secondary Colors" value={colors.secondary} onChange={(val) => updateField(['colors', 'secondary'], val)} />
                            <DictInput label="Accent Colors" value={colors.accent} onChange={(val) => updateField(['colors', 'accent'], val)} />
                            <DictInput label="Usage Rules (Key/Value mappings)" value={colors.usage_rules} onChange={(val) => updateField(['colors', 'usage_rules'], val)} />
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Typography Rules</h4>
                            <TextInput label="Heading Feel" value={typography.heading_feel} onChange={(val) => updateField(['typography', 'heading_feel'], val)} />
                            <TextInput label="Body Feel" value={typography.body_feel} onChange={(val) => updateField(['typography', 'body_feel'], val)} />
                            <TextInput label="Overlay Feel" value={typography.overlay_feel} onChange={(val) => updateField(['typography', 'overlay_feel'], val)} />
                            <ArrayInput label="Typography Rules" value={typography.rules} onChange={(val) => updateField(['typography', 'rules'], val)} />
                        </div>
                    </div>
                )}

                {activeTab === 'styles_context' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Display Styles Library</h4>
                            <DictInput label="Display Styles Dictionary" value={configObj.display_styles} onChange={(val) => updateField(['display_styles'], val)} placeholder="hero-closeup: Tight frame on hero detail" />
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Product Vocabulary Parts</h4>
                            <DictInput label="Product Parts Vocabulary" value={productVocabulary.parts} onChange={(val) => updateField(['product_vocabulary', 'parts'], val)} placeholder={"neckline: Neckline\nhem: Hem"} />
                        </div>
                    </div>
                )}

                {activeTab === 'occasions_cta' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Occasions</h4>
                            <ArrayInput label="Festive Occasions" value={occasions.festive} onChange={(val) => updateField(['occasions', 'festive'], val)} />
                            <ArrayInput label="Wedding Occasions" value={occasions.wedding} onChange={(val) => updateField(['occasions', 'wedding'], val)} />
                            <ArrayInput label="Everyday Occasions" value={occasions.everyday} onChange={(val) => updateField(['occasions', 'everyday'], val)} />
                            <ArrayInput label="Campaign Types" value={occasions.campaign} onChange={(val) => updateField(['occasions', 'campaign'], val)} />
                            <DictInput label="Content Mix (%)" value={occasions.content_mix} onChange={(val) => updateField(['occasions', 'content_mix'], val)} placeholder={"hero: 50\nlifestyle: 25"} />
                        </div>
                        <div>
                            <h4 className="font-semibold mb-4 text-wabi-text text-base">Elements & Formats</h4>
                            <ArrayInput label="CTA Rotation" value={configObj.cta_rotation} onChange={(val) => updateField(['cta_rotation'], val)} />
                            <ArrayInput label="Variation Modifiers" value={configObj.variation_modifiers} onChange={(val) => updateField(['variation_modifiers'], val)} />
                            <ArrayInput label="Sample Artisans/Names" value={configObj.sample_artisans} onChange={(val) => updateField(['sample_artisans'], val)} />
                            <ArrayInput label="Specific Niche Hashtags" value={hashtags.niche} onChange={(val) => updateField(['hashtags', 'niche'], val)} />
                        </div>
                    </div>
                )}

                {activeTab === 'advanced' && (
                    <div>
                        <Alert
                            message="Warning: Direct JSON edits here will overwrite specific field tabs upon saving. Avoid removing top-level keys."
                            type="error"
                            className="mb-4"
                        />
                        <textarea
                            value={rawConfig}
                            onChange={(e) => setRawConfig(e.target.value)}
                            className="w-full h-[400px] px-4 py-3 font-mono text-sm bg-wabi-bg/80 text-wabi-text border border-wabi-text/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-wabi-text/15 resize-y"
                            spellCheck={false}
                        />
                    </div>
                )}
            </div>

            <div className="flex justify-end mt-8 pt-4 border-t border-wabi-text/5">
                <Button onClick={handleSave} loading={saving} loadingText="Saving Profile...">
                    Save AI Profile
                </Button>
            </div>
        </SectionCard>
    );
}
