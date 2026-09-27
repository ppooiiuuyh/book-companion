# book-companion

스캔 책 PDF를 Claude와 "같이 읽기" 위한 지식 베이스로 만드는 도구입니다. 쪽 앵커가 붙은 원문을 만들고, 그 위에 요약·조사·통독 층을 쌓습니다.
설계서는 바탕화면 `book-companion/book-companion-design-v0.1.html`에 있습니다.

## 폴더

```
book-companion/
├── tools/bc.py            ← CLI
├── tools/bookc/           ← intake · ocr · layout · apply · assemble · lint · glossary · budget · state · outline
├── references/conventions.md  ← 층 분리·주소·교정(review JSON) 규약
├── models/tessdata/       ← Tesseract 한국어 모델(tessdata_fast) + 출력 설정
├── books/하류사회/          ← 책 하나의 지식 베이스
│   ├── 00_서문/source.md, 01_중류화에서_하류화로/source.md (+ img/)
│   ├── glossary.md
│   └── _work/manifest.json, review/*.json   ← 기계 기록 중 보존할 것
├── books-pdf/             ← PDF 보관 (/bookc <파일명> 은 여기서만 찾음)
├── plugin/                ← 스킬 패키지(.plugin)
└── experiments/           ← ocr-bakeoff(엔진 비교), pilot-eval(파일럿 검증)
```

## 파이프라인

```bash
PY=python3   # 필요 패키지: pymupdf pillow numpy rapidfuzz kiwipiepy, 시스템: tesseract 5
B=books/하류사회
$PY tools/bc.py intake   $B --pdf 하류사회.pdf --title 하류사회 --author "미우라 아츠시"   # 쪽 이미지 추출, 장 검출
$PY tools/bc.py ocr      $B                     # 초벌 OCR (224쪽 약 2분, 2코어)
$PY tools/bc.py layout   $B --pages ch:00,01    # 줄 유형·문단·도표 영역 → _work/draft/pNNN.md
#   ↳ Claude가 쪽 이미지와 draft를 대조해 _work/review/pNNN.json 작성 (규약: references/conventions.md)
$PY tools/bc.py apply    $B --pages ch:00,01    # review 적용 → _work/final/pNNN.json
$PY tools/bc.py assemble $B --chapters 00,01    # 장별 source.md + 도표 크롭
$PY tools/bc.py lint     $B --chapters 00,01    # 품질 게이트
$PY tools/bc.py glossary $B
```

`_work/`의 pages·ocr·layout·draft·final은 다시 만들 수 있어서 저장하지 않습니다. `review/`(교정 기록)와 `manifest.json`만 보존합니다.

## 진행 상태 (2026-09-28)

| 단계 | 상태 |
|---|---|
| 인테이크 | 완료 (224쪽, 서문·8장·마치며 + 후기·참고문헌·주석·저자소개) |
| 초벌 OCR | 완료 (224쪽) |
| 파일럿 교정·조립 | **서문 + 1장 완료 (p005–025)** → 게이트 A 검토 대기 |
| 나머지 장 | 미착수 |
| 조사 · 통독 · 요약 | 미착수 |
| 스킬화 | 완료(v0.2, 병렬 파동 실행) — `plugin/book-companion.plugin` (`/bookc`, `/bookc-1-intake` … `/bookc-5-synthesize`, `/bookc-status`, `/bookc-open`) |

파일럿 결과는 `experiments/pilot-eval/REPORT.md`에 있습니다.
