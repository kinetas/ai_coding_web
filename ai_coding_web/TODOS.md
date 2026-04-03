# TODOS

## Phase 2: 키워드 티커 컴포넌트

**What:** 헤더 하단에 상위 키워드 자동 스크롤 티커 추가

**Why:** 대시보드 뉴스룸 느낌을 완성하는 핵심 요소. 사이트 열자마자 "지금 핫한 키워드"가 움직이며 보임.

**Pros:** Bloomberg Terminal 느낌 완성. 사용자가 즉각적으로 트렌드 파악 가능.

**Cons:** JS 애니메이션 추가로 index.js 복잡도 증가. API 실패 시 빈 티커 처리 필요.

**Context:** Phase 1 (2컬럼 레이아웃, CSS 변수화) 완료 후 구현. `/api/wordcloud` 엔드포인트 데이터 사용. CSS `@keyframes` 스크롤 + JS로 데이터 주입. 실패 시 마지막 캐시 데이터 표시.

**Depends on:** Phase 1 완료 (styles.css CSS 변수 + index.html 구조)

---

## Phase 2: URL 해시 기반 카테고리 필터 공유

**What:** `?category=agri` 쿼리 파라미터를 `#category=agri` 해시로 전환

**Why:** 해시는 서버 요청 없이 공유 가능. 현재 `?category=` 방식은 일부 정적 서버에서 파라미터를 무시함.

**Pros:** 카테고리 필터 URL 공유 가능. 브라우저 뒤로가기로 필터 상태 복원.

**Cons:** `index.js`의 URLSearchParams 로직 수정 필요. 기존 `?category=` 링크 하위 호환 처리 필요.

**Context:** `index.js:232-236`에 이미 `?category=` 파싱 로직 있음. `window.location.hash` 파싱 추가 + `hashchange` 이벤트 리스너.

**Depends on:** Phase 1 완료
