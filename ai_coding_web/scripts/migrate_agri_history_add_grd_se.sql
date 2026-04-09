-- SQLite/PostgreSQL 공용 마이그레이션
-- agri_price_history 에 grd_cd, se_cd 컬럼 추가 (가이드 4-1 시계열 식별 키 보완)
--
-- SQLite: python -c "import sqlite3; c=sqlite3.connect('db.sqlite3'); c.execute(...)"
-- 또는 etl.py 실행 시 Base.metadata.create_all() 가 신규 DB에는 자동 반영됨.
-- 기존 DB에 적용하려면 아래 SQL을 직접 실행하거나 DB를 삭제 후 재생성하세요.

-- 컬럼 추가 (이미 있으면 오류 발생 → 무시)
ALTER TABLE agri_price_history ADD COLUMN grd_cd TEXT;
ALTER TABLE agri_price_history ADD COLUMN se_cd TEXT;

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_agri_hist_grd_se ON agri_price_history (grd_cd, se_cd);
