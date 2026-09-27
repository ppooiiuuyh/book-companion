# book-companion

스캔 책 PDF를 Claude와 같이 읽는 지식 베이스로 만듭니다. 결과물은 쪽 앵커가 붙은 Markdown 원문, 도표 이미지와 판독표, 요약, 통독 메모, 외부 조사입니다.

## 명령

| 명령 | 하는 일 | 선행 |
|---|---|---|
| `/bookc <pdf>` | 전체 실행. 2·3·4단계를 장 단위로 겹쳐 병렬(최대 4) 실행하고, 끊겼으면 이어서 합니다 | – |
| `/bookc-1-intake <pdf>` | 쪽 이미지 추출, 장 구조 확인, 초벌 OCR | – |
| `/bookc-2-parse <책>` | 이미지와 대조해 교정하고 장별 source.md로 조립 | 1 |
| `/bookc-3-research <책>` | 서점·블로그·기사·원서 반응 4개 영역을 병렬 조사한 뒤 병합 | 1 |
| `/bookc-4-read <책>` | 1차: 장별 요약·도표 읽기(병렬), 2차: 앞에서부터 통독 메모(순차) | 2, 3 |
| `/bookc-5-synthesize <책>` | 책 요약(index.md)과 외부 평가 대조(synthesis.md) | 4 |
| `/bookc-status [책]` | 진행 상태 | – |
| `/bookc-open <책>` | 만든 지식 베이스로 대화 | 2 일부 |

PDF가 없는 전자책은 먼저 `~/project/book-companion/capture/eBookToPdf`로 화면을 캡처해 PDF를 만듭니다(사용자가 직접 실행하며, 결과는 `books-pdf/`에 저장됩니다).

`<pdf>`에는 경로나 파일명을 씁니다. 파일명만 쓰면 `~/project/book-companion/books-pdf/`에서만 찾습니다. 선행 단계가 끝나지 않은 단계 명령은 실행하지 않고, 무엇이 먼저 필요한지 알려 줍니다.

## 폴더

```
~/project/book-companion/
├── books-pdf/            PDF 보관
└── books/<책>/
    ├── index.md          입구: L0 요약·목차·핵심 개념 (5단계)
    ├── synthesis.md      독해 ↔ 외부 평가 대조 (5단계)
    ├── glossary.md
    ├── NN_장/source.md   원문 (+ img/)       (2단계)
    ├── NN_장/study.md    L1·L2 요약          (4단계)
    ├── reading/          통독 메모, _carry.md (4단계)
    ├── research/         sources·highlights·critiques·watchlist, _parts/(영역별 원자료) (3단계)
    ├── progress.html     진행 현황 대시보드(단계·경과 시간·진행률·병렬 타임라인). 실행 중 20초마다 새로 고침
    └── _work/            manifest(진행 상태), OCR, 교정 기록, runlog.jsonl(실행 기록)
```

## 구성

- `scripts/tools/bc.py`: CLI (intake · ocr · prepare · layout · apply · assemble · lint · notes · glossary · outline · status · can · next · todo · ready · mark · log · progress · chapter · set · pack · unpack)
- `scripts/models/tessdata/`: Tesseract 한국어 모델(tessdata_fast)과 출력 설정
- `scripts/setup.sh`: tesseract와 python 패키지(pymupdf, pillow, numpy, rapidfuzz, kiwipiepy)를 준비합니다
- `references/`: conventions(층·주소·교정 규약), runtime(환경·책 찾기·동기화), parse-worker(교정·감사 지시문)

## 비용 감각

200쪽, 약 20만 자 책 기준입니다. 파싱 교정은 입력 약 0.8M 토큰, 출력 약 0.12M 토큰이 듭니다. 통독은 두 번에 나눠 읽어 원문 약 15만 토큰 × 약 1.8에 메모와 요약 출력이 더해집니다(한 번 읽을 때보다 15–20% 늘지만 1차를 병렬로 돌려 시간은 줄어듭니다). 기계 처리(OCR·조립)는 몇 분이면 끝납니다.
