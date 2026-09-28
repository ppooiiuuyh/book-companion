---
name: bookc
description: book-companion 전체 실행. 스캔 책 PDF 하나를 인테이크 → 파싱 → 조사 → 통독 → 종합 → 인사이트 → 리뷰까지 끝까지 처리해 Claude와 같이 읽는 지식 베이스로 만든다. 파싱·조사·통독을 장 단위로 겹쳐 병렬 실행하고, 중간에 끊겼으면 마지막으로 끝난 곳부터 이어 간다. "/bookc [pdf 경로 또는 books-pdf 안의 파일명]", "이 책 전부 처리해줘", "책 작업 이어서 해줘"에 쓴다.
---

# 전체 실행 (/bookc)

인자: PDF 경로, 또는 `books-pdf/` 안의 파일명(확장자는 빼도 된다). 인자가 없으면 진행 중인 책을 찾는다.

## 1. 시작

1. `PLUGIN/references/runtime.md`를 읽는다(`PLUGIN` = 이 스킬 폴더의 두 단계 위). 그 절차대로 준비, 책 찾기, 내려받기를 한다. 쪽 이미지를 만들 수 있게 PDF도 스테이징한다.
2. 이미 있는 책이면 `$BC status $B` 표를 보여 주고 "이어서 합니다"라고 한 줄 알린다. 새 책이면 "새로 시작합니다"라고 알린다.
3. **1단계(인테이크)** 가 끝나지 않았으면 `PLUGIN/skills/bookc-1-intake/SKILL.md`의 절차를 먼저 끝까지 한다. 인테이크는 병렬로 하지 않는다.

## 2. 파동(wave) 실행 — 2·3·4단계를 겹쳐서

인테이크 뒤에는 단계를 하나씩 끝내고 넘어가지 않는다. **장 단위로 준비된 작업을 모아 한 번에 병렬로** 돌린다. 반복 순서:

1. `$BC ready $B`로 지금 시작할 수 있는 작업을 우선순위 순서대로 받는다(한 줄에 JSON 하나). 목록이 비었으면 3절로 간다.
2. 위에서부터 **최대 4개**를 골라 이번 파동으로 삼는다. 규칙:
   - `read`(통독 2차)는 한 번에 한 장만 한다. 목록에 있으면 항상 포함한다. 가장 긴 순차 사슬이기 때문이다.
   - `parse`는 장 하나에 작업자 하나를 둔다. 남은 쪽이 25쪽을 넘으면 둘로 나누어 작업자 2개로 센다. `note`가 "조립·lint만"인 장은 에이전트 없이 직접 처리한다(아래 3번).
   - `research`는 영역 하나에 작업자 하나를 둔다. `research-merge`는 직접 한다.
   - 남는 자리는 `study`(통독 1차)로 채운다.
3. 이번 파동의 작업자들을 **한 메시지에 여러 Agent 호출로 동시에** 띄운다. 작업마다 지시문은 아래와 같다.
   - `parse` → `PLUGIN/references/parse-worker.md`의 작업자 지시문
   - `research` → `PLUGIN/skills/bookc-3-research/SKILL.md`의 영역 작업자 지시문
   - `study` → `PLUGIN/skills/bookc-4-read/SKILL.md`의 1차 지시
   - `read` → 같은 파일의 2차 지시(해당 장 하나만)
4. 파동이 끝나면 후처리를 **직접** 한다.
   - `parse` 장: `apply`, `assemble`, `lint`를 돌린다(bookc-2-parse 6번과 같다). 주석 장이면 먼저 `$BC notes`. 주석 장이 아직 조립되지 않았으면 다른 장은 교정만 해 두고 조립은 다음 파동으로 미룬다. 통과하면 `mark parse`.
   - `study` 장: `mark study`, `read` 장: `mark read`
   - `research-merge`: bookc-3-research의 3–4번을 직접 수행한다.
   - 실패한 작업자가 있으면 따로 처리하지 않는다. 다음 `ready`에 남은 일로 다시 나온다. 같은 작업이 두 번 연속 실패하면 멈춘다(4절).
5. 체크포인트(올려 보내기)를 남긴다. 그다음 `SendUserMessage`로 한 줄을 알린다. 예: "파동 3 ✓ 파싱 02·03, 통독1차 00·01, 조사 bookstore — 교정 71/202쪽, 통독 0/10장". 다시 1번으로 돌아간다.

