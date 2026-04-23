-- Service cases imported from Salesforce customer service exports
CREATE TABLE IF NOT EXISTS service_cases (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id text NOT NULL DEFAULT 'beurer',
    case_id text NOT NULL,
    product_raw text NOT NULL,
    product_model text,
    product_category text,
    reason text NOT NULL,
    case_date date NOT NULL,
    imported_at timestamptz DEFAULT now(),
    import_batch_id uuid NOT NULL
);

-- Deduplication: one case per client
CREATE UNIQUE INDEX IF NOT EXISTS service_cases_client_case_idx
    ON service_cases(client_id, case_id);

-- Date range queries
CREATE INDEX IF NOT EXISTS service_cases_client_date_idx
    ON service_cases(client_id, case_date);

-- Product lookups
CREATE INDEX IF NOT EXISTS service_cases_client_product_idx
    ON service_cases(client_id, product_model);
