-- Migration: 005_syndicates
-- Purpose: Syndicate management tables for PBG v0.7.2
-- Run in: Supabase SQL editor (iflamze45 project)

CREATE TABLE IF NOT EXISTS syndicates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  owner_api_key TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS syndicate_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  syndicate_id UUID NOT NULL REFERENCES syndicates(id) ON DELETE CASCADE,
  api_key TEXT NOT NULL,
  joined_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(syndicate_id, api_key)
);

CREATE TABLE IF NOT EXISTS syndicate_tickets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  syndicate_id UUID NOT NULL REFERENCES syndicates(id) ON DELETE CASCADE,
  booking_code TEXT NOT NULL,
  added_by TEXT NOT NULL,
  added_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_syndicates_owner ON syndicates(owner_api_key);
CREATE INDEX IF NOT EXISTS idx_syndicate_members_syndicate ON syndicate_members(syndicate_id);
CREATE INDEX IF NOT EXISTS idx_syndicate_tickets_syndicate ON syndicate_tickets(syndicate_id);

-- RLS: backend uses service_role key — full access policy
ALTER TABLE syndicates ENABLE ROW LEVEL SECURITY;
ALTER TABLE syndicate_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE syndicate_tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_full_access" ON syndicates FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_full_access" ON syndicate_members FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_full_access" ON syndicate_tickets FOR ALL USING (true) WITH CHECK (true);
