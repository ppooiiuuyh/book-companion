# 실행 환경·책 찾기·동기화 (모든 bookc 스킬 공통)

## 0. 용어

- `PLUGIN` = 스킬 기본 폴더(`Base directory for this skill`)의 두 단계 위. `PLUGIN/scripts/tools/bc.py`가 CLI다.
- `PROJECT` = 사용자의 book-companion 프로젝트 폴더. **위치는 정해져 있지 않다.** 맨 위에 표식 파일 `book-companion.json`이 있는 폴더가 프로젝트다(아래 2절에서 찾는다). 폴더 이름·위치를 문서나 안내문에 박아 두지 않고, 항상 찾아낸 실제 경로를 쓴다.
  - `PROJECT/book-companion.json` : 표식 `{"kind": "book-companion", "version": 1, "id": "<무작위 12자>", "created": "<날짜>"}`
  - `PROJECT/books-pdf/` : PDF 보관 (파일명만 주면 여기서만 찾는다)
  - `PROJECT/books/<slug>/` : 책 하나의 지식 베이스
  - `PROJECT/capture/` : 캡처 도구(`/bookc-capture`가 설치)
- 프로젝트 안의 모든 경로(링크, manifest, 진행 현황 페이지)는 `PROJECT` 기준 상대 경로다. 그래서 폴더를 통째로 옮겨도 안의 작업은 깨지지 않는다.
- `WORK` = 실제로 처리하는 작업 사본의 루트. 아래 두 방식 중 하나.

## 1. 방식 고르기 (환경 판별)

도구 목록과 셸로 판단한다. 사용자에게 묻지 않는다.

| 방식 | 판별 | WORK | 동기화 |
|---|---|---|---|
| A. 클라우드 + 기기 | `mcp__remote-devices__*` 도구가 있다 (Claude 데스크톱 앱, 컴퓨터 연결) | `/home/claude/bookc` | 필요 (아래 4절) |
| B. 로컬 | 그 도구가 없고, 이 셸이 사용자 컴퓨터다(Claude Code 등. macOS면 `uname` = `Darwin`) | `PROJECT` | 없음 |
| C. 연결 없음 | 둘 다 아니다(클라우드 셸만 있음) | – | 사용자 파일에 닿지 않는다. 데스크톱 앱에서 컴퓨터를 연결하라고 안내하고 멈춘다 |

방식 A에서는 쪽 이미지를 Read로 봐야 하고 기기 VM에는 tesseract 5와 패키지 설치 권한이 없을 수 있으므로, 처리는 클라우드 작업 사본에서 한다.

## 2. 준비와 프로젝트 찾기 (세션마다)

```bash
eval "$(bash PLUGIN/scripts/setup.sh | tail -1)"     # → $PY 설정. 이미 준비됐으면 즉시 끝남
BC="$PY PLUGIN/scripts/tools/bc.py"
```

### 2.1 찾기 순서

**방식 A (데스크톱 앱)**
1. `mcp__remote-devices__get_device_info`의 `connectedFolders`를 본다. 각 폴더는 `device_bash`에서 `$HOME/mnt/<폴더 이름>`이다.
2. 표식이 있는 폴더를 찾는다: `for d in $HOME/mnt/*/; do [ -f "$d/book-companion.json" ] && echo "$d"; done`
   - 연결 폴더의 **하위**에 프로젝트가 있을 수도 있다(상위 폴더를 연결한 경우): `find $HOME/mnt -maxdepth 3 -name book-companion.json`
3. **예전 사용자 호환**: 표식은 없지만 `books-pdf/`와 `books/`가 둘 다 있는 폴더는 기존 프로젝트로 보고, 표식을 조용히 만들어 둔다(2.3의 명령).
4. 결과
   - 하나 → 그 폴더가 `PROJECT`. `DEV` = 그 폴더의 `$HOME/mnt/…` 경로, 기기 실제 경로 = connectedFolders의 값(+하위 경로).
   - 여럿 → 폴더 이름과 책 수를 보여 주고 AskUserQuestion으로 고르게 한다. 표식의 `id`가 같은 것이 둘이면 "복사본으로 보인다"고 알린다.
   - 없음 → 2.2.

