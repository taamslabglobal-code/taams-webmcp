# Demo video script — TAAMs Import Sourcing Desk (WebMCP Challenge)

Target length **2:55** (hard limit 3:00 — going over risks disqualification).
English narration is written to be read aloud as-is. Filming directions are in
Korean, in their own column.

- Live page: https://taams-sourcing-desk.netlify.app
- Recording: 1920×1080, 30fps, browser at 100% zoom
- Narration: recorded separately, laid over the screen capture (do **not** try
  to speak while clicking — timings will drift)

**One-sentence spine of the whole video:**
> An agent that operates the page you are looking at, and still cannot send
> anything without you.

**The single question that drives the demo:**
> "Thai mango or Brazilian? Who should I buy from?"

> ⚠ 숫자 규칙: 아래 표에 있는 수치만 쓴다. 새 숫자를 만들거나 반올림하지 않는다.
> 시장규모·수상 가능성 등 검증되지 않은 주장은 나레이션에도 자막에도 넣지 않는다.

---

## 1. Timeline

| Time | 화면 (촬영 지시) | Narration (read as written) | Sec |
|---|---|---|---|
| **0:00–0:13** | 검은 화면. 흰 텍스트 두 줄만 순차 페이드인: `Is this a real supplier?` → `Is this a real price?` 페이지는 아직 보여주지 않는다. | Buying food from another country starts with two questions. Is this a real supplier? And is this a real price? Neither of them is a software question. | 13 |
| **0:13–0:26** | 검은 배경 유지, 텍스트만 교체: `customs portals` / `cold calls` / `guesswork` 세 단어를 0.8초 간격으로 쌓는다. (스톡 이미지·몽타주 쓰지 말 것 — 저작권 리스크, 그리고 텍스트가 더 빠르다) | Today a buyer answers them by hand. Government customs portals. Cold calls. Guessing whether a quoted price is normal. All of this happens before one quote is even sent. | 13 |
| **0:26–0:48** | 컷 → 라이브 페이지 전체(3열). 좌측 검색창에 사람이 직접 `mango` 를 **한 글자씩** 타이핑(자동완성 드롭다운 보이게) → 결과 클릭. 품목 카드·스파크라인·`Active Korean importers` 목록이 채워지는 것을 끊지 말고 그대로 보여준다. `$5.07/kg` 파란 pill 이 뜨는 순간 0.5초 정지. | This is a normal web page. I type a product, and I get real Korean customs records. Mango: four thousand, three hundred and sixty-eight clearances in 2025. Nine supplying countries. Five dollars and seven cents per kilogram, last month. No agent involved yet. This is just a mouse and a keyboard. | 22 |
| **0:48–1:00** | 우상단 녹색 배지 **`Agent tools: 7 ready`** 로 커서 이동 후 1초 머무름 → 화면 확대(1.4배) 2초 → 원래 배율 복귀. 이어서 브라우저 에이전트 사이드패널을 연다. 패널 입력창에 질문을 타이핑하고 **엔터는 아직 누르지 않는다**(다음 구간 시작과 맞춤). | Same page, now in an agent-capable browser. Seven tools are registered with WebMCP. So I can just ask: Thai mango or Brazilian? Who should I buy from? | 12 |
| **1:00–1:26** | 엔터. 이후 **카메라는 사이드패널이 아니라 페이지 본문에 둔다.** 우측 `Agent Activity` 로그가 한 줄씩 쌓이는 것과, 그때마다 좌·중앙이 바뀌는 것을 같은 프레임에 담는다. 국가 칩 줄(태국 3310 / 브라질 651 / 베트남 243…)이 렌더될 때 0.5초 정지. 채팅 답변 텍스트는 클로즈업하지 않는다. | Watch the page, not the chat. The agent resolves the product name, pulls twelve months of unit prices, ranks a hundred and twenty-five overseas suppliers, and lists a hundred and seventy-five Korean importers already buying this. Every call lands on my screen, in place. There is no summary for me to copy back into the tool. | 26 |
| **1:26–1:52** | **이 구간이 이 영상의 핵심이다.** 사전에 DevTools Network 탭을 화면 하단에 열어두고 필터를 비운 뒤 **Clear** 해 둔다. 에이전트가 pin → highlight 를 실행: 중앙 비교보드 슬롯에 카드가 꽂히고, `태국 (Thailand) 3310` 칩이 파랗게 켜지며 **브라질 행이 회색으로 디밍**된다. 디밍되는 순간 커서로 브라질 행을 한 번 훑어 "사라지지 않았음"을 보여준다. 동시에 Network 탭이 **비어 있는 것**을 2초간 보여준다(빨간 화살표 자막 `0 requests` 권장). | Now the part a remote server cannot do. Pin it to the board. Highlight Thailand. Look at the network tab: nothing fires. These two tools fetch nothing. They rearrange what is already in front of me. Brazil is dimmed, not deleted. A remote MCP server can return better JSON. It cannot know that a table is on my screen. | 26 |
| **1:52–2:26** | 에이전트가 `draft_sourcing_request` 실행 → 소싱요청 카드가 채워진다(품목·공급사 `AROY FARM CO LTD`·수량·비고). 이어서 승인 모달 `Approve sourcing request?` 가 뜬다. **모달을 1.4배로 확대해 4초간 정지** — `Nothing is sent until you click Approve.` 문구와 초안 4항목이 읽히도록. 그다음 사람이 커서를 천천히 옮겨 `Approve & open email` 을 클릭. 메일 클라이언트가 **미리 채워진 상태로** 열리는 것을 보여주고, **보내기는 누르지 않는다.** | Last, the agent drafts a sourcing request to a named Thai supplier. Then it stops. It has authority to prepare, and no authority to send. The page shows me exactly what is about to leave: product, supplier, quantity, notes. I read it. I click Approve. Only then does an email open, from my own mail client, and I am still the one who presses send. If I cancel, the draft stays on screen and nothing goes out. | 34 |
| **2:26–2:42** | 페이지로 복귀. 사람이 **손으로** 직접: 다른 품목 카드의 `Pin to comparison board` 클릭 → 국가 칩 `브라질 (Brazil) 651` 클릭(하이라이트 전환) → `Draft sourcing request` 클릭. 세 동작을 끊김 없이 한 테이크로. 이때 우측 로그에 사람 표시 줄이 쌓이는 것을 함께 보여준다. | And every one of those actions is a button. Search, pin, highlight, draft — I can click them all myself. The agent uses the same functions I do. That is the whole idea. | 16 |
| **2:42–2:55** | 화면을 서서히 축소(0.9배)하며 페이지 전체가 보이게 → 하단에 URL 자막 `taams-sourcing-desk.netlify.app` 고정 → 마지막 2초 검은 화면에 URL + `MIT licensed`. | TAAMs Import Sourcing Desk. One point three million Korean customs records, one page, seven WebMCP tools. A person and an agent sourcing together — and the person still signs off. | 13 |

