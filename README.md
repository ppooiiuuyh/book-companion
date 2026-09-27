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
├── capture/eBookToPdf/    ← 0단계: 전자책 뷰어 화면 캡처 → PDF (Mac GUI, 사용자가 직접 실행)
├── plugin/                ← 스킬 플러그인 소스(skills·setup) + build.sh → plugin/dist/book-companion.plugin
└── experiments/           ← ocr-bakeoff(엔진 비교), pilot-eval(파일럿 검증)
```

## 0단계: 캡처 (PDF가 없을 때)

```bash
cd capture/eBookToPdf && poetry install && poetry run python eBookToPdf.py
```

- 저장 경로 기본값이 `books-pdf/`라서, 만든 PDF는 바로 `/bookc <파일명>`으로 부를 수 있습니다. 캡처 이미지와 로그는 `capture/eBookToPdf/_captures/`에 쌓이고 git에는 들어가지 않습니다.
- macOS에서 실행하는 터미널에 손쉬운 사용, 입력 모니터링, 화면 기록 권한을 줘야 합니다.
- GUI 도구라 Claude 세션에서는 실행할 수 없습니다. 원본은 eastshine12/eBookToPdf(MIT)이며, 원본 기록은 git에 병합되어 있습니다(원격 이름 `ebooktopdf`).

## git

- 책에서 나온 것은 올리지 않습니다: `books-pdf/`(원본 PDF), `books/`(책별 산출물), 실험의 쪽 이미지·정답·OCR 출력. 모두 `.gitignore`에 들어 있습니다.
- 올리는 것: 파이프라인 코드(`tools/`), 규약(`references/`), OCR 모델(`models/`), 플러그인 소스(`plugin/`), 캡처 도구(`capture/`), 실험 스크립트와 점수.
- 플러그인 빌드: `bash plugin/build.sh` 실행 후 `plugin/dist/book-companion.plugin`

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