파싱이 모두 끝나면 2단계 7번(표본 감사)을 한다. 이때 장마다 감사자를 따로 두어 **병렬로** 돌린다(최대 4). 그다음 `$BC glossary $B`를 실행한다. 이 두 가지는 2단계의 끝으로 치며, 통독 2차와 겹쳐 진행해도 된다.

## 진행 현황 기록 (runtime.md 7절)

- **시작**: 준비와 책 찾기가 끝나면 `$BC log $B run-start run=bookc`을 기록하고 progress.html을 기기로 보낸다. 위치는 한 번 알린다.
- **인테이크가 남아 있으면**: `stage-start stage=intake`로 시작하고 `stage-end`로 닫는다. 추출, 구조 확인, OCR은 각각 `kind=other` task로 기록한다.
- **파동마다**
  1. `wave-start wave=N`, 이어서 작업자마다 `task-start`를 기록한다(`lane`=1…4, `label`=장 id 또는 조사 영역, parse면 `pages`=맡긴 쪽 수). 그다음 progress.html을 보내고 Agent를 띄운다.
  2. Agent가 돌아오면 작업마다 `task-end status=ok|fail`을 기록한다.
  3. 직접 하는 후처리(조립·lint, 조사 병합)도 `kind=other` task로 짧게 기록한다. 끝나면 `wave-end`, 체크포인트, progress.html 보내기 순서로 마친다.
- **감사·종합·인사이트**: 감사자는 `kind=other label=감사 NN`으로, 종합은 `kind=other label=종합`으로, 인사이트는 `kind=other label=인사이트`로, 리뷰는 `kind=other label=리뷰 store|critical|log`로 기록한다(각각 `stage-start stage=synthesize|insight|review`로 감싼다).
- **끝**: `run-end status=done`을 기록하고 progress.html을 보낸다. 4절 사유로 멈추면 `run-end status=stopped note=사유`를 기록한다.
## 3. 마무리

1. `$BC can $B synthesize`가 통과하면 `PLUGIN/skills/bookc-5-synthesize/SKILL.md`의 절차를 수행한다.
2. 이어서 `PLUGIN/skills/bookc-6-insight/SKILL.md`의 절차를 수행한다(한 줄 요약·핵심 주장·인사이트·반박 → insights.md).
3. 이어서 `PLUGIN/skills/bookc-7-review/SKILL.md`의 절차를 수행한다(서점 리뷰·비평형 서평·독서 기록 → reviews/). 사용자 관점을 묻는 질문은 이 시점에 한 번만 한다.
4. `$BC status $B`, insights.md의 한 줄 요약, 결과 폴더 위치(사용자 기기의 `project/book-companion/books/<slug>/`)를 알린다. 이어서 `/bookc-open <책>`으로 대화를 시작할 수 있다고 안내한다.

## 4. 멈춰야 할 때

- 1단계 구조 확인에서 장 경계를 자신 있게 정할 수 없으면(목차와 안 맞음, 표지가 없는 책 등) 가장 그럴듯한 안을 적용하고, 무엇을 적용했는지 알린 뒤 계속한다. 사용자가 있으면 AskUserQuestion으로 확인해도 된다.
- 기기에 닿지 않으면 클라우드 작업 사본에서 계속한다. 체크포인트를 올려 보내지 못했다는 사실은 끝에 알린다.
- 같은 작업이 두 번 연속 실패하면 멈춘다. 어디서 무엇이 실패했는지, 그리고 이어 하는 방법(같은 `/bookc` 명령)을 알린다.

## 이어 하기와 단계 스킬의 관계

- 이 스킬은 상태를 따로 기억하지 않는다. 진행 상황은 모두 `_work/manifest.json`과 파일에 있다. 같은 명령을 다시 실행하면 `ready`가 남은 일만 돌려준다.
- 단계를 장 단위로 겹치는 것은 이 전체 실행에서만 한다. `/bookc-4-read` 같은 단계 스킬은 선행 단계 전체가 끝나야 실행된다(`bc.py can`). 두 방식이 만든 결과물과 상태 기록은 같다.
