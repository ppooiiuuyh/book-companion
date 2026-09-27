---
name: bookc-1-intake
description: book-companion 1단계. 스캔 책 PDF에서 쪽 이미지를 꺼내고 장 구조(서문·장·뒷부분)를 검출·확인한 뒤 전 쪽 초벌 OCR을 한다. "/bookc-1-intake [pdf 경로 또는 파일명]", "책 인테이크", "책 구조 잡아줘"에 쓴다.
---

# 1단계: 인테이크

인자: PDF 경로 또는 `books-pdf/` 안의 파일명. 선행 단계 없음.

먼저 `PLUGIN/references/runtime.md`를 읽고 그 절차(준비 → 책 찾기 → 내려받기)를 따른다. `PLUGIN`은 이 스킬 폴더의 두 단계 위다. 아래에서 `B=WORK/books/<slug>`.

## 절차

1. **이미 끝났는지 확인.** `$BC status $B`에서 1단계가 "완료"면 그 표를 보여 주고 끝낸다. manifest는 있는데 미완료면 남은 부분(OCR 또는 구조 확인)만 한다.
2. **PDF 스테이징** (방식 A): `device_stage_files`로 PDF를 올린다. 스테이징 경로를 `PDF`라 부른다.
3. **추출·구조 검출** (manifest가 없을 때만):
   ```bash
   $BC intake $B --pdf "$PDF" [--title … --author … --translator … --publisher … --year …]
   ```
   서지 정보는 판권 쪽(보통 앞쪽 2–4쪽 또는 맨 끝 쪽)을 Read로 보고 채운다. 모르면 비워 둔다(제목은 파일명에서 자동).
4. **구조 확인** — 자동 검출은 틀릴 수 있으므로 반드시 눈으로 확인한다.
   - 출력된 장 목록의 각 시작 쪽(장 표지)과 그 앞 쪽을 `B/_work/pages/pNNN.jpg`로 Read해서 경계가 맞는지 본다. 목차 쪽이 있으면 목차와 대조한다.
   - 마지막 장의 끝 부분을 훑어 뒷부분(후기·옮긴이 후기·참고문헌·주석·찾아보기·저자 소개·판권)을 찾는다. 각각 `back=1`인 장으로 분리한다. id는 90부터.
   - 고치는 명령:
     ```bash
     $BC chapter $B edit 09 pages=209-215
     $BC chapter $B add 90 label=후기 pages=216-218 back=1
     $BC chapter $B add 92 label=주석 pages=222-223 back=1
     ```
     장 표지 쪽은 `title_pages=`로 지정한다(표지가 없는 장은 비워 둔다). 표지 쪽은 교정·조립에서 빠진다.
   - 인쇄 쪽 번호와 PDF 쪽 번호의 차이를 본문 쪽 하나로 확인해 기록한다: `$BC set $B printed_page_offset=8`
   - 책 끝 주석 장이 있으면 기록: `$BC set $B roles.notes='"92"'`
   - 다 맞으면 `$BC mark $B intake`
5. **초벌 OCR**: `$BC ocr $B` (이미 된 쪽은 건너뛴다. 200쪽 기준 2코어로 약 2분이므로 Bash timeout을 600000으로 준다. 중간에 끊기면 같은 명령을 다시 실행하면 남은 쪽만 한다.)
6. **분량 추정**: `$BC budget $B` 결과를 보관해 두었다가 끝에 보여 준다.
7. **체크포인트**: runtime.md 4절대로 올려 보낸다.
8. **보고**: `$BC outline $B`의 장 표와 `$BC status $B`, 분량 추정을 짧게 보여 주고, 다음 단계(`/bookc-2-parse`, `/bookc-3-research`)를 알려 준다.

## 진행 현황 기록 (runtime.md 7절)

- 선행 검사를 통과하면 `$BC log $B run-start run=bookc-1-intake`, 이어서 `$BC log $B stage-start stage=intake`를 기록하고 progress.html을 기기로 보낸다. 위치는 한 번 알린다. 선행 검사에서 불가하면 아무것도 기록하지 않는다.
- 추출(`label=추출`), 구조 확인(`label=구조`), OCR(`label=OCR`)을 각각 `kind=other` task로 기록한다.
- 끝나면 `stage-end`, `run-end status=done`을 기록하고 progress.html을 보낸다. 도중에 멈추면 `run-end status=stopped note=사유`를 기록한다.
## 주의

- `--force`로 intake를 다시 돌리면 장 구조가 새로 검출되어 수동 수정이 사라진다. 교정(review)이 이미 있으면 쓰지 않는다.
- 장 제목(`title`)을 바꾸면 폴더 이름(slug)도 바뀐다. 2단계 조립 이후에는 제목을 바꾸지 않는다.
- 원문 텍스트는 사용자의 개인 사본이다. 책 폴더 밖으로 내보내거나 공개 게시하지 않는다.
