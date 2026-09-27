---
name: bookc-status
description: book-companion 진행 상태 확인. 책 하나(또는 모든 책)의 단계별 진행표, 장별 교정·통독 현황, 다음에 실행할 스킬을 보여 준다. "/bookc-status [책]", "책 작업 어디까지 됐어", "책 진행 상황"에 쓴다.
---

# 진행 상태

인자: 책(PDF 경로·파일명·책 폴더 이름) 또는 없음.

1. `PLUGIN/references/runtime.md` 2절대로 `$BC`를 준비한다.
2. **인자 없음**: 사용자 기기의 `books/*/_work/manifest.json`을 모두 읽어(방식 A는 `device_bash`의 python3로 직접 읽는다 — 내려받을 필요 없음) 책마다 한 줄 표로 보여 준다: 책, 1–5단계 완료 여부(✓/…/–), 파싱 교정 쪽 수, 통독 장 수, 마지막 갱신 시각. `books-pdf/`에 있지만 아직 시작하지 않은 PDF도 "미시작"으로 함께 보여 준다.
3. **인자 있음**: 책을 찾아(runtime.md 3절) manifest만 내려받거나(작으면 `device_bash cat`으로 읽어 WORK에 쓴다) 전체를 내려받고 `$BC status $B`를 그대로 보여 준다. 이어서 `$BC todo $B parse`가 비어 있지 않으면 남은 장을 요약한다.
4. 마지막 줄에 다음에 실행할 명령(`/bookc <책>` 또는 단계 스킬)을 적는다.

파일을 바꾸지 않는다.

## 진행 현황 페이지

- 인자가 있으면 `$BC progress $B`로 progress.html을 다시 그린다. 방식 A에서는 기기로 보낸다(runtime.md 7절).
- 그다음 `project/book-companion/books/<slug>/progress.html` 위치를 computer:// 링크로 함께 알려 준다.
