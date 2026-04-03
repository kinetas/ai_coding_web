-- 조사일·품목 단위 스냅샷 (ETL이 API로 적재, 앱은 조회·집계는 Supabase 기준)
-- Supabase SQL Editor에서 supabase_align_etl.sql / supabase_agri_price_analytics.sql 이후 실행.

create table if not exists public.agri_price_history (
  id bigint generated always as identity primary key,
  exmn_ymd text not null,
  item_key text not null,
  item_cd text,
  vrty_cd text,
  grd_cd text,
  se_cd text,
  payload jsonb not null default '{}'::jsonb,
  ingested_at timestamptz not null default now(),
  constraint agri_price_history_exmn_item_key unique (exmn_ymd, item_key)
);

create index if not exists idx_agri_price_history_exmn on public.agri_price_history (exmn_ymd desc);
create index if not exists idx_agri_price_history_item_cd on public.agri_price_history (item_cd, exmn_ymd desc);

alter table public.agri_price_history enable row level security;

drop policy if exists "Allow public read agri_price_history" on public.agri_price_history;
create policy "Allow public read agri_price_history"
  on public.agri_price_history for select to anon using (true);

comment on table public.agri_price_history is 'ETL: etl_supabase.py — API item 원본 JSON(payload), 조사일별 품목 키로 upsert';
