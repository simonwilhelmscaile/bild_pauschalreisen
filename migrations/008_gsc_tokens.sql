-- GSC OAuth tokens for Google Search Console integration
CREATE TABLE IF NOT EXISTS gsc_tokens (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    site_url text NOT NULL,
    access_token text,
    refresh_token text NOT NULL,
    token_expiry timestamptz,
    email text,
    tenant_id uuid REFERENCES tenant_configs(id),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Allow upsert by site_url
CREATE UNIQUE INDEX IF NOT EXISTS gsc_tokens_site_url_idx ON gsc_tokens(site_url);
