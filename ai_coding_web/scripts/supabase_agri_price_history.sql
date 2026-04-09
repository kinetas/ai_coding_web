-- 조사일·품목 단위 스냅샷 (ETL이 API로 적재, 앱은 조회·집계는 Supabase 기준)
-- Supabase SQL Editor에서 supabase_align_etl.sql / supabase_agri_price_analytics.sql 이후 실행.
--
-- 가이드(agri_json_analysis_guide.txt) 4-1 시계열 식별 키:
--   item_cd + vrty_cd + grd_cd + se_cd + exmn_ymd
-- unit / unit_sz 는 payload 내 보존 (NULL 처리 복잡도로 컬럼 미분리)
-- 중량(kg/g): payload.exmn_dd_cnvs_avg_prc 사용
-- 개수(개/마리 등): payload.exmn_dd_avg_prc + unit_sz 보존

create table if not exists public.agri_price_history (
  id bigint generated always as identity primary key,
  exmn_ymd text not null,
  item_key text not null,
  item_cd text,
  vrty_cd text,
  grd_cd text,   -- 등급 코드 (가이드 4-1 시계열 키)
  se_cd text,    -- 거래 단계 코드 (가이드 4-1 시계열 키)
  payload jsonb not null default '{}'::jsonb,
  ingested_at timestamptz not null default now(),
  constraint agri_price_history_exmn_item_key unique (exmn_ymd, item_key)
);

-- 기존 테이블에 컬럼 추가 (이미 있으면 무시)
alter table public.agri_price_history
  add column if not exists grd_cd text,
  add column if not exists se_cd text;

create index if not exists idx_agri_price_history_exmn on public.agri_price_history (exmn_ymd desc);
create index if not exists idx_agri_price_history_item_cd on public.agri_price_history (item_cd, exmn_ymd desc);
create index if not exists idx_agri_price_history_grd_se on public.agri_price_history (grd_cd, se_cd);

alter table public.agri_price_history enable row level security;

drop policy if exists "Allow public read agri_price_history" on public.agri_price_history;
create policy "Allow public read agri_price_history"
  on public.agri_price_history for select to anon using (true);

comment on table public.agri_price_history is 'ETL: etl_supabase.py — API item 원본 JSON(payload), 조사일별 품목 키로 upsert. 시계열 키: item_cd+vrty_cd+grd_cd+se_cd+exmn_ymd';
comment on column public.agri_price_history.grd_cd is '등급 코드 (상/중/하 등) — 가이드 4-1 시계열 식별 키';
comment on column public.agri_price_history.se_cd is '거래 단계 코드 (중도매/소매 등) — 가이드 4-1 시계열 식별 키';
