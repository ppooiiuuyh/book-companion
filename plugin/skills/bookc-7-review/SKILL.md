---
name: bookc-7-review
description: book-companion 7단계. 완성된 지식 베이스와 사용자의 입장(my_stance.json·대화)을 바탕으로 서점 리뷰, 비평형 서평, 개인 독서 기록 세 편을 좋은 리뷰 기준에 맞춰 쓰고 자체 점검표를 붙여 진행 현황 페이지 '한눈에 보기' 탭에 보여 준다. "/bookc-7-review [책] [store|critical|log]", "이 책 리뷰 써줘", "서평 써줘"에 쓴다.
---

# 7단계: 리뷰

인자: 책(PDF 경로·파일명·책 폴더 이름). 선택 인자로 용도(store, critical, log)를 줄 수 있다. 없으면 세 편 모두 쓴다. 선행 단계: 6(인사이트).

`PLUGIN/references/runtime.md`의 준비 → 책 찾기 → 내려받기 → `$BC can $B review` (불가하면 안내문 전하고 끝).

## 절차

1. **기준 읽기**: `PLUGIN/references/review-guide.md`를 읽는다. 리뷰는 반드시 이 기준을 따른다.
2. **사용자 관점 모으기** (review-guide의 '사용자의 관점' 순서대로)
   - 기기의 책 폴더에 `my_stance.json`이 있으면 읽는다. 사용자의 다운로드 폴더에 있다고 하면 책 폴더로 옮겨 달라고 한 번 요청한다.
   - 없고 사용자가 대화 중이면 AskUserQuestion으로 짧게 묻는다: 읽게 된 계기, 가장 남은 점, 권하고 싶은 독자. 모두 선택형으로 묻고, 직접 입력도 받는다.
   - 사용자가 없거나 건너뛰면 관점 없이 쓴다. 이때 개인사는 지어내지 않는다.
3. **재료 읽기**: `insights.md`(한 줄 요약, 핵심 주장, 반박), `index.md`, `synthesis.md`, `reading/09.md`(또는 마지막 장)의 "책 전체를 마치며", `research/highlights.md`·`critiques.md`, `_work/manifest.json`의 book 정보(판본·번역). 인용할 대목은 `source.md`에서 `grep`으로 확인하고, 인쇄 쪽 번호(PDF 쪽 + `printed_page_offset`)로 밝힌다.
4. **쓰기**: `B/reviews/store.md`, `critical.md`, `log.md`
   - 각 파일 머리는 frontmatter(`book`, `layer: review`, `kind`, `generated`)와 `# 제목` 한 줄이다.
   - 본문은 review-guide의 용도별 구조를 따른다. 원문 앵커(`p045-b3`)는 본문에 그대로 넣어도 되며, 진행 현황 페이지에서 원문 보기 칩이 된다(문단당 1–3개).
   - **섹션은 `##` 소제목으로 나눈다**(서점 리뷰도: `## 어떤 책인가`·`## 좋았던 점`·`## 아쉬운 점과 주의할 점`·`## 권할 독자`). 첫 `##` 앞의 첫 단락은 페이지에서 총평 상자로, 각 `##` 섹션은 카드로 보인다. 문단은 2–4문장, 한 섹션 안 여러 논점은 `**굵은 소제목.**`으로 시작하는 짧은 문단으로 나눈다.
   - 판단·결론·실천 조언 문장을 `==…==`로 하이라이트한다(서점 6–8곳, 비평 8–10곳, 기록 5–7곳, 섹션마다 1곳 이상, 문장 하나씩).
   - 내부 파일명·도구 이름을 쓰지 않고, 용어는 처음 나올 때 풀이한다(6단계의 '읽기 쉬운 글' 규칙).
   - 사용자 입장이 있으면 반영한다. 동의·반대한 주장은 리뷰의 판단에 쓰고, 메모는 개인 기록에 쓴다.
5. **점검**: review-guide의 점검표로 세 편을 스스로 점검해 `B/reviews/meta.json`을 쓴다.
   ```json
   {"store": {"stars": 3.5, "stance_used": true, "checks": {"첫 단락 테제": {"pass": true, "note": ""}, "...": {}}},
    "critical": {"stance_used": true, "checks": {}}, "log": {"stance_used": false, "checks": {}}}
   ```
   - 분량은 `python3 -c`로 공백을 뺀 글자 수를 세어 확인한다.
   - 점검표는 내부 품질 관리용이며 진행 현황 페이지에는 보이지 않는다. 항목 이름과 note는 짧은 우리말로 쓴다(예: "요약보다 평가가 많다" — "내용 요약은 전체의 약 12%"). 앵커·용어를 넣지 않는다.
   - 실패한 항목이 있으면 고쳐서 다시 점검한다. 끝내 고칠 수 없는 것은 note에 이유를 쓴다.
6. `$BC progress $B`로 '한눈에 보기' 탭의 리뷰 칸에 세 편이 나오는지 확인한다 → `$BC mark $B review --files store.md,critical.md,log.md` → 체크포인트 → progress.html 보내기.
7. **보고**: 세 편의 제목과 분량, 서점 리뷰의 첫 문장과 별점, 점검에서 끝내 통과하지 못한 항목, 진행 현황 페이지 링크(`#overview`)를 알린다. 사용자 입장 없이 썼으면, 계기·가장 남은 점·권할 독자를 알려 주면 사용자의 목소리로 고쳐 쓴다고 알린다(my_stance.json을 책 폴더에 두어도 된다).

## 진행 현황 기록 (runtime.md 7절)

- `run-start run=bookc-7-review`, `stage-start stage=review`로 시작한다.
- 리뷰 한 편마다 `kind=other label=리뷰 store|critical|log` task를 기록한다. 세 편은 서로 독립이므로 서브에이전트 3개로 병렬로 써도 된다. 이 경우 1–3번의 재료와 사용자 관점을 각 작업자에게 넘긴다.
- 끝나면 `stage-end`, `run-end status=done`을 기록한다.

## 규칙

- **언어**: 독자에게 보이는 글은 모두 한국어로 쓴다. 원문 인용·용어는 한국어 뒤에 괄호나 인용으로 붙인다(conventions.md 7절). 원문 층(source.md)은 번역하지 않는다.
- 사용자의 경험·감정·이력을 지어내지 않는다.
- 저작권: 인용은 한 문장 이하로, 한 편에 3개 이내로 한다. 원문을 풀어 옮겨 쓰는 것도 길게 하지 않는다.
- 서점에 올리는 것은 사용자가 결정한다. Claude는 초안만 만든다. 초안 끝에 "AI 도움으로 작성" 같은 표기를 권할지는 사용자에게 맡긴다.
