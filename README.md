# PIMMmurderboard · 그해 여름, 동창회

**AI가 빈 좌석을 배역으로 대신 플레이하는 온라인 머더미스터리 진행 엔진.**
정통 3~4인 머더미스터리 골조를 그대로 쓰되, 인원이 모자라면 남은 배역을 AI가 맡아
대본대로 함께 논다(거짓말·의심·투표까지). **2명이서도 3~4인 시나리오를 즐길 수 있다.**

- 각 참가자가 **배역**을 맡는다. 각자 비밀·목표가 있고, **누구나 범인일 수 있다.**
- 각자 **자기 PC/폰으로 접속**해 함께 플레이(같은 와이파이). 비밀은 각자 기기에만 보인다.
- 사람이 맡지 않은 배역은 **AI 플레이어**가 채운다.

---

## 빠른 시작

### 1) 준비물
- Python 3.10+
- Claude API 키 (기본 백엔드) — 또는 무료 로컬 모델 [Ollama](https://ollama.com)

### 2) 실행
```bash
# mac / linux
./run.sh          # 최초 실행 시 .env 를 만들어 줌 → 키 입력 후 다시 실행

# windows
run.bat
```
수동으로 하려면:
```bash
pip install -r requirements.txt
cp .env.example .env      # ANTHROPIC_API_KEY 입력
python server.py
```

### 3) 접속
서버가 켜지면 접속 주소가 출력됩니다.
```
이 컴퓨터    →  http://127.0.0.1:8790
같은 와이파이 →  http://192.168.x.x:8790   ← 폰·다른 PC는 이 주소로
```
- 각자 접속 → **배역 선택** → 빈 자리는 **‘AI로 채우기’**
- 배역을 고르면 **‘내 시트’**로 자기 비밀·목표 확인 (그 기기에만 보임)
- 테이블에서 대화(오픈채팅) → **‘AI 배역 부르기’**로 AI가 끼어듦
- 충분히 이야기했으면 **‘범인 지목’** → 사람은 각자 투표, AI는 ‘표 받기’ → **결과 공개**

> 방화벽이 접속을 막으면 8790 포트 인바운드를 허용하세요.
> LAN 밖(원격)에서 붙이려면 `cloudflared tunnel --url http://localhost:8790` 같은 터널을 쓰세요.

---

## AI 백엔드

`.env` 의 `LLM_BACKEND` 로 고릅니다.

| 값 | 설명 | 한국어·연기 | 비용 |
|---|---|---|---|
| `claude` (기본) | 로컬 서버가 Claude API 호출 (키는 서버측 보관) | 최상 | 종량(2인 한 판 수백 원 수준) |
| `ollama` | 완전 로컬 모델, 오프라인 | 보통 (qwen2.5 권장) | 무료 |

> **참고:** Claude Max/Pro 구독과 Anthropic API는 별개 과금입니다. 이 서버의 `ANTHROPIC_API_KEY`
> 사용은 구독과 무관하게 종량 청구됩니다. 진짜 ₩0 을 원하면 `LLM_BACKEND=ollama`.

빠르고 저렴하게: `.env` 의 `REUNION_MODEL=claude-sonnet-5`.

---

## 새 시나리오 만들기

`scenario.py` **한 파일**이 시나리오 전부입니다. 통째로 바꾸면 다른 사건이 됩니다.

- `TITLE / INTRO / VICTIM / PHASES` — 사건 개요·라운드
- `CHARACTERS[]` — 배역들. 각 배역:
  - 공개: `name, age, job, avatar, color, tagline`
  - 비밀(서버 전용): `persona`(말투), `sheet`(대본), `goals`(승리조건), `is_culprit`, `ai_note`(AI 연기 지침)
- `CULPRIT_ID` / `SOLUTION` — 범인과 진상(결과 공개용)

비밀·정답은 브라우저로 내려가지 않습니다(서버에서만 읽음). 자기 배역 시트는
그 배역을 맡은 기기에서만 열람됩니다.

---

## 구조

```
브라우저(각 기기)  ──HTTP/폴링──▶  server.py (로컬, 방 상태 보유)  ──▶  Claude API / Ollama
   index.html                       scenario.py (비밀·정답)              (AI 배역 연기·투표)
```

- `server.py` — 방(room) 상태 + 배역 클레임 + 테이블 동기화 + AI 발화/투표 릴레이
- `index.html` — 타이틀 / 로비(배역 선택) / 오픈채팅 테이블 / 투표·결과
- `scenario.py` — 시나리오 데이터 & AI 프롬프트 빌더