**방식 B (Claude Code 등 로컬)**
1. 환경 변수 `BOOKC_HOME`이 있고 그 안에 표식이 있으면 그것.
2. `~/.config/book-companion/config.json`의 `"project"` 경로에 표식이 있으면 그것.
3. 현재 폴더와 그 상위 폴더에서 표식을 찾는다.
4. 설정 경로가 있는데 표식이 없으면 **옮겨진 것**으로 본다. macOS면 `mdfind -name book-companion.json 2>/dev/null`(없으면 `find ~ -maxdepth 4 -name book-companion.json`)로 다시 찾는다. 같은 `id`를 찾으면 config를 새 경로로 고치고 "폴더가 옮겨져 새 위치를 씁니다: …"라고 한 줄 알린다.
5. 그래도 없으면 2.2.

### 2.2 못 찾았을 때 (한 번만 묻는다)

"없음"을 곧바로 "처음 사용"으로 보지 않는다. 폴더를 옮겨 연결이 끊긴 것일 수 있다. AskUserQuestion 한 번:

- **기존 폴더가 있다(옮겼다)** → 방식 A: 그 폴더를 앱에서 연결해 달라고 하거나, 위치를 말해 주면 `device_request_folder_access`로 요청한다. 연결되면 2.1을 다시 한다. 방식 B: 위치를 받아 config에 적는다.
- **처음이다(새로 만들기)** → 위치를 고르게 한다. 추천: `~/BookCompanion`. 선택지로 `~/Documents/BookCompanion`, 직접 입력.
  - 방식 A: 폴더가 없으면 만들 수 없으므로 그 **상위 폴더**를 `device_request_folder_access`로 요청한다(홈 폴더 자체는 요청할 수 없으니 `~/Documents` 같은 하위 폴더를 쓰거나, 사용자에게 빈 폴더를 만들어 연결해 달라고 한다). 연결되면 2.3으로 만든다.
  - 방식 B: 바로 만들고 config에 적는다.

### 2.3 만들기·표식 달기 (멱등)

```bash
cd "<PROJECT>" && mkdir -p books-pdf books capture
[ -f book-companion.json ] || python3 - <<'EOF'
import json, secrets, datetime
json.dump({"kind": "book-companion", "version": 1, "id": secrets.token_hex(6),
           "created": datetime.date.today().isoformat()}, open("book-companion.json", "w"), ensure_ascii=False, indent=1)
EOF
```
방식 B에서는 이어서 `~/.config/book-companion/config.json`에 `{"project": "<PROJECT 절대 경로>"}`를 쓴다.
만들었거나 옮겨진 것을 찾았으면 실제 경로를 한 줄로 알린다. 그 뒤로는 묻지 않는다.

## 3. 책 찾기 (인자 해석)

인자 `ARG`를 받으면:

1. **경로**(`/` 포함 또는 `~`로 시작): 그 PDF를 쓴다. `books-pdf/` 밖에 있으면 `cp -n`으로 `books-pdf/`에 복사해 두고, 복사했다고 한 줄 알린다(다음부터 파일명으로 부를 수 있게).
2. **파일명**: `books-pdf/`에서만 찾는다. macOS 파일명은 NFD일 수 있으므로 NFC로 정규화해 비교한다.
   - 정확히 같은 이름 → 그 파일. `.pdf`를 빼고 줘도 된다.
   - 아니면 부분 일치. 여러 개면 목록을 보여 주고 AskUserQuestion으로 고르게 한다. 없으면 `books-pdf/` 목록을 보여 주고 멈춘다. 이때 PDF가 아직 없는 전자책이면 `/bookc-capture`(0단계: 캡처 도구 준비와 터미널 명령 안내, 사용자가 직접 실행, 결과는 `books-pdf/`)로 만들 수 있다고 한 줄 안내한다.
   ```bash
   python3 - <<'EOF'
   import unicodedata, pathlib, sys
   q = unicodedata.normalize("NFC", "ARG").removesuffix(".pdf").lower()
   for p in sorted(pathlib.Path("DEV/books-pdf").glob("*.pdf")):
       n = unicodedata.normalize("NFC", p.stem).lower()
       print(("=" if n == q else "~" if q in n else " "), p.name)
   EOF
   ```
