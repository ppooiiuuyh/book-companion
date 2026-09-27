---
name: bookc-4-read
description: book-companion 4단계. 1차로 장별 요약(L2 절·L1 장)과 도표 읽기를 병렬로 만들고, 2차로 앞에서부터 한 장씩 차례로 통독하며 앞 장 맥락을 이은 메모·질문·연결을 남긴다. 장 단위로 이어서 한다. "/bookc-4-read [책]", "책 통독", "장별 요약 만들어줘"에 쓴다.
---

# 4단계: 통독 (1차 병렬 요약 → 2차 순차 통독)

인자: PDF 경로·파일명·책 폴더 이름. 선행 단계: 2(파싱 전 장 완료), 3(조사).

`PLUGIN/references/runtime.md`의 준비 → 책 찾기 → 내려받기 → `$BC can $B read` (불가하면 안내문 전하고 끝). 쪽 이미지는 필요 없다(도표는 `img/`를 본다).

## 왜 두 번인가

- **1차(요약)**: `study.md`는 규약상 그 장의 원문만 근거로 쓰므로 앞 장 맥락이 필요 없다. 장끼리 **병렬**로 만든다.
- **2차(통독)**: 앞 장을 읽은 상태에서 다음 장을 읽는 것이 목적이다. **순차**로, `reading/_carry.md`로 맥락을 이어 간다. 1차 결과를 먼저 읽으므로 2차는 흐름·연결·질문에 집중한다.

`$BC todo $B read`는 장마다 남은 차수(1차/2차)를 보여 준다. 끝난 것은 건너뛴다.

## 1차: 장별 요약 — 병렬

1차가 남은 장마다 서브에이전트(general-purpose)를 하나씩 띄운다. **한 메시지에 여러 Agent 호출**로 동시에 최대 4개까지 띄운다. 지시 내용:

- 읽을 것: `PLUGIN/references/conventions.md`의 5절, 이 장의 `source.md` 전체, 이 장 `img/`의 도표(Read), `glossary.md`
- 쓸 것 ① `<slug>/study.md`
  - frontmatter에 `book`, `chapter`, `layer: study`, `pages`
  - `## L1 장 요약` 5–8문장
  - `## L2 절 요약`: source.md의 `##` 절마다 `### §N.k 제목 (p045–p048)`, 그 아래 3–5문장과 원문 앵커. 문장마다 `[주장]` `[근거]` `[해석]`을 구분한다. 원문에 없는 것은 쓰지 않는다
- 쓸 것 ② `reading/<id>.md`의 `## 도표 읽기`: 도표마다 무엇을 보여 주는지, 본문 주장과 맞는지(앵커 포함). 파일이 없으면 frontmatter(`book`, `chapter`, `layer: reading`)와 이 절만 만든다
- 다른 장의 파일은 건드리지 않는다. 끝나면 L1 요약 첫 문장만 돌려준다.

작업자가 끝날 때마다 `$BC mark $B study --chapters <id>`를 실행한다. 모든 1차가 끝나면 체크포인트를 남긴다.

## 2차: 통독 — 순차

1. 처음이면 `reading/_carry.md`를 만든다. 넣을 것: 책 정보, 장 목록(`$BC outline $B`), `research/highlights.md`·`critiques.md`의 요지 5줄, `watchlist.md`의 질문 번호 목록.
2. 2차가 남은 첫 장부터 **한 장씩** 진행한다. 서브에이전트 하나로 하거나, 책이 짧으면(본문 6만 자 이하) 직접 한다.
   - 읽을 것: conventions.md의 6절, `reading/_carry.md`, 직전 장 `reading/<id>.md`, `research/watchlist.md`, 이 장의 `study.md`(1차 결과), `source.md` 전체
   - 쓸 것: `reading/<id>.md`에 아래 절을 **덧붙인다**. `## 도표 읽기`는 그대로 둔다.
     - `## 흐름 메모`: 읽는 순서대로 5–15개. 각 메모 끝에 앵커 `(p045-b3)`를 단다. 내용은 저자의 논지 전개, 근거의 강약, 앞 장과의 연결, 놀라운 점, 의문
     - `## watchlist 답`: 이 장에서 답이 나온 질문 번호와 답(앵커 포함). 새로 생긴 질문은 `## 새 질문`에 적는다
     - `## 이 장의 핵심 한 문단`: Claude의 해석임을 밝힌다
   - 고칠 것:
     - `reading/_carry.md` 끝에 이 장 요지 3–5줄을 덧붙이고 "지금까지 열린 질문"을 갱신한다. 3천 자를 넘으면 오래된 장 요지를 한 줄씩으로 줄인다.
     - `research/watchlist.md`에서 답한 질문을 `- [x] … → reading/<id>.md`로 바꾼다.
3. 장이 끝날 때마다 `$BC mark $B read --chapters <id>` 다음 체크포인트를 남기고, `SendUserMessage`로 한두 줄 진행 상황을 알린다.
4. **마무리**
   - 후기나 옮긴이 후기가 있으면 `reading/90.md`에 짧게 메모한다(필수 아님).
   - `$BC status $B`와 장별 핵심을 한 줄씩 보고한다.

## 진행 현황 기록 (runtime.md 7절)

- 선행 검사를 통과하면 `$BC log $B run-start run=bookc-4-read`, 이어서 `$BC log $B stage-start stage=study`를 기록하고 progress.html을 기기로 보낸다. 위치는 한 번 알린다. 선행 검사에서 불가하면 아무것도 기록하지 않는다.
- 1차는 `stage=study`, 2차는 `stage=read`로 나눠 stage-start/stage-end를 기록한다. 장마다 `kind=study` 또는 `kind=read` task를 기록한다(`label`=장 id). 2차는 장이 끝날 때마다 progress.html을 보낸다.
- 끝나면 `stage-end`, `run-end status=done`을 기록하고 progress.html을 보낸다. 도중에 멈추면 `run-end status=stopped note=사유`를 기록한다.
## 규칙

- study.md에는 원문에 있는 것만 쓴다. 해석, 평가, 외부 의견은 reading/에 쓴다.
- 요약 문장에는 반드시 앵커나 쪽 범위를 단다.
- 통독 도중 원문 오류(OCR 누락 등)를 발견하면 reading 메모에 `[원문 확인 필요 p045]`로 적고 계속한다. 끝에 목록으로 보고한다.