**총 2:55.**

---

## 2. On-screen text (자막) — 최소한만

자막은 나레이션을 반복하지 않는다. 아래 5개만 넣는다.

| 시점 | 자막 |
|---|---|
| 0:26 | `Live data — Korean customs clearance records` |
| 1:00 | `Tier A — lookup (4 tools)` |
| 1:26 | `Tier B — screen control (2 tools) · 0 network requests` |
| 1:52 | `Tier C — action, gated by a human (1 tool)` |
| 2:26 | `Same buttons, by hand` |

Tier 라벨 3개가 이 영상의 뼈대다. 다른 자막을 늘려서 이 세 개가 묻히게 하지 말 것.

---

## 3. Narration only (읽기 연습용)

**386 words · 140 wpm 기준 약 2분 45초** (구간 사이 호흡 포함 2:55).
한 문장에 주장 하나. 문장 끝에서 반드시 한 박자 쉰다.

> Buying food from another country starts with two questions. Is this a real
> supplier? And is this a real price? Neither of them is a software question.
>
> Today a buyer answers them by hand. Government customs portals. Cold calls.
> Guessing whether a quoted price is normal. All of this happens before one
> quote is even sent.
>
> This is a normal web page. I type a product, and I get real Korean customs
> records. Mango: four thousand, three hundred and sixty-eight clearances in
> 2025. Nine supplying countries. Five dollars and seven cents per kilogram,
> last month. No agent involved yet. This is just a mouse and a keyboard.
>
> Same page, now in an agent-capable browser. Seven tools are registered with
> WebMCP. So I can just ask: Thai mango or Brazilian? Who should I buy from?
>
> Watch the page, not the chat. The agent resolves the product name, pulls
> twelve months of unit prices, ranks a hundred and twenty-five overseas
> suppliers, and lists a hundred and seventy-five Korean importers already
> buying this. Every call lands on my screen, in place. There is no summary for
> me to copy back into the tool.
>
> Now the part a remote server cannot do. Pin it to the board. Highlight
> Thailand. Look at the network tab: nothing fires. These two tools fetch
> nothing. They rearrange what is already in front of me. Brazil is dimmed, not
> deleted. A remote MCP server can return better JSON. It cannot know that a
> table is on my screen.
>
> Last, the agent drafts a sourcing request to a named Thai supplier. Then it
> stops. It has authority to prepare, and no authority to send. The page shows
> me exactly what is about to leave: product, supplier, quantity, notes. I read
> it. I click Approve. Only then does an email open, from my own mail client,
> and I am still the one who presses send. If I cancel, the draft stays on
> screen and nothing goes out.
>
> And every one of those actions is a button. Search, pin, highlight, draft — I
> can click them all myself. The agent uses the same functions I do. That is
> the whole idea.
>
> TAAMs Import Sourcing Desk. One point three million Korean customs records, one
> page, seven WebMCP tools. A person and an agent sourcing together — and the
> person still signs off.

