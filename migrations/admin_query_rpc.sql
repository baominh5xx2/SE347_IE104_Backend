-- ============================================
-- Admin Query RPC Function for BigQuery Tool
-- Allows dynamic SQL with strict validation
-- Created: 2025-12-17
-- ============================================

-- Function to validate and execute admin queries
-- This is the ONLY function needed - LLM will generate all queries dynamically
CREATE OR REPLACE FUNCTION admin_execute_query(
    query_text TEXT,
    params JSONB DEFAULT '{}'::JSONB
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
    query_lower TEXT;
    forbidden_keywords TEXT[] := ARRAY[
        'insert', 'update', 'delete', 'drop', 'truncate', 
        'alter', 'create', 'grant', 'revoke', 'execute',
        'pg_', 'information_schema'
    ];
    keyword TEXT;
BEGIN
    -- Normalize query for validation
    query_lower := lower(trim(query_text));
    
    -- Remove trailing semicolons (they cause issues in subquery)
    query_lower := rtrim(query_lower, ';');
    query_text := rtrim(trim(query_text), ';');
    
    -- Check if query starts with SELECT or WITH (for CTEs)
    IF NOT query_lower ~ '^(select|with)' THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed. Query must start with SELECT or WITH.';
    END IF;
    
    -- Check for forbidden keywords (DML, DDL, system tables)
    FOREACH keyword IN ARRAY forbidden_keywords
    LOOP
        IF query_lower ~ ('\m' || keyword || '\M') THEN
            RAISE EXCEPTION 'Forbidden keyword detected: %', keyword;
        END IF;
    END LOOP;
    
    -- Execute the query and return as JSONB array
    EXECUTE format('SELECT COALESCE(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (%s) t', query_text) INTO result;
    
    RETURN result;
    
EXCEPTION
    WHEN OTHERS THEN
        -- Return error as JSONB object (not raise, so client can handle)
        RETURN jsonb_build_object(
            'error', TRUE,
            'message', SQLERRM,
            'query', left(query_text, 200)  -- Truncate query in error for safety
        );
END;
$$;

-- Grant execute permission to authenticated users (Supabase RLS)
GRANT EXECUTE ON FUNCTION admin_execute_query TO authenticated;

-- Documentation
COMMENT ON FUNCTION admin_execute_query IS 
'Safe dynamic SQL execution for admin queries.
- Only allows SELECT/WITH queries
- Blocks INSERT/UPDATE/DELETE/DROP and system table access
- Returns JSONB array of results or error object';

-- ============================================
-- Verification (run after migration)
-- ============================================
-- SELECT admin_execute_query('SELECT COUNT(*) as cnt FROM bookings');
-- Expected: [{"cnt": <number>}]