3. **인자 없음**: `books/*/_work/manifest.json`이 있는 책 목록과 상태를 보여 준다. 진행 중인 책이 하나뿐이면 그 책으로 이어 간다.
4. **책 폴더(slug) 정하기**: 이미 만든 책이 있는지 먼저 본다(manifest의 `pdf.name`이 같거나, 이름이 달라도 `pdf.sha1`이 같은 책). 있으면 그 slug로 **이어서** 한다. 없으면 파일명에서 괄호 부분을 뺀 이름(공백→`_`)을 slug로 쓴다. 인자가 책 폴더 이름이면 `books/<인자>/`를 바로 쓴다.
   ```bash
   python3 - <<'EOF'
   import json, pathlib, unicodedata, hashlib
   N = lambda s: unicodedata.normalize("NFC", s)
   pdf = pathlib.Path("PDF경로"); sha = None
   ms = [(m, json.loads(m.read_text()).get("pdf", {})) for m in pathlib.Path("DEV/books").glob("*/_work/manifest.json")]
   hit = [m for m, p in ms if N(p.get("name", "")) == N(pdf.name)]
   if not hit:
       sha = hashlib.sha1(pdf.read_bytes()).hexdigest()
       hit = [m for m, p in ms if p.get("sha1") == sha]
   print(hit[0].parent.parent.name if hit else "")
   EOF
   ```

## 4. 동기화 (방식 A)

작업 사본 `WORK/books/<slug>`와 기기 `DEV/books/<slug>`를 tgz 한 개로 주고받는다. 다시 만들 수 있는 `_work/{pages,layout,draft,final}`은 옮기지 않는다.

**내려받기 (스킬 시작 시 한 번)**
1. 기기에 책 폴더가 있으면 `device_bash`:
   `cd DEV/books/<slug> && tar czf _work/_down.tgz --exclude=./_work/pages --exclude=./_work/layout --exclude=./_work/draft --exclude=./_work/final --exclude='*.tgz' .`
2. `device_stage_files`로 그 tgz를 올리고, `$BC unpack WORK/books/<slug> <stagedPath>`.
3. PDF도 스테이징한다(쪽 이미지를 만들어야 하는 단계만: 1·2단계). 이미 `WORK`에 쪽 이미지가 다 있으면 생략.

**올려 보내기 (체크포인트마다)**
1. `$BC pack WORK/books/<slug> /mnt/user-data/outputs/bookc_<slug>_$(date +%s).tgz` — **매번 새 파일 이름**을 쓴다. 같은 stagedPath를 다시 커밋하면 예전 내용이 전달될 수 있다.
2. `SendUserFile` 없이 `device_commit_files`에 `stagedPath`로 넘겨 `…/books/<slug>/_work/_up.tgz`에 쓴다(`force: true`). 기기에서 `ls -l`로 크기가 클라우드 쪽 파일과 같은지 확인한다.
3. `device_bash`: `cd DEV/books/<slug> && tar xzf _work/_up.tgz --overwrite` — `--overwrite`가 꼭 필요하다. 기기에서는 파일을 지울 수 없어서, 이 옵션이 없으면 tar가 기존 파일을 덮어쓰지 못한다.

체크포인트: 인테이크 끝, 장 하나 조립·lint 통과, 조사 끝, 통독 장 하나 끝, 종합 끝. 끊겨도 마지막 체크포인트부터 이어진다. 기기가 응답하지 않으면 작업은 `WORK`에서 계속하고, 다시 연결되면 올려 보낸다(사용자에게 한 줄 알림).

기기 파일은 지울 수 없다(삭제 권한 없음). `_down.tgz`·`_up.tgz`는 매번 덮어쓴다.

## 5. 이어 하기 규칙

- 상태는 모두 `_work/manifest.json`의 `status`와 파일 존재로 판단한다. 판단은 스크립트에 맡긴다: `$BC status`, `$BC can <stage>`, `$BC next`, `$BC todo parse|read`.
- 이미 된 쪽·장은 다시 하지 않는다(`review/pNNN.json`이 있으면 그 쪽은 교정 완료).
- 사용자에게 진행을 보여 줄 때는 `$BC status` 표를 그대로 보여 준다.