### 발음 메모 (읽기 전 3회 소리내어 연습)

| 표기 | 읽는 법 |
|---|---|
| 4,368 | "four thousand, three hundred and **sixty-eight**" — 콤마에서 반드시 끊는다 |
| $5.07/kg | "five dollars and seven cents per kilogram" |
| 125 / 175 | "a hundred and twenty-five" / "a hundred and seventy-five" |
| 1,318,602 | 숫자로 읽지 않는다 — "one point three million" |
| WebMCP | "web-em-see-pee" (한 단어로 뭉치지 않기) |
| JSON | "jay-sun" |

문장이 길게 느껴지면 **속도를 올리지 말고 문장을 자른다.** 빠르게 읽은 영어는
심사위원에게 정보가 되지 않는다.

---

## 4. 녹화 전 체크리스트

녹화 직전 위에서 아래로 한 번에 확인한다. 하나라도 빠지면 재촬영이다.

**브라우저**
- [ ] Chrome 151, `chrome://flags/#enable-webmcp-testing` **Enabled** + 재시작 완료
- [ ] `probe.html` 을 먼저 열어 4개 체크 전부 통과 확인 (통과 못 하면 촬영 자체가 무의미)
- [ ] 확대율 **100%** (`Ctrl+0`). 다른 배율이면 레이아웃이 3열에서 무너진다
- [ ] 창 크기 1920×1080, 전체화면(F11) 대신 **일반 창** — 주소창이 보여야 라이브 URL 이 증거가 된다
- [ ] 시크릿 창 사용 금지(확장 없음이 좋지만 WebMCP 플래그가 안 먹을 수 있음) → 대신 **새 프로필** 사용
- [ ] 확장 프로그램 전부 비활성화 (툴바 아이콘이 보이면 안 됨)
- [ ] 북마크바 숨김 (`Ctrl+Shift+B`)
- [ ] 캐시 비운 뒤 **하드 리로드** (`Ctrl+Shift+R`) 1회 — 단, 녹화 직전에 한 번 미리 로드해
      네트워크 지연이 화면에 남지 않게 한다
- [ ] DevTools Network 탭 열어두고 **Clear**, 필터 비움 (1:26 구간용)

**OS / 화면**
- [ ] 알림 전부 끄기 (Windows 집중 지원 켜기 / Discord·Slack·메일 종료)
- [ ] 다른 창·트레이 팝업 없음. 바탕화면 아이콘 안 보이게
- [ ] 시계·배터리 등 개인정보성 표시 제외되게 캡처 영역 지정
- [ ] 마우스 커서 강조(하이라이트) 켜기 — 클릭이 안 보이면 Tier B 가 전달되지 않는다
- [ ] 메일 클라이언트를 **빈 새 계정/기본 앱**으로 지정 (2:26 구간에서 개인 메일함 내용이 노출되면 안 됨)

