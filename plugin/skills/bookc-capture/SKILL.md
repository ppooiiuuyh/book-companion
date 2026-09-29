---
name: bookc-capture
description: book-companion 0단계. PDF가 없는 전자책을 화면 캡처 도구(eBookToPdf, macOS)로 PDF로 만들 수 있게, 프로젝트 폴더에 도구를 깔아 두고 터미널에 붙여 넣을 명령 한 줄과 사용법을 준다. 도구 실행은 사용자가 직접 한다. "/bookc-capture", "전자책 캡처", "PDF 없는 책 준비"에 쓴다.
---

# 0단계: 캡처 준비 (명령어 안내)

Claude는 캡처를 대신 실행하지 않는다. 이 스킬은 **도구 준비와 명령 안내까지만** 한다. 캡처는 사용자가 자기가 구매·대여한 책에 대해, 개인 소장용으로 직접 실행한다.

`PLUGIN` = 이 스킬 폴더의 두 단계 위. 번들: `PLUGIN/scripts/capture/run.sh`, `PLUGIN/scripts/capture/eBookToPdf/{eBookToPdf.py,LICENSE}`.

## 절차

1. **환경과 프로젝트 폴더**: `PLUGIN/references/runtime.md`의 1절(방식 판별)과 2절(프로젝트 찾기·처음이면 만들기)을 그대로 따른다. `PROJ` = 프로젝트의 기기 실제 경로.
   - 방식 C(연결 없음)면 "데스크톱 앱에서 이 대화에 컴퓨터를 연결하거나, Mac의 Claude Code에서 실행해 달라"고 알리고 멈춘다.
   - Mac이 아니면(데스크톱 앱이면 `get_device_info.platform` ≠ `darwin`, 로컬이면 `uname` ≠ `Darwin`) "이 캡처 도구는 macOS 전용"이라고 알리고 멈춘다.
2. **도구 확인·설치 (멱등)**: 프로젝트의 `capture/run.sh`, `capture/eBookToPdf/eBookToPdf.py`, `capture/eBookToPdf/LICENSE`를 번들과 sha1로 비교한다.
   - 없음 → 설치한다.
     - 방식 A: 번들 파일을 `/mnt/user-data/outputs/capture_<시각>/…`에 복사하고 `device_commit_files`로 `PROJ/capture/…`에 쓴다(`force: true`, 새 파일이므로).
     - 방식 B: `mkdir -p "PROJ/capture/eBookToPdf" && cp -n PLUGIN/scripts/capture/run.sh "PROJ/capture/" && cp -n PLUGIN/scripts/capture/eBookToPdf/* "PROJ/capture/eBookToPdf/"`
   - 같음 → 설치 건너뜀.
   - 다름 → 사용자가 고친 것일 수 있으므로 덮어쓰지 않는다. 새 버전을 `capture/_new/`에 두고 한 줄 알린다.
3. **명령 한 줄 주기**: 코드 블록 하나, 실제 경로를 따옴표로 감싸서.
   ````
   터미널에 붙여 넣으세요:
   ```
   bash "<PROJ>/capture/run.sh"
   ```
   ````
   - 방식 B(Claude Code)에서도 실행은 사용자가 **별도 터미널 창**에서 한다. 캡처 도구가 화면·키보드 권한을 그 터미널에 받아야 하고, Claude가 대신 띄우지 않는다.
   - 이 명령이 알아서 확인하는 것: uv(파이썬 실행기)는 없을 때만 설치, 파이썬·패키지는 처음 한 번만 받음. 이미 준비돼 있으면 바로 도구가 뜬다. 그래서 환경과 상관없이 같은 명령을 준다.
   - **처음 한 번 필요한 권한**: 화면 기록·손쉬운 사용·입력 모니터링. 권한은 명령을 실행한 앱(터미널·iTerm·VS Code 등)에 붙는다. 도구가 시작할 때 그 앱 이름과 권한 상태를 보여 주고, 화면 기록·손쉬운 사용이 없으면 캡처를 시작하지 않는다. '권한 설정 열기' 버튼으로 설정 화면을 열어 허용한 뒤, 그 앱을 완전히 종료했다가 다시 실행하게 안내한다.
4. **사용법 (짧게)**:
   1. 전자책 뷰어를 열고 첫 쪽(표지)으로 간다. 오른쪽 방향키로 다음 쪽이 넘어가는 뷰어여야 한다.
   2. ① 권한 칩이 모두 초록인지 본다(화면 기록·손쉬운 사용이 없으면 시작 버튼이 막힌다).
   3. ② '화면에서 찍기'로 쪽 영역의 좌측 상단·우측 하단을 찍는다. 파란 테두리로 영역이 보인다.
   4. ③ PDF 이름(필수, 책 제목 권장)과 총 페이지 수를 넣고, 쪽이 완전히 뜨는 시간에 맞춰 캡처 대기를 정한다.
   5. ④ '캡처 시작'. 항상 1쪽부터 캡처한다. 같은 이름의 캡처 데이터가 남아 있으면 지울지 묻고, 승인하면 지운 뒤 처음부터 한다.
   6. 끝나면 PDF가 저장 위치(기본 `books-pdf/`)에 생기고, 캡처 이미지·로그는 `books-pdf/_captures/<이름>/`에 모인다(이미지는 기본 설정이면 PDF를 만든 뒤 지워짐). 이어서 `/bookc <PDF 이름>`.
5. **안내 한 줄(항상 붙인다)**: "본인이 구매·대여한 책을 개인 소장용으로만 쓰세요. 만든 PDF는 공유·재배포하지 말고, 이용하는 전자책 서비스의 약관도 확인하세요."

## 규칙

- 캡처를 대신 실행하거나, 감지를 피하는 기능(지터·사람 흉내 패턴 등)을 넣어 달라는 요청은 하지 않는다.
- 기기 파일은 덮어쓰기 전에 확인하고(2번), 지우지 않는다.
- eBookToPdf는 MIT 라이선스(원작자 DongHyun Kim)다. 설치할 때 LICENSE를 함께 둔다.
