# PIMMmurderboard · 졸업사진(卒業寫眞)

**AI가 빈 좌석을 배역으로 대신 플레이하는 온라인 머더미스터리 진행 엔진.**
2명이서도 3~4인 시나리오를 — 각자 자기 기기로 접속해 자기 배역·정보만 보고,
남은 배역은 AI가 대본대로(거짓말·의심·투표) 채운다. 현재 수록 시나리오: 《졸업사진》.

- 각 참가자가 **배역**을 맡고, 각자 비밀·목표를 가진다.
- 각자 **자기 PC/폰으로 접속**, 비밀은 각자 기기에만.
- 사람이 안 맡은 배역은 **AI 플레이어**(Claude API / 로컬 Ollama)가 채운다.

## 게임 진행 방식 (GM 모드)

**진행자(GM) 1명 + 플레이어 + 빈자리는 AI**로 굴러간다. 인터넷 없이 **로컬 PC + 같은 와이파이(LAN)** 만으로도 된다.

- **진행자(GM)** — 로비에서 `🎬 GM으로 진행`. 페이즈를 넘기고(`다음 페이즈 ›`), **누가 어떤 카드를 조사했는지 마킹**만 한다.
  진행자는 **카드 내용을 볼 수 없어**(마킹 전용) 공용 화면에 스포일러가 없다.
- **플레이어** — 각자 자기 기기에서 배역을 고르고, **조사 턴에 정해진 장수(R1:3, R2:3, R3:2)만큼** 카드를 열어 자기 손패로 본다. 알아낸 것은 대화로만 공유.
- **AI 배역** — 사람이 안 맡은 자리는 AI(또는 옆에 띄운 Claude 세션)가 연기한다. AI가 연 카드는 진행자가 대신 마킹.
- 모두 조사를 마치면 토론 → 진행자가 `다음 페이즈`로 넘긴다. 종막 질문지는 서술형, 채점은 AI/진행자가.

> 조사카드 발견·페이즈 전환에는 연출 애니메이션이 들어간다. 후반부로 갈수록 ‘범인 찾기 → 진상(진혼) 깨닫기’로 무게가 옮겨간다.

## 한 번 배포하면 모두 URL만 (무설정)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pimmprofile-byte/PIMMmurderboard)

1. 위 버튼 → GitHub 연결 → 이 repo 선택 (`render.yaml` 자동 인식)
2. **`ANTHROPIC_API_KEY`** 에 본인 키 입력(비공개) → Create
3. 몇 분 뒤 `https://<이름>.onrender.com` 발급 → **참가자 전원 이 URL만 열면 끝** (설치 0)
   - 각자 **배역 선택/랜덤** → 자기 큐카드·공개정보, 조사·투표 실시간 동기화

> 무료 티어는 유휴 시 슬립 → 첫 접속이 느릴 수 있음. 키는 서버 env에만(코드/URL에 노출 금지).
> 로컬 실행을 원하면 아래 '빠른 시작' 참고.

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