**콘텐츠**
- [ ] 라이브 URL 이 살아있고 `Agent tools: 7 ready` 배지가 실제로 녹색인지
- [ ] 화면 어디에도 개인정보·내부 경로·테스트 계정이 보이지 않는지 최종 육안 확인
- [ ] 페이지 헤더 표기(`TAAMs Import Sourcing Desk`)와 README/SUBMISSION 의 명칭이
      일치하는지 확인 — **불일치 시 녹화 전에 한쪽으로 통일한다.** 영상에는 화면의
      이름이 그대로 찍히므로 나중에 문서만 고쳐도 소용없다

---

## 5. 촬영 실패하기 쉬운 지점과 대비책

| 위험 | 왜 생기나 | 대비책 |
|---|---|---|
| **에이전트가 엉뚱한 도구를 부른다** | 자연어 질문 하나로 7개 도구를 순서대로 유도하는 것은 확률적이다. 한 번에 성공하지 않는다 | 같은 질문으로 **최소 5회 리허설**해서 잘 되는 문구를 고정한다. 그래도 실패하면 질문을 두 개로 쪼갠다(① "Compare Thai and Brazilian mango" ② "Pin it and show only Thailand"). 나레이션은 그대로 써도 맞는다 |
| **1:26 Network 탭에 요청이 찍힌다** | 이전 구간의 지연 응답이나 favicon·analytics 가 늦게 도착 | 하이라이트 실행 **직전에 Clear** 를 한 번 더 누르고, 클릭 후 2초를 기다린 뒤 탭을 보여준다. 그래도 잡음이 있으면 필터에 `Fetch/XHR` 만 선택 |
| **응답이 느려 구간이 밀린다** | 라이브 API 왕복 | 화면 캡처와 나레이션을 **따로 녹음**해 편집에서 맞춘다. 대기 구간은 편집으로 잘라낸다(속도 조작은 하지 말 것 — 로그 시각이 어긋나 보인다) |
| **승인 모달이 너무 빨리 닫힌다** | 익숙해져서 반사적으로 클릭 | 모달이 뜬 뒤 **속으로 넷을 세고** 클릭. 이 4초가 Tier C 주장의 전부다 |
| **메일 클라이언트가 안 열리거나 개인 메일함이 보인다** | `mailto:` 기본 앱 설정 | 사전에 기본 메일 앱을 확인. 열리는 창에 개인 정보가 있으면 **그 프레임은 잘라내고** 카드 상태 변화만 보여준다 — 나레이션은 수정 불필요 |
| **3:00 초과** | 나레이션을 여유 있게 읽다 보면 반드시 넘는다 | 편집본이 2:58 을 넘으면 아래 §6 순서대로 잘라낸다 |
| **화면 텍스트가 안 읽힌다** | 1080p 로 인코딩하면 표 글자가 뭉갠다 | 국가 칩·모달·`$5.07/kg` pill 은 **반드시 확대 컷**을 넣는다. 전체화면만으로 끝내지 말 것 |
| **말이 빨라져 발음이 뭉갠다** | 시간 압박 | 위 §3 을 3회 소리내어 읽고 타이머로 재본 뒤 녹음. 2:50 안에 못 읽으면 속도가 아니라 문장을 줄인다 |

---

## 6. 3:00 을 넘겼을 때 자를 순서

위에서부터 잘라낸다. **Tier B(1:26–1:52)와 Tier C 승인 모달(1:52–2:26)은 절대
건드리지 않는다** — 이 두 구간이 출품작의 유일한 차별점이다.

1. 0:13–0:26 문제 구간을 13초 → 8초로 (`Government customs portals. Cold calls.
   Guessing whether a quoted price is normal.` 만 남기고 앞뒤 문장 삭제) — **−5초**
2. 0:26–0:48 에서 `Nine supplying countries.` 삭제(화면에 칩으로 이미 보인다) — **−3초**
3. 1:00–1:26 에서 `There is no summary for me to copy back into the tool.` 삭제 — **−4초**
4. 2:26–2:42 를 16초 → 11초로 (손 클릭 3회를 2회로) — **−5초**

네 개를 다 적용하면 2:38 이 된다. 그 이상은 자르지 말 것 — 주장이 아니라 근거가
사라지기 시작한다.
