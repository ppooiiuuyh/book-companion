---
name: bookc-2-parse
description: book-companion 2단계. 쪽 이미지와 초벌 OCR을 대조 교정해 장별 source.md(쪽·블록 앵커, 도표 이미지·판독표, 각주)를 만들고 lint·표본 감사를 통과시킨다. 끊긴 곳부터 이어서 한다. "/bookc-2-parse <책>", "책 파싱 계속", "원문 교정"에 쓴다.
---

# 2단계: 파싱 (원본 대조 교정 · 조립)

인자: PDF 경로·파일명·책 폴더 이름 중 하나. 선행 단계: 1(인테이크).

`PLUGIN/references/runtime.md`의 준비 → 책 찾기 → 내려받기를 한 다음, **선행 검사**를 한다.
```bash
$BC can $B parse || exit   # 불가하면 출력 안내문을 그대로 전하고 끝
```

## 절차

1. **남은 일 확인**: `$BC todo $B parse` → 장마다 남은 교정 쪽과 조립 필요 여부. 비어 있으면 8번(마무리)으로.
2. **작업 준비**: 쪽 이미지가 없으면 PDF를 스테이징해서
   `$BC prepare $B --pages ch:<남은 장들> --pdf "$PDF"` (쪽 이미지·OCR·draft 생성. 이미 교정된 쪽의 draft도 다시 만들어진다 — apply에 필요.)
3. **주석 장 먼저**: manifest `roles.notes`(없으면 label이 주석·미주·옮긴이 주인 뒷부분 장)가 아직 조립되지 않았으면 그 장부터 직접 교정한다(짧다). 각 주석 항목이 `N. 내용` 한 문단이 되게 한다. 그다음
   `$BC apply $B --pages ch:92 && $BC assemble $B --chapters 92 && $BC notes $B --chapters 92`
   → 이후 본문의 `[^n]`은 조립 때 자동으로 정의가 붙는다.
4. **분량 알림**: 새로 교정할 쪽이 50쪽 이상이면 `SendUserMessage`로 "남은 N쪽, 예상 토큰(쪽당 입력 약 4천·출력 약 0.6천)"을 한 줄 알리고 계속한다.
5. **교정 분배**: `PLUGIN/references/parse-worker.md`의 작업자 지시문으로 서브에이전트(general-purpose)를 띄운다.
   - 장 하나 = 작업자 하나. 25쪽이 넘는 장은 반으로 나눈다. **동시에 최대 4개**, 한 메시지에 여러 Agent 호출로 병렬 실행한다.
   - 작업자에게는 남은 쪽만 준다(`todo` 결과). 이미 있는 review 파일은 건너뛰라고 지시문에 들어 있다.
   - 서브에이전트가 한도·오류로 멈추면 `todo`로 남은 쪽을 다시 확인해 그 쪽만 새 작업자에게 준다.
6. **장별 마무리** (작업자가 끝난 장부터 차례로):
   ```bash
   $BC apply $B --pages ch:<id>
   $BC assemble $B --chapters <id>
   $BC lint $B --chapters <id>
   ```
   - errors가 있으면 원인 쪽의 review를 고쳐 다시 apply·assemble한다. warnings의 혼동형·%오인식·OCR 잔재는 해당 쪽 이미지를 보고 진짜 오류면 review에 반영, 책 그대로면 무시한다.
   - 새 혼동형은 `_work/confusions.json`에 합친다(다음 작업자가 참고).
   - 통과하면 `$BC mark $B parse --chapters <id>` → **체크포인트**(runtime.md 4절 올려 보내기).
7. **표본 감사**: 이번 실행에서 교정한 쪽 중 무작위로 장마다 1–2쪽(전체 최소 3쪽)을 골라 parse-worker.md의 감사자 지시문으로 맡긴다. 장마다 감사자 하나씩, 한 메시지에 여러 Agent 호출로 **병렬** 실행한다(최대 4). 불일치가 나오면 review를 고치고 해당 장을 다시 6번. 불일치율이 쪽당 3건을 넘으면 그 장 전체를 다른 작업자에게 재검토시킨다.
8. **마무리**: `$BC glossary $B` → 체크포인트 → `$BC status $B` 표와 함께 교정 통계(교정 쪽 수, 도표 수, unsure 목록, 감사 결과)를 짧게 보고한다. `unsure`가 남았으면 쪽 번호를 알려 주고 사용자 확인을 권한다.

## 규칙

- 교정의 정답은 쪽 이미지다. 초안(draft)이나 앞 장 결과를 근거로 고치지 않는다.
- 장 표지 쪽(`title_pages`)은 교정 대상이 아니다(`todo`에서 이미 빠져 있다).
- 이미 교정된 쪽을 다시 하려면 사용자가 요청한 경우에만 해당 `review/pNNN.json`을 새로 쓴다.
- 도표 판독은 보이는 수치만. 추정값은 "약", 겹쳐서 모르면 "불확실".
