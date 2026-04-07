# Hanness Framework — MVP Page Manifest

> Context-aware 분할: 프로젝트 전체 MVP 작업을 9개 페이지 단위로 쪼갠 마스터 인덱스.
> 각 페이지 단위는 독립적으로 구현·검증 가능하며, 직렬 실행 순서를 따른다.

## 실행 순서 (직렬)

| 순서 | ID   | 페이지 명                     | 대상 HTML               | 상태      |
|------|------|-------------------------------|-------------------------|-----------|
| 1    | P01  | 공통 레이아웃 & 인프라        | 전체 공통               | pending   |
| 2    | P02  | 홈 / 워드클라우드 메인        | index.html              | pending   |
| 3    | P03  | 농산물 시세 분석              | agri-analytics.html     | pending   |
| 4    | P04  | 카테고리 분석 (공통 템플릿)   | analysis-1~5.html       | pending   |
| 5    | P05  | 로그인 / 인증 UX              | login.html              | pending   |
| 6    | P06  | 마이페이지 대시보드           | mypage.html             | pending   |
| 7    | P07  | 저장된 분석 목록              | my-analyses.html        | pending   |
| 8    | P08  | 분석 빌더 / 상세              | my-analysis.html        | pending   |
| 9    | P09  | ETL 파이프라인 & 인제스트 API | etl.py / ingest 엔드포인트 | pending |

## 의존 그래프

```
P01 (공통)
 ├─▶ P02 (홈)
 ├─▶ P03 (농산물)
 ├─▶ P04 (카테고리 분석)
 ├─▶ P05 (로그인)
 │    └─▶ P06 (마이페이지)
 │         ├─▶ P07 (분석 목록)
 │         └─▶ P08 (빌더)
 └─▶ P09 (ETL / ingest)  ←── P02, P03, P04 가 소비
```

## 체크포인트 실행

```bash
python hanness/runner.py --page P01   # 단일 페이지 실행
python hanness/runner.py --all        # 전체 직렬 실행
python hanness/runner.py --status     # 전체 상태 출력
```

## 파일 규칙

- `hanness/pages/pNN.page` — 페이지 명세 (구현 목표 · 대상 파일 · 수락 기준)
- `hanness/tasks/pNN.task` — 런타임 체크포인트 (상태 · 진행 항목 · 출력물)
- `hanness/runner.py`      — 직렬 실행 스크립트 (Step 2에서 구현)
