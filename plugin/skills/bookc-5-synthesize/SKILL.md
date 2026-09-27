---
name: bookc-5-synthesize
description: book-companion 5단계. 장 요약·통독 메모·외부 조사를 종합해 책 전체 요약(L0)과 목차 겸 입구 문서(index.md), Claude의 독해와 외부 평가를 대조한 synthesis.md를 만든다. "/bookc-5-synthesize <책>", "책 종합 정리"에 쓴다.
---

# 5단계: 종합

인자: PDF 경로·파일명·책 폴더 이름. 선행 단계: 4(통독 전 장 완료).

`PLUGIN/references/runtime.md`의 준비 → 책 찾기 → 내려받기 → `$BC can $B synthesize` (불가하면 안내문 전하고 끝).

## 절차

1. 읽을 것: 모든 `<slug>/study.md`(L1 부분), `reading/_carry.md`, 모든 `reading/<id>.md`의 "핵심 한 문단", `research/` 네 파일, `glossary.md`, `$BC outline $B`.
2. **`B/index.md`** — 이 책의 입구. 대화할 때 가장 먼저 읽는 파일이므로 6천 자 이내로.
   - frontmatter: `book`, `author`, `translator`, `pages`, `printed_page_offset`, `layer: index`, `generated`
   - `## L0 책 요약` 8–12문장 (study.md의 L1만 근거, `[주장]/[근거]/[해석]` 구분)
   - `## 목차`: 장마다 `- [제N장 제목](NN_slug/source.md) — L1 한 줄 (p012–p025) · [요약](NN_slug/study.md) · [메모](reading/NN.md)`
   - `## 핵심 개념`: 5–10개, glossary 링크와 첫 등장 앵커
   - `## 핵심 도표`: 논지를 받치는 도표 3–6개, 이미지 링크와 한 줄 설명
   - `## 파일 안내`: 층 구조(원문/요약/통독/외부)와 쪽 번호 규칙(PDF 쪽 + offset = 인쇄 쪽)
3. **`B/synthesis.md`** — Claude의 독해와 외부 평가 대조
   - `## 논지 구조`: 전제 → 근거 → 결론의 뼈대, 장 앵커
   - `## 외부 평가와 대조`: 하이라이트·비판마다 원문 근거 앵커로 "맞다 / 과장 / 원문에 없음 / 판단 보류"
   - `## watchlist 결산`: 답한 질문, 끝내 답이 없는 질문
   - `## 강점과 한계`, `## 지금 읽을 때 주의할 점`(시대·지역 맥락, 데이터 시점)
   - `## 함께 이야기해 볼 질문` 5–8개
4. `$BC lint $B` (전 장) 재확인. errors가 있으면 보고하고 고친다.
5. `$BC mark $B synthesize` → 체크포인트 → `$BC status $B`와 L0 요약 3문장, 사용 방법(`/bookc-open <책>`)을 보고한다.

## 규칙

- index.md의 요약은 원문 근거만. 외부 의견과 Claude의 평가는 synthesis.md에.
- 링크는 책 폴더 기준 상대 경로. Obsidian·일반 Markdown 뷰어에서 모두 열려야 한다.