## 6. 선행 단계 검사 (단계 스킬 공통 첫 동작)

```bash
$BC can WORK/books/<slug> <stage>
```
exit 1이면 출력된 안내문을 사용자에게 그대로 전하고 **아무 작업도 하지 않고 끝낸다.** (그 단계에 필요한 선행 스킬 이름이 안내문에 들어 있다.)

| 단계 | 스킬 | 선행 조건 |
|---|---|---|
| 1 intake | /bookc-1-intake | 없음 |
| 2 parse | /bookc-2-parse | 1 |
| 3 research | /bookc-3-research | 1 |
| 4 read | /bookc-4-read | 2, 3 |
| 5 synthesize | /bookc-5-synthesize | 4 |
| 6 insight | /bookc-6-insight | 5 |
| 7 review | /bookc-7-review | 6 |

## 7. 진행 현황 기록 (progress.html)

모든 bookc 스킬은 작업을 이벤트로 남긴다. 그러면 책 폴더의 `progress.html`(진행 대시보드)이 다시 그려진다.
대시보드에는 전체 진행률, 경과·누적 시간, 동시 작업자 수, 예상 남은 시간, 단계별 막대, 작업자별 병렬 타임라인, 동시 작업 수·누적 교정 쪽수 그래프, 장별 현황 격자, 작업·이벤트 기록이 나온다.

```bash
export BOOKC_PROGRESS_COPY_DIR=/mnt/user-data/outputs/progress   # 방식 A: 매번 새 이름의 사본을 만들고 그 경로를 마지막 줄에 출력
$BC log $B run-start run=bookc                 # 스킬 이름 (bookc, bookc-2-parse …)
$BC log $B stage-start stage=parse             # 단계 스킬만. stage: intake|parse|research|study|read|synthesize|insight|review
$BC log $B wave-start wave=3                   # /bookc 파동만
$BC log $B task-start task=parse:04a kind=parse chapter=04 pages=20 lane=1 label=04a
$BC log $B task-end task=parse:04a status=ok   # 실패: status=fail note=이유
$BC log $B wave-end wave=3
$BC log $B stage-end stage=parse
$BC log $B run-end status=done                 # 도중에 멈추면 stopped, 실패로 끝나면 failed
```

- **이벤트 값**
  - `kind`는 parse, research, study, read, other 중 하나다. 인테이크, 직접 하는 조립·lint, 감사, 조사 병합, 종합은 other로 적는다.
  - `task`는 한 실행 안에서 겹치지 않게 짓는다. 실패한 작업을 다시 시작하면 같은 이름을 써도 된다(재시도로 표시됨).
  - `lane`은 작업자 번호(1–4)다.
  - 한 파동의 task-start 여러 개는 `&&`로 이어 Bash 한 번에 기록한다.
- **기기로 보내기 (방식 A)**
  - log 출력의 마지막 줄이 사본 경로다. 이 경로를 `device_commit_files`에 넘긴다: stagedPath는 그 경로, devicePath는 `…/books/<slug>/progress.html`, `force: true`.
  - 보내는 때는 세 번이다: 작업자를 띄우기 직전(task-start 기록 뒤), 파동이나 단계가 끝나고 후처리를 마친 뒤, 실행이 끝났을 때.
  - 방식 B(로컬)는 책 폴더에 바로 쓰이므로 보낼 필요가 없다.
- **처음 보낸 뒤**, 사용자에게 한 번만 알린다.
  - 알릴 내용: 진행 현황은 `<PROJECT>/books/<slug>/progress.html`(실제 경로로)이고, 브라우저로 열어 두면 실행 중에는 20초마다 새로 고쳐진다.
  - computer:// 링크를 함께 준다.
- **작업자가 도는 동안**에는 파일이 새로 쓰이지 않는다. 대신 페이지가 진행 중인 작업의 경과 시간과 '지금' 선을 스스로 움직인다.
- **run-end 없이 끊긴 실행**은 다음 실행이 시작되면 '중단됨'으로 표시된다.
