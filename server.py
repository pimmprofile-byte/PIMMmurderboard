"""
PIMMmurderboard · 졸업사진(卒業寫眞) — 로컬 멀티플레이 게임 서버

각자 자기 PC/폰으로 접속(같은 와이파이). 서버가 '방(room)' 상태를 쥐고 각 기기가 폴링 동기화.
배역의 비밀은 그 배역을 맡은 기기에만. 사람이 안 맡은 배역은 AI가 대본대로 플레이(조사·거짓말·자백).
승리 구조: 오승택을 죽인 범인은 없다 — 종막 질문지(서술형)를 AI가 채점, 모두 자기지목 시 진혼 엔딩.

백엔드 교체형: 기본 Claude API(.env ANTHROPIC_API_KEY) / 무료 Ollama(LLM_BACKEND=ollama, qwen2.5).
실행: pip install -r requirements.txt → cp .env.example .env → python server.py
"""
from __future__ import annotations

import json
import os
import random
import re
import socket
import threading
import time
import urllib.request
import zlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

_HERE = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(_HERE / ".env")
except Exception:
    pass

import handoff  # noqa: E402
import scenarios  # noqa: E402

# 활성 시나리오(앱 전역) — 모든 함수는 전역 SC를 읽으므로, SC를 재바인딩하면 앱 전체가 그 시나리오로 전환된다.
SC = scenarios.get(os.getenv("SCENARIO") or scenarios.default_id())

BACKEND = os.getenv("LLM_BACKEND", "claude").lower()
CLAUDE_MODEL = os.getenv("REUNION_MODEL") or os.getenv("PIMM_MODEL") or "claude-opus-4-8"
# 배역 대사는 한두 문장짜리 응수라 빠른 게 곧 재미다 — 여기만 작은 모델로 돌린다.
# 채점은 판마다 한 번뿐이고 정확해야 하므로 CLAUDE_MODEL을 그대로 쓴다.
CLAUDE_MODEL_FAST = os.getenv("PIMM_MODEL_FAST") or "claude-haiku-4-5-20251001"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")
HOST = os.getenv("REUNION_HOST", "0.0.0.0")
# 호스팅(Render 등)은 PORT를 주입 → 그걸 우선 사용, 로컬은 REUNION_PORT/기본값
PORT = int(os.getenv("PORT") or os.getenv("REUNION_PORT", "8790"))
AGENT_KEY = os.getenv("AGENT_KEY", "")  # 에이전트(코드 세션) 원격 조종 키(설정 시 그 키 필요, 미설정 시 개방)
# 심층심문 — 어떤 카드를 증거로 대는지가 추리다. 증거 없이 60%, 엉뚱한 카드면 오히려 20%로
# 떨어지고(허를 찔러 얼버무릴 여지를 준다), 정확한 카드(시나리오의 rebuttal)면 100% 실토.
INTERROGATE_TRUTH_BASE = 0.60
INTERROGATE_TRUTH_WRONG_EVIDENCE = 0.20

try:
    import anthropic
except Exception:
    anthropic = None
_ac = None


def _claude(system: str, user: str, mt: int, model: str = "") -> str:
    global _ac
    if anthropic is None:
        raise RuntimeError("anthropic SDK 미설치 — pip install anthropic")
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY 미설정 (.env) — 또는 LLM_BACKEND=ollama")
    if _ac is None:
        _ac = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    last = None
    for i in range(3):
        try:
            m = _ac.messages.create(model=model or CLAUDE_MODEL, max_tokens=mt, system=system,
                                    messages=[{"role": "user", "content": user}])
            for b in m.content:
                if getattr(b, "type", None) == "text":
                    return b.text.strip()
            return ""
        except Exception as e:  # noqa: BLE001
            last = e
            if i < 2:
                time.sleep((2 ** i) + random.uniform(0, 0.4))
    raise RuntimeError(f"Claude 호출 실패: {last}")


def _ollama(system: str, user: str, mt: int, model: str = "") -> str:
    payload = {"model": OLLAMA_MODEL, "stream": False, "options": {"temperature": 0.85, "num_predict": mt},
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    last = None
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return (json.loads(r.read().decode("utf-8")).get("message", {}).get("content", "") or "").strip()
        except Exception as e:  # noqa: BLE001
            last = e
            if i < 2:
                time.sleep((2 ** i) + random.uniform(0, 0.4))
    raise RuntimeError(f"Ollama 호출 실패({OLLAMA_URL}, {OLLAMA_MODEL}): {last}")


def llm(system: str, user: str, mt: int = 400, fast: bool = False) -> str:
    """fast=True면 배역 대사용 작은 모델로. Ollama 백엔드는 모델이 하나뿐이라 무시된다."""
    model = CLAUDE_MODEL_FAST if fast else CLAUDE_MODEL
    return _ollama(system, user, mt, model) if BACKEND == "ollama" else _claude(system, user, mt, model)


def backend_ready() -> tuple[bool, str]:
    if BACKEND == "ollama":
        return True, f"Ollama · {OLLAMA_MODEL}"
    if not ANTHROPIC_API_KEY:
        return False, "Claude · API 키 미설정 (.env)"
    if anthropic is None:
        return False, "Claude · anthropic SDK 미설치"
    return True, f"Claude · {CLAUDE_MODEL} (대사 {CLAUDE_MODEL_FAST})"


def _parse_json(raw: str) -> dict:
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        return json.loads(m.group(0)) if m else {}
    except Exception:
        return {}


def current_round(seq: int) -> int:
    if seq >= 6:
        return 3
    if seq >= 4:
        return 2
    if seq >= 2:
        return 1
    return 0


# ── 방 상태 ──
LOCK = threading.RLock()


def fresh_room() -> dict:
    return {
        "rev": 1, "seq": 1,
        "scenarioId": SC.ID,
        # 판마다 새로 생기는 값. 클라이언트가 "이 판에서 오프닝을 봤나"를 이걸로 가른다 —
        # 시나리오 이름으로 기억하면 한 번 본 브라우저에서 영영 안 나온다.
        "roomId": f"r{random.randrange(16**8):08x}",
        "host": None,             # 방 권한자(호스트) clientId — 시나리오 선택·페이즈 진행 통제
        "roles": {c["id"]: {"mode": "open", "clientId": None} for c in SC.CHARACTERS},
        "table": [{"kind": "system", "text": f'— {SC.PHASES[0]["name"]} —'}],
        "revealed": [],           # 전체공개 card id
        "hands": {},              # roleId -> [cardId] (손패, 비공개 · 조사/마킹 통합)
        "checkedRound": {},       # roleId -> {cardId: round} (턴별 조사 수 제한 계산용)
        "grades": {},             # roleId -> grade dict (name 포함)
        "finalAnswers": {},       # roleId -> [answer str] (백엔드 미설정 시 진행자 수동채점용 보관)
        "typing": None,
        "events": [],            # 진행 세션이 따라 읽는 사건 기록
        "podOpen": False,        # 특정 카드가 전체공개되면 지도에 탈출 포드가 드러난다
        "turn": None,             # 조사 페이즈 현재 차례 roleId (하이브리드 턴)
        "interrogate": {"seq": None, "used": 0, "votes": [], "bonus": False},  # 토론 페이즈 심층심문 예산
        "started": False,         # 호스트가 '이대로 진행'을 확정하면 True — 이후 배역 변경 불가
    }


ROOM = fresh_room()


def use_scenario(sid: str) -> bool:
    """시나리오를 교체하고 방을 새 시나리오로 초기화한다(모두에게 반영)."""
    global SC, ROOM
    if sid not in scenarios.ids():
        return False
    with LOCK:
        prev_host = ROOM.get("host")
        SC = scenarios.get(sid)
        ROOM = fresh_room()
        ROOM["host"] = prev_host   # 호스트는 시나리오 전환 후에도 유지
    return True


def bump():
    ROOM["rev"] += 1


def _ev(kind: str, **fields) -> None:
    """진행 세션이 따라 읽는 사건 기록.

    세션은 푸시를 못 받는다 — 자기 차례가 와야 움직인다. 그래서 서버가 일어난 일을
    번호 붙여 쌓아두고, 세션이 커서 이후만 받아 간다. state를 통째로 비교하는 것보다
    싸고, 무엇이 새로 생겼는지가 분명하다.
    """
    evs = ROOM.setdefault("events", [])
    evs.append({"id": len(evs) + 1, "seq": ROOM["seq"], "kind": kind, **fields})
    del evs[:-400]


def _auto_reveal_obligatory():
    return  # '전체공개' 개념 미사용(우선) — 공개의무 카드도 GM이 대화로 내레이션한다


def public_state() -> dict:
    with LOCK:
        seq = ROOM["seq"]
        ph = SC.phase_by_seq(seq)
        g = ROOM["grades"]
        ending = SC.compute_ending(g)  # 준비 안 됐으면 시나리오가 None을 반환
        # 진상(정답·범인)은 '진상 공개' 페이즈 전까지 클라이언트로 내보내지 않는다(스포일러 방지).
        if ph.get("key") != "reveal":
            ending = None
        cur = current_round(seq)
        ap = int(ph.get("ap", 0) or 0)
        # 내용 없는 마킹 현황(누가 어떤 카드를 조사했는지 id만) + 이번 턴 남은 조사 수
        checked = {rid: list(cs) for rid, cs in ROOM["hands"].items() if cs}
        used = {rid: sum(1 for r in cm.values() if r == cur) for rid, cm in ROOM["checkedRound"].items()}
        return {
            "rev": ROOM["rev"], "seq": seq, "round": cur, "scenarioId": SC.ID,
            "roomId": ROOM.get("roomId", ""),
            "podOpen": bool(ROOM.get("podOpen")),
            "chat": {"on": CHAT["on"], "gap": CHAT["gap"]},
            "phase": {"seq": ph["seq"], "key": ph["key"], "name": ph["name"], "gm": ph["gm"], "ap": ap, "min": ph["min"]},
            "roles": {rid: {"mode": r["mode"], "claimed": r["clientId"] is not None} for rid, r in ROOM["roles"].items()},
            "table": ROOM["table"],
            "revealed": [SC.public_card(cid) for cid in ROOM["revealed"]],
            "revealedIds": list(ROOM["revealed"]),
            "checked": checked,
            "usedAP": used,
            "handLimit": _hand_limit(),
            "keepGoals": _keep_goal_results() if ph.get("key") in ("final", "reveal") else [],
            "overLimit": {rid: max(0, len(cs) - _hand_limit()) for rid, cs in ROOM["hands"].items() if len(cs) > _hand_limit()},
            "turn": ROOM.get("turn") if ap > 0 else None,
            "turnOrder": _turn_order() if ap > 0 else [],
            "interrogate": _interrogate_budget() if ph.get("key") == "talk" else None,
            "started": bool(ROOM.get("started")),
            "typing": ROOM["typing"],
            "grades": g,
            "ending": ending,
        }


app = FastAPI(title="PIMMmurderboard")

# GM 콘솔(다른 출처의 board.html)이 라이브 서버를 호출할 수 있게 CORS 개방
try:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
except Exception:
    pass

# 이미지 에셋(인물 사진 등)을 /assets 로 서빙 — 파일을 넣는 즉시 UI가 집어간다.
# 규약: assets/{scenarioId}_portrait_{roleId}.png  (없으면 클라이언트가 이모지로 폴백)
try:
    from fastapi.staticfiles import StaticFiles
    _ASSETS = _HERE / "assets"
    _ASSETS.mkdir(exist_ok=True)
    app.mount("/assets", StaticFiles(directory=str(_ASSETS)), name="assets")
except Exception:
    pass


class Claim(BaseModel):
    roleId: str
    clientId: str


class SetAI(BaseModel):
    roleId: str


class HumanSay(BaseModel):
    roleId: str
    clientId: str
    text: str


class RoleOnly(BaseModel):
    roleId: str


class ChatCtl(BaseModel):
    key: str = ""
    clientId: str = ""
    on: bool | None = None
    gap: float | None = None


class CardOnly(BaseModel):
    cardId: str


class ClientOnly(BaseModel):
    clientId: str


class Investigate(BaseModel):
    cardId: str
    roleId: str
    clientId: str


class Interrogate(BaseModel):
    askerRoleId: str
    targetRoleId: str
    cardId: str
    evidenceCardId: str = ""
    clientId: str


class InterrogateVote(BaseModel):
    roleId: str
    clientId: str


class AgentSay(BaseModel):
    roleId: str
    text: str
    key: str = ""


class AgentCard(BaseModel):
    cardId: str
    roleId: str = ""
    key: str = ""


class KeyOnly(BaseModel):
    key: str = ""


class SelectScenario(BaseModel):
    scenarioId: str
    key: str = ""
    clientId: str = ""


class HostReq(BaseModel):
    clientId: str = ""


class TurnReq(BaseModel):
    clientId: str = ""
    roleId: str = ""
    key: str = ""


class FinalAnswers(BaseModel):
    roleId: str
    clientId: str
    answers: list[str]


@app.get("/api/scenario")
def scenario():
    ok, label = backend_ready()
    d = SC.public_scenario()
    d["backend"] = {"ok": ok, "label": label}
    # 조사카드 카탈로그(제목·본문 제외 — 미공개 슬롯 구조만)
    d["cardCatalog"] = [{"id": c["id"], "loc": c["loc"], "locName": c["locName"], "round": c["round"],
                         "spot": c.get("spot", ""),
                         "requires": c.get("requires"), "obligatory": c.get("reveal") == "obligatory"}
                        for c in SC.CARDS]
    return d


@app.get("/api/scenarios")
def scenarios_list():
    return {"scenarios": scenarios.meta_list(), "active": SC.ID}


@app.post("/api/select")
def select_scenario(b: SelectScenario):
    # 호스트(또는 AGENT_KEY 보유 GM 콘솔)만 시나리오 전환 가능
    if not (_is_host(b.clientId) or _agent_ok(b.key)):
        return JSONResponse({"error": "host"}, status_code=403)
    if b.scenarioId not in scenarios.ids():
        return JSONResponse({"error": "없는 시나리오"}, status_code=400)
    use_scenario(b.scenarioId)  # 방을 새 시나리오로 초기화(호스트는 유지)
    return {"ok": True, "active": SC.ID}


@app.get("/api/state")
def state(clientId: str = ""):
    st = public_state()
    with LOCK:
        st["hasHost"] = ROOM.get("host") is not None
        # 내가 맡은 배역. 예전엔 클라이언트가 localStorage 기억만 보고 판단해서,
        # 잡은 직후나 새로고침 뒤에 자기 배역을 '참여 중'(남이 맡음)으로 그리곤 했다.
        st["myRole"] = next((rid for rid, r in ROOM["roles"].items()
                             if clientId and r["clientId"] == clientId), None)
        st["isHost"] = bool(clientId) and ROOM.get("host") == clientId
        # 호스트를 아무도 안 잡은 방도 있다. 그때는 '호스트 전용' 연출을 아무도 못 보게 되므로
        # 클라이언트가 그 사정을 알 수 있게 해준다(다른 엔드포인트도 같은 규칙으로 통과시킨다).
        st["hasHost"] = ROOM.get("host") is not None
        # 내가 맡은 배역. 예전엔 클라이언트가 localStorage 기억만 보고 판단해서,
        # 잡은 직후나 새로고침 뒤에 자기 배역을 '참여 중'(남이 맡음)으로 그리곤 했다.
        st["myRole"] = next((rid for rid, r in ROOM["roles"].items()
                             if clientId and r["clientId"] == clientId), None)
    return st


@app.post("/api/start")
def start_game(b: HostReq):
    """호스트가 배역 확정 — 이후 배역은 바꿀 수 없고, 모두가 오프닝으로 들어간다."""
    with LOCK:
        if ROOM.get("host") is not None and not _is_host(b.clientId):
            return JSONResponse({"error": "호스트만 시작할 수 있습니다"}, status_code=403)
        opens = [rid for rid, r in ROOM["roles"].items() if r["mode"] == "open"]
        if opens:
            return JSONResponse({"error": f"아직 정해지지 않은 배역이 {len(opens)}개 있습니다"}, status_code=409)
        ROOM["started"] = True
        ROOM["table"].append({"kind": "system", "broadcast": True, "text": "🎬 배역이 확정됐습니다. 오프닝을 시작합니다."})
        bump()
    return {"ok": True, "started": True}


def _roles_locked() -> bool:
    return bool(ROOM.get("started"))


@app.post("/api/host/claim")
def host_claim(b: HostReq):
    with LOCK:
        if not b.clientId:
            return JSONResponse({"error": "clientId"}, status_code=400)
        if ROOM.get("host") in (None, b.clientId):
            ROOM["host"] = b.clientId
            bump()
            return {"ok": True, "isHost": True}
        return {"ok": False, "isHost": False, "hasHost": True}


@app.post("/api/host/release")
def host_release(b: HostReq):
    with LOCK:
        if ROOM.get("host") == b.clientId:
            ROOM["host"] = None
            bump()
        return {"ok": True}


@app.post("/api/claim")
def claim(b: Claim):
    with LOCK:
        if _roles_locked():
            return JSONResponse({"error": "게임이 시작돼 배역을 바꿀 수 없습니다"}, status_code=409)
        r = ROOM["roles"].get(b.roleId)
        if not r:
            return JSONResponse({"error": "없는 배역"}, status_code=404)
        if r["clientId"] and r["clientId"] != b.clientId:
            return JSONResponse({"error": "이미 다른 사람이 맡은 배역입니다"}, status_code=409)
        for rr in ROOM["roles"].values():
            if rr["clientId"] == b.clientId:
                rr["clientId"] = None
                rr["mode"] = "open"
        r["clientId"] = b.clientId
        r["mode"] = "human"
        bump()
    return {"ok": True}


@app.post("/api/claim-random")
def claim_random(b: ClientOnly):
    with LOCK:
        if _roles_locked():
            return JSONResponse({"error": "게임이 시작돼 배역을 바꿀 수 없습니다"}, status_code=409)
        for rid, r in ROOM["roles"].items():
            if r["clientId"] == b.clientId:
                return {"ok": True, "roleId": rid}
        opens = [rid for rid, r in ROOM["roles"].items() if r["mode"] == "open"]
        if not opens:
            return JSONResponse({"error": "빈 배역이 없습니다"}, status_code=409)
        rid = random.choice(opens)
        ROOM["roles"][rid]["clientId"] = b.clientId
        ROOM["roles"][rid]["mode"] = "human"
        bump()
    return {"ok": True, "roleId": rid}


@app.post("/api/release")
def release(b: Claim):
    with LOCK:
        if _roles_locked():
            return JSONResponse({"error": "게임이 시작돼 배역을 바꿀 수 없습니다"}, status_code=409)
        r = ROOM["roles"].get(b.roleId)
        if r and r["clientId"] == b.clientId:
            r["clientId"] = None
            r["mode"] = "open"
            bump()
    return {"ok": True}


@app.post("/api/setai")
def setai(b: SetAI):
    with LOCK:
        if _roles_locked():
            return JSONResponse({"error": "게임이 시작돼 배역을 바꿀 수 없습니다"}, status_code=409)
        r = ROOM["roles"].get(b.roleId)
        if not r:
            return JSONResponse({"error": "없는 배역"}, status_code=404)
        if r["mode"] == "human":
            return JSONResponse({"error": "사람이 맡은 배역"}, status_code=409)
        r["mode"] = "ai" if r["mode"] != "ai" else "open"
        r["clientId"] = None
        bump()
    return {"ok": True}


@app.get("/api/sheet/{role_id}")
def sheet(role_id: str, clientId: str = ""):
    with LOCK:
        r = ROOM["roles"].get(role_id)
        seq = ROOM["seq"]
        if not r:
            return JSONResponse({"error": "없는 배역"}, status_code=404)
        if r["clientId"] != clientId:  # 엄격: 내가 '맡은' 배역만 (빈자리·AI 배역 비밀 열람 차단)
            return JSONResponse({"error": "자기 배역만 열람할 수 있습니다"}, status_code=403)
    s = SC.private_sheet(role_id)
    s["fragments"] = SC.memory_up_to(role_id, seq)
    return s


@app.post("/api/reveal-card")
def reveal_card(b: CardOnly):
    with LOCK:
        c = SC.get_card(b.cardId)
        if not c:
            return JSONResponse({"error": "없는 카드"}, status_code=404)
        cr = current_round(ROOM["seq"])
        if c["round"] > cr:
            return JSONResponse({"error": f"아직 조사할 수 없습니다 (조사 R{c['round']}에 열림)"}, status_code=409)
        req = c.get("requires")
        if req and req not in ROOM["revealed"]:
            rq = SC.get_card(req)
            return JSONResponse({"error": f"먼저 '{rq['title'] if rq else req}'가 필요합니다"}, status_code=409)
        if b.cardId not in ROOM["revealed"]:
            ROOM["revealed"].append(b.cardId)
            bump()
    return {"card": SC.public_card(b.cardId)}


def _agent_ok(key: str) -> bool:
    return (not AGENT_KEY) or key == AGENT_KEY


def _is_host(client_id: str) -> bool:
    return bool(client_id) and ROOM.get("host") == client_id


def _ap_for(seq: int) -> int:
    return int(SC.phase_by_seq(seq).get("ap", 0) or 0)


def _round_checks(role_id: str, rnd: int) -> int:
    """이번 조사 라운드에 이 배역이 조사한 카드 수."""
    return sum(1 for r in ROOM["checkedRound"].get(role_id, {}).values() if r == rnd)


def _keep_goal_results() -> list:
    """'카드를 끝까지 쥐기' 목표를 쓰는 시나리오에서, 종막 시점 달성 여부를 계산한다."""
    fn = getattr(SC, "keep_goal_result", None)
    if not fn:
        return []
    out = []
    for c in SC.CHARACTERS:
        r = fn(c["id"], ROOM["hands"].get(c["id"], []), ROOM["revealed"])
        if r:
            r["name"] = c["name"]
            r["color"] = c.get("color")
            out.append(r)
    return out


def _hand_limit() -> int:
    """손패 상한 — 넘치면 넘치는 만큼 골라서 전체공개로 내려놓아야 한다."""
    return int(getattr(SC, "HAND_LIMIT", 3))


def _over_limit(role_id: str) -> int:
    return max(0, len(ROOM["hands"].get(role_id, [])) - _hand_limit())


def _human_roles() -> list:
    return [rid for rid, r in ROOM["roles"].items() if r["mode"] == "human" and r["clientId"]]


def _ensure_interrogate_seq() -> None:
    """토론 페이즈에 새로 들어오면 심문 예산·투표를 초기화한다(페이즈당 예산)."""
    seq = ROOM["seq"]
    ph = SC.phase_by_seq(seq)
    ig = ROOM["interrogate"]
    if ph.get("key") == "talk" and ig.get("seq") != seq:
        ROOM["interrogate"] = {"seq": seq, "used": 0, "votes": [], "bonus": False}


def _interrogate_budget() -> dict:
    """1인당 2회 + 과반수(2인이면 만장일치) 투표로 +1. 토론 페이즈마다 리셋."""
    _ensure_interrogate_seq()
    ig = ROOM["interrogate"]
    n = len(_human_roles())
    base = 2 * n
    bonus = 1 if ig["bonus"] else 0
    total = base + bonus
    need = (n // 2 + 1) if n else 0
    return {"base": base, "bonus": bonus, "total": total, "used": ig["used"],
            "remaining": max(0, total - ig["used"]), "voteNeed": need,
            "voteHave": len(ig["votes"]), "bonusGranted": ig["bonus"]}


def _holder_of(card_id: str) -> str | None:
    """그 카드를 이미 조사한 배역(없으면 None). 조사카드는 한 사람만 가진다."""
    for rid, cids in ROOM["hands"].items():
        if card_id in cids:
            return rid
    return None


# ── 하이브리드 턴 (순번 강제 + 호스트/GM 넘기기·스킵) ─────────────────────────
def _turn_order() -> list:
    """턴 순번 = 시나리오가 정의한 TURN_ORDER, 없으면 배역 등장 순.

    라운드마다 선두를 한 칸씩 돌린다 — 고정 순번이면 첫 배역이 매 라운드 먼저
    고르게 되어, 경쟁 카드(예: 보유 목표 카드)를 늘 같은 사람이 가져간다.
    """
    order = [rid for rid in (list(getattr(SC, "TURN_ORDER", None) or [c["id"] for c in SC.CHARACTERS]))
             if rid in ROOM["roles"]]
    if not order:
        return order
    shift = max(0, current_round(ROOM["seq"]) - 1) % len(order)
    return order[shift:] + order[:shift]


def _reset_turn_for_seq(seq: int) -> None:
    """조사 페이즈에 들어오면 순번 첫 배역으로, 아니면 턴 없음."""
    ph = SC.phase_by_seq(seq)
    prev, ROOM["seq"] = ROOM["seq"], seq          # 순번 회전은 새 seq 기준으로 계산한다
    order = _turn_order()
    ROOM["seq"] = prev
    ROOM["turn"] = order[0] if (int(ph.get("ap", 0) or 0) > 0 and order) else None


def _advance_turn() -> None:
    """다음 순번으로. 이번 라운드 AP를 다 쓴 배역은 건너뛴다(한 바퀴 안에서)."""
    order = _turn_order()
    if not order:
        ROOM["turn"] = None
        return
    ap = _ap_for(ROOM["seq"])
    cur = current_round(ROOM["seq"])
    start = order.index(ROOM["turn"]) if ROOM.get("turn") in order else -1
    for step in range(1, len(order) + 1):
        cand = order[(start + step) % len(order)]
        if ap <= 0 or _round_checks(cand, cur) < ap:   # 아직 조사 여력이 있는 배역
            ROOM["turn"] = cand
            bump()
            return
    ROOM["turn"] = order[(start + 1) % len(order)]      # 전원 소진 → 그냥 다음 배역
    bump()


# ── AI 자동 조사 (API 없이 휴리스틱 · 인물답게 + 추리 따라가기) ────────────────
def _openable_cards(role_id: str) -> list:
    cur = current_round(ROOM["seq"])
    mine = ROOM["hands"].get(role_id, [])
    seen = set(ROOM["revealed"])
    for cids in ROOM["hands"].values():
        seen.update(cids)
    out = []
    for c in SC.CARDS:
        if c["id"] in mine or c["id"] in ROOM["revealed"] or c["round"] > cur:
            continue
        if _holder_of(c["id"]):          # 남이 이미 가져간 카드는 후보에서 제외
            continue
        req = c.get("requires")
        if req and req not in seen:
            continue
        out.append(c)
    return out


def _recent_text(n: int = 8) -> str:
    """최근 '사람과 인물이 한 말'만 모은다. GM 안내와 페이즈 지문은 뺀다 —
    그 지문에는 이번 라운드에 볼 것들이 미리 적혀 있어서, 걸러내지 않으면
    아무도 입에 올린 적 없는 물건이 화제인 것처럼 잡힌다."""
    said = [m for m in ROOM["table"] if m.get("kind") in ("human", "ai")]
    return " ".join((m.get("text") or "") for m in said[-n:])


def _title_tokens(card: dict) -> list[str]:
    """카드 제목·위치에서 대화에 나올 만한 낱말을 뽑는다.

    형태소 분석기 없이 부분문자열로 맞춘다 — 한국어는 조사가 붙어 늘어나므로
    '단말기'는 '단말기가/단말기를'에도 걸린다. 짧은 토막은 오탐이 나서 버린다.
    """
    out = []
    for part in (card.get("title", "") + " " + card.get("spot", "")).replace("·", " ").split():
        w = part.strip("()[],.의를을이가는은도만")
        if len(w) >= 2 and not w.isdigit():
            out.append(w)
    return out


def _topic_boost(role_id: str) -> dict:
    """지금 대화가 향하는 곳을 카드 단위로 환산한다.

    구역만 보던 신호(_hot_locs)로는 '단말기 얘기 중'이나 '지금 유태오가 몰리는 중'
    같은 흐름을 못 읽는다. 그래서 카드 제목의 낱말과 사람 이름까지 본다.
    LLM 없이 도는 부분이라 대화가 붙는 만큼만 정확하다 — 그 정도면 충분하다.
    """
    txt = _recent_text(8)
    if not txt:
        return {}
    boost = {}
    for c in SC.CARDS:
        hit = sum(1 for w in _title_tokens(c) if w in txt)
        if hit:
            boost[c["id"]] = boost.get(c["id"], 0) + 2.2 * hit
    # 지금 몰리고 있는 사람은 자기 구역을 뒤져 방어할 거리를 찾는다
    me = SC.get_character(role_id)
    if me and txt.count(me["name"]) >= 2:
        home = set(((getattr(SC, "INVEST_AI", {}) or {}).get(role_id, {})).get("home", []))
        for c in SC.CARDS:
            if c["loc"] in home:
                boost[c["id"]] = boost.get(c["id"], 0) + 1.8
    return boost


def _hot_locs() -> dict:
    """최근 대화·공개에서 언급된 구역 = 추리가 향하는 곳."""
    locs = {}
    for m in ROOM["table"][-8:]:
        txt = m.get("text", "") or ""
        # 한 발언에서 같은 구역은 한 번만 센다 — 구역별로 카드 수만큼 가산되면
        # 카드가 많은 구역이 과열돼 전원이 그리로 몰린다.
        for loc in {c["loc"] for c in SC.CARDS if c["locName"] and c["locName"] in txt}:
            locs[loc] = locs.get(loc, 0) + 1
    for cid in ROOM["revealed"][-4:]:
        c = SC.get_card(cid)
        if c:
            locs[c["loc"]] = locs.get(c["loc"], 0) + 1
    return locs


def _ai_pick(role_id: str, n: int) -> list:
    """AI 배역이 성향+합리성에 따라 카드 n장을 자동으로 조사한다(즉시, API 0)."""
    prof = (getattr(SC, "INVEST_AI", {}) or {}).get(role_id, {})
    home = set(prof.get("home", []))
    interest = prof.get("interest", {})   # cardId -> 가중치(음수면 회피)
    role_kind = prof.get("role", "normal")
    hot = _hot_locs()
    topic = _topic_boost(role_id)          # 대화가 지금 가리키는 카드들
    cur = current_round(ROOM["seq"])
    loc_count = {}
    for cid in ROOM["hands"].get(role_id, []):
        c = SC.get_card(cid)
        if c:
            loc_count[c["loc"]] = loc_count.get(c["loc"], 0) + 1
    picks = []
    for _ in range(max(0, n)):
        cands = [c for c in _openable_cards(role_id) if c["id"] not in picks]
        if not cands:
            break

        def score(c):
            s = 1.0
            if c["loc"] in home:
                s += 3.0
            s += interest.get(c["id"], 0)              # 관심(+)·회피(−)
            if c["round"] == cur:
                s += 1.2                                # 이번 라운드 새 카드
            s += 0.5 * hot.get(c["loc"], 0)             # 추리 따라가기(과하면 전원이 한 구역에 몰린다)
            s += topic.get(c["id"], 0)                  # 방금 입에 오른 물건을 직접 보러 간다
            s -= 0.8 * loc_count.get(c["loc"], 0)       # 같은 구역 과다 회피
            if role_kind == "troll" and c.get("bait"):
                s += 2.5                                # 진범: 미끼로 유도
            # 재현가능 tie-break — 파이썬 str hash()는 프로세스마다 값이 달라 재현이 안 된다.
            s += (zlib.crc32(f'{ROOM["seq"]}|{role_id}|{c["id"]}'.encode()) % 97) / 970.0
            return s

        best = max(cands, key=score)
        if _try_investigate(role_id, best["id"], enforce_turn=False):
            break
        picks.append(best["id"])
        loc_count[best["loc"]] = loc_count.get(best["loc"], 0) + 1
    _ai_trim_hand(role_id)
    return picks


def _ai_trim_hand(role_id: str) -> list:
    """손패 상한을 넘으면 AI가 알아서 내려놓는다.
    자기에게 불리한 카드(interest 음수 = 감추고 싶은 것)는 끝까지 쥐고, 무해하거나 공유해도 될 것부터 공개한다."""
    prof = (getattr(SC, "INVEST_AI", {}) or {}).get(role_id, {})
    interest = prof.get("interest", {})
    hide = set(prof.get("hide", []))     # 손에 들어오면 끝까지 감추는 카드
    out = []
    while _over_limit(role_id) > 0:
        hand = list(ROOM["hands"].get(role_id, []))
        if not hand:
            break
        # hide 목록은 마지막까지 쥔다. 그 밖에서는 interest 가 높을수록 먼저 내려놓는다.
        drop = max(hand, key=lambda cid: (-1 if cid in hide else 0,
                                          interest.get(cid, 0.0),
                                          zlib.crc32(f"{role_id}|{cid}".encode()) % 97))
        _publish_from(role_id, drop)
        out.append(drop)
    return out


def _try_investigate(role_id: str, card_id: str, enforce_ap: bool = True, enforce_turn: bool = False) -> str | None:
    c = SC.get_card(card_id)
    if not c:
        return "없는 카드"
    cur = current_round(ROOM["seq"])
    if c["round"] > cur:
        return f"아직 조사할 수 없습니다 (조사 R{c['round']}에 열림)"
    ap = _ap_for(ROOM["seq"])
    already = card_id in ROOM["hands"].get(role_id, [])
    holder = _holder_of(card_id)
    if holder and holder != role_id:
        # 조사카드는 한 사람만 가진다 — 먼저 조사한 사람에게 물어봐야 한다.
        h = SC.get_character(holder) or {}
        return f"이미 {h.get('name', '다른 배역')}가 조사한 카드예요 — 그 사람에게 물어보세요"
    if enforce_ap and not already:
        if ap <= 0:
            return "지금은 조사 턴이 아닙니다 (조사 페이즈에서만 열 수 있어요)"
        if enforce_turn and ROOM.get("turn") and role_id != ROOM["turn"]:
            t = SC.get_character(ROOM["turn"]) or {}
            return f"지금은 {t.get('name', '다른 배역')} 차례예요 — 순서를 기다려 주세요"
        if _round_checks(role_id, cur) >= ap:
            return f"이번 조사 턴({cur}라운드)에 열 수 있는 {ap}장을 모두 사용했습니다"
    # 선행조건은 테이블 전체 기준 — 조사카드는 한 사람만 갖지만, 누군가 찾아낸 사실은
    # 대화로 공유되므로 그 뒤를 다른 사람이 이어 팔 수 있어야 한다.
    req = c.get("requires")
    seen = set(ROOM["revealed"])
    for cids in ROOM["hands"].values():
        seen.update(cids)
    if req and req not in seen:
        rq = SC.get_card(req)
        return f"먼저 '{rq['title'] if rq else req}'가 필요합니다"
    if card_id in ROOM["revealed"]:
        return None
    h = ROOM["hands"].setdefault(role_id, [])
    if card_id not in h:
        h.append(card_id)
        ROOM["checkedRound"].setdefault(role_id, {})[card_id] = cur
        bump()
    return None


def _mark_toggle(role_id: str, card_id: str) -> str | None:
    """GM 마킹 토글: 내용은 반환하지 않는다(진행자는 카드 내용을 볼 수 없음)."""
    if role_id not in ROOM["roles"]:
        return "없는 배역"
    h = ROOM["hands"].setdefault(role_id, [])
    if card_id in h:  # 마킹 해제
        h.remove(card_id)
        ROOM["checkedRound"].get(role_id, {}).pop(card_id, None)
        bump()
        return None
    # GM 마킹은 진행자가 테이블에서 벌어진 일을 그대로 옮겨 적는 것이라 조사 턴 제한을 걸지 않는다.
    # 걸어두면 토론 페이즈(AP 0)에서 잘못 푼 마킹을 되돌릴 수가 없다 — 실제로 그래서 막혔다.
    return _try_investigate(role_id, card_id, enforce_ap=False)


def _subj(name: str) -> str:
    """이름 뒤 조사 — 받침이 있으면 '이', 없으면 '가'."""
    if not name:
        return "가"
    ch = name[-1]
    return "이" if ("가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28) else "가"


def _obj(word: str) -> str:
    """목적격 조사 — 받침이 있으면 '을', 없으면 '를'."""
    if not word:
        return "를"
    ch = word[-1]
    return "을" if ("가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28) else "를"


def _publish_from(role_id: str, card_id: str) -> None:
    """그 배역의 손패에서 카드를 빼 전체공개로 돌리고 테이블에 알린다."""
    c = SC.get_card(card_id)
    who = SC.get_character(role_id) or {}
    _publish(card_id, by=role_id)
    if c:
        nm = who.get("name", role_id)
        where = f'{c["locName"]} · {c["spot"]}' if c.get("spot") else c["locName"]
        ttl = c["title"]
        ROOM["table"].append({"kind": "system", "broadcast": True,
                              "text": f'📌 {nm}{_subj(nm)} [{where}] 「{ttl}」{_obj(ttl)} 전체공개했습니다.'})
        bump()


def _publish(card_id: str, by: str = "") -> None:
    """공개는 여기 한 곳으로 모인다 — 사건 기록도 여기서 낸다.
    호출 경로가 여럿이라(본인 공개·GM 공개·정리) 위쪽에서 내면 빠지는 길이 생긴다."""
    for hl in ROOM["hands"].values():
        if card_id in hl:
            hl.remove(card_id)
    if card_id not in ROOM["revealed"]:
        ROOM["revealed"].append(card_id)
        c = SC.get_card(card_id)
        if c and c.get("unlocks") == "pod" and not ROOM.get("podOpen"):
            ROOM["podOpen"] = True
            ROOM["table"].append({"kind": "system", "broadcast": True,
                                  "text": "🛟 계통도가 가리키던 것이 드러났습니다 — 배치도에 탈출 포드가 표시됩니다."})
            _ev("unlock", what="pod", cardId=card_id)
        if c:
            who = SC.get_character(by) or {}
            _ev("reveal", roleId=by, speaker=who.get("name", ""), cardId=card_id,
                title=c["title"], loc=c["loc"], locName=c["locName"], spot=c.get("spot", ""),
                text=c.get("text", ""), hint=c.get("hint", ""))
        bump()


@app.post("/api/investigate")
def investigate(b: Investigate):
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["clientId"] != b.clientId:
            return JSONResponse({"error": "그 배역으로 조사할 수 없습니다"}, status_code=403)
        err = _try_investigate(b.roleId, b.cardId, enforce_turn=True)
        if err:
            return JSONResponse({"error": err}, status_code=409)
        # 이번 턴 AP를 다 썼으면 자동으로 다음 차례로
        ap = _ap_for(ROOM["seq"])
        if ap > 0 and ROOM.get("turn") == b.roleId and _round_checks(b.roleId, current_round(ROOM["seq"])) >= ap:
            _advance_turn()
    return {"card": SC.public_card(b.cardId)}


@app.post("/api/mark")
def mark(b: AgentCard):
    """진행자(GM) 마킹 — 어떤 배역이 어떤 카드를 조사했는지 토글. 카드 내용은 반환하지 않음."""
    if not _agent_ok(b.key):
        return JSONResponse({"error": "key"}, status_code=403)
    with LOCK:
        if not b.roleId:
            return JSONResponse({"error": "배역 필요"}, status_code=400)
        err = _mark_toggle(b.roleId, b.cardId)
        if err:
            return JSONResponse({"error": err}, status_code=409)
        checked = b.cardId in ROOM["hands"].get(b.roleId, [])
    return {"ok": True, "checked": checked}


@app.post("/api/publish")
def publish_card(b: Investigate):
    """손패에서 카드 한 장을 전체공개로 내려놓는다(손패 상한 정리)."""
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["clientId"] != b.clientId:
            return JSONResponse({"error": "권한 없음"}, status_code=403)
        if b.cardId not in ROOM["hands"].get(b.roleId, []):
            return JSONResponse({"error": "내 손패에 없는 카드입니다"}, status_code=409)
        _publish_from(b.roleId, b.cardId)
    return {"ok": True, "over": _over_limit(b.roleId)}


@app.post("/api/interrogate/vote")
def interrogate_vote(b: InterrogateVote):
    """토론 페이즈 추가 심문 1회 신청 — 과반수(2인이면 만장일치) 찬성 시 부여된다."""
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["clientId"] != b.clientId or r["mode"] != "human":
            return JSONResponse({"error": "그 배역으로 투표할 수 없습니다"}, status_code=403)
        ph = SC.phase_by_seq(ROOM["seq"])
        if ph.get("key") != "talk":
            return JSONResponse({"error": "토론 페이즈에서만 신청할 수 있습니다"}, status_code=409)
        budget = _interrogate_budget()
        if budget["bonusGranted"]:
            return {"ok": True, "budget": budget}
        votes = ROOM["interrogate"]["votes"]
        if b.roleId not in votes:
            votes.append(b.roleId)
        budget = _interrogate_budget()
        if budget["voteNeed"] > 0 and len(votes) >= budget["voteNeed"]:
            ROOM["interrogate"]["bonus"] = True
            ROOM["table"].append({"kind": "system", "broadcast": True,
                                  "text": "🗳️ 추가 심문 1회가 승인됐습니다."})
        bump()
        return {"ok": True, "budget": _interrogate_budget()}


@app.post("/api/interrogate")
def interrogate(b: Interrogate):
    """심층심문 — 상대가 지금 손패로 쥔 카드를 지목해 답을 요구한다. 카드 자체는 공개되지
    않는다 — 대답만 들을 뿐이고, 민감한 카드는 그 대답이 진실이 아닐 수도 있다(캐릭터가
    거짓/얼버무림으로 넘어간다). 어떤 증거를 대는지가 곧 추리다 — 증거 없이 물으면 기본
    확률, 엉뚱한 카드를 대면 오히려 확률이 떨어지고(허 찔러 넘어갈 여지를 준다), 시나리오가
    정한 정확한 카드를 짚으면 반드시 실토한다. 예산(1회)은 성패와 무관하게 소모된다."""
    with LOCK:
        r = ROOM["roles"].get(b.askerRoleId)
        if not r or r["clientId"] != b.clientId or r["mode"] != "human":
            return JSONResponse({"error": "그 배역으로 심문할 수 없습니다"}, status_code=403)
        ph = SC.phase_by_seq(ROOM["seq"])
        if ph.get("key") != "talk":
            return JSONResponse({"error": "심층심문은 토론 페이즈에서만 할 수 있습니다"}, status_code=409)
        if b.askerRoleId == b.targetRoleId:
            return JSONResponse({"error": "자기 자신은 심문할 수 없습니다"}, status_code=409)
        if b.targetRoleId not in ROOM["roles"]:
            return JSONResponse({"error": "없는 배역"}, status_code=404)
        budget = _interrogate_budget()
        if budget["remaining"] <= 0:
            return JSONResponse({"error": "이번 토론에서 쓸 수 있는 심문 횟수를 다 썼습니다"}, status_code=409)
        if b.cardId not in ROOM["hands"].get(b.targetRoleId, []):
            return JSONResponse({"error": "그 배역이 지금 들고 있는 카드가 아닙니다"}, status_code=409)

        evid_id = (b.evidenceCardId or "").strip()
        if evid_id:
            has_access = evid_id in ROOM["hands"].get(b.askerRoleId, []) or evid_id in ROOM["revealed"]
            if not has_access:
                return JSONResponse({"error": "내가 갖고 있지 않은 카드는 증거로 댈 수 없습니다"}, status_code=409)

        card = SC.get_card(b.cardId)
        target = SC.get_character(b.targetRoleId) or {}
        asker = SC.get_character(b.askerRoleId) or {}
        entry = (getattr(SC, "INTERROGATE", {}) or {}).get(b.targetRoleId, {}).get(b.cardId)

        if entry:
            if evid_id and evid_id == entry.get("rebuttal"):
                told_truth = True
            elif evid_id:
                told_truth = random.random() < INTERROGATE_TRUTH_WRONG_EVIDENCE
            else:
                told_truth = random.random() < INTERROGATE_TRUTH_BASE
            outcome = "truth" if told_truth else "evasive"
            line = entry["truth"] if told_truth else entry["evasive"]
        else:
            intro = (getattr(SC, "INTERROGATE_PLAIN", {}) or {}).get(b.targetRoleId, "")
            outcome, line = "plain", f'{intro} 「{card["title"]}」— {card["text"]}'.strip()

        ROOM["interrogate"]["used"] += 1

        where = f'{card["locName"]} · {card["spot"]}' if card.get("spot") else card["locName"]
        badge = {"truth": "🗣️ 실토", "evasive": "🌀 얼버무림", "plain": "💬 답변"}[outcome]
        header = f'{badge} — {asker.get("name","")} → {target.get("name","")} · [{where}] 「{card["title"]}」'
        ROOM["table"].append({"kind": "interrogate", "broadcast": True,
                              "askerRoleId": b.askerRoleId, "targetRoleId": b.targetRoleId,
                              "cardId": b.cardId, "outcome": outcome, "text": header, "line": line})
        bump()
        return {"ok": True, "outcome": outcome, "line": line, "budget": _interrogate_budget()}


@app.get("/api/hand/{role_id}")
def get_hand(role_id: str, clientId: str = ""):
    with LOCK:
        r = ROOM["roles"].get(role_id)
        if not r or r["clientId"] != clientId:  # 엄격: 내 손패만
            return JSONResponse({"error": "권한 없음"}, status_code=403)
        return {"hand": [SC.public_card(c) for c in ROOM["hands"].get(role_id, [])]}


# ── 에이전트(코드 세션) 원격 조종: GM 읽기 + AI 배역 대리 행동 ──
@app.get("/api/gm")
def gm(key: str = ""):
    if not _agent_ok(key):
        return JSONResponse({"error": "key"}, status_code=403)
    with LOCK:
        return {
            "seq": ROOM["seq"], "round": current_round(ROOM["seq"]),
            "phase": SC.phase_by_seq(ROOM["seq"]),
            "roles": {rid: {"mode": r["mode"], "claimed": r["clientId"] is not None} for rid, r in ROOM["roles"].items()},
            "table": ROOM["table"],
            "revealed": [SC.public_card(c) for c in ROOM["revealed"]],
            "hands": {rid: [SC.public_card(c) for c in cs] for rid, cs in ROOM["hands"].items()},
            "grades": ROOM["grades"],
            "finalAnswers": ROOM["finalAnswers"],
        }


@app.post("/api/agent/say")
def agent_say(b: AgentSay):
    if not _agent_ok(b.key):
        return JSONResponse({"error": "key"}, status_code=403)
    with LOCK:
        c = SC.get_character(b.roleId)
        if not c:
            return JSONResponse({"error": "없는 배역"}, status_code=404)
        ROOM["table"].append({"kind": "ai", "roleId": b.roleId, "speaker": c["name"], "text": b.text.strip()})
        bump()
    return {"ok": True}


@app.post("/api/agent/investigate")
def agent_investigate(b: AgentCard):
    if not _agent_ok(b.key):
        return JSONResponse({"error": "key"}, status_code=403)
    with LOCK:
        err = _try_investigate(b.roleId, b.cardId)
        if err:
            return JSONResponse({"error": err}, status_code=409)
    return {"card": SC.public_card(b.cardId)}


@app.post("/api/turn/next")
def turn_next(b: TurnReq):
    """다음 조사 차례로 넘기기 — 호스트/GM, 또는 현재 차례 당사자. 호스트 미설정 시 통과."""
    with LOCK:
        role = ROOM["roles"].get(b.roleId) or {}
        allowed = _agent_ok(b.key) or (b.roleId and b.roleId == ROOM.get("turn") and role.get("clientId") == b.clientId)
        if ROOM.get("host") is not None:
            allowed = allowed or _is_host(b.clientId)
        else:
            allowed = True
        if not allowed:
            return JSONResponse({"error": "권한 없음"}, status_code=403)
        _advance_turn()
        return {"ok": True, "turn": ROOM.get("turn")}


@app.post("/api/ai-investigate")
def ai_investigate_auto(b: TurnReq):
    """AI 배역 자동 조사(휴리스틱, 즉시). 대상 미지정 시 현재 차례 배역."""
    with LOCK:
        rid = b.roleId or ROOM.get("turn")
        if not rid or rid not in ROOM["roles"]:
            return JSONResponse({"error": "대상 배역 없음"}, status_code=400)
        allowed = _agent_ok(b.key) or (ROOM.get("host") is None) or _is_host(b.clientId)
        if not allowed:
            return JSONResponse({"error": "권한 없음"}, status_code=403)
        if _ap_for(ROOM["seq"]) <= 0:
            return JSONResponse({"error": "조사 페이즈가 아닙니다"}, status_code=409)
        remaining = _ap_for(ROOM["seq"]) - _round_checks(rid, current_round(ROOM["seq"]))
        picks = _ai_pick(rid, remaining)
        if ROOM.get("turn") == rid:
            _advance_turn()
        cat = {c["id"]: c for c in SC.CARDS}
    return {"ok": True, "roleId": rid,
            "picked": [{"id": i, "title": cat[i]["title"], "loc": cat[i]["loc"], "locName": cat[i]["locName"]} for i in picks]}


@app.get("/api/events")
def events(key: str = "", since: int = 0, wait: int = 0):
    """진행 세션이 따라 읽는 사건 목록. since 이후 것만 준다.

    세션은 푸시를 못 받으니 스스로 물어봐야 한다. wait를 주면 새 사건이 생길 때까지
    그만큼(최대 25초) 붙들고 있다가 답한다 — 짧은 간격으로 되묻지 않아도 되도록.
    새 게 없으면 빈 목록으로 돌아온다.
    """
    if not _agent_ok(key):
        return JSONResponse({"error": "key"}, status_code=403)
    deadline = time.monotonic() + max(0, min(25, wait))
    while True:
        with LOCK:
            evs = [e for e in ROOM.get("events", []) if e["id"] > since]
            all_ev = ROOM.get("events") or []
            cursor = all_ev[-1]["id"] if all_ev else 0
            ph = SC.phase_by_seq(ROOM["seq"])
            turn = ROOM.get("turn")
        if evs or time.monotonic() >= deadline:
            return {"cursor": cursor, "events": evs, "turn": turn,
                    "phase": {"seq": ph["seq"], "name": ph["name"],
                              "key": ph.get("key", ""), "ap": int(ph.get("ap", 0) or 0)}}
        time.sleep(0.6)


@app.get("/api/relay-next")
def relay_next(key: str = "", clientId: str = ""):
    """지금 말할 차례인 AI 배역만 알려준다. 내용은 주지 않는다.

    진행 세션은 이 이름 하나만 받아서 그 배역의 서브에이전트를 띄우면 된다.
    카드도 대본도 진행 세션을 지나가지 않는다.
    """
    if not (_agent_ok(key) or _is_host(clientId)):
        return JSONResponse({"error": "key"}, status_code=403)
    rid = _pick_reactor()
    if not rid:
        return JSONResponse({"error": "AI 배역이 없습니다"}, status_code=409)
    c = SC.get_character(rid) or {}
    return {"roleId": rid, "name": c.get("name", rid)}


@app.get("/api/relay/{role_id}", response_class=PlainTextResponse)
def relay_prompt(role_id: str, key: str = "", clientId: str = ""):
    """API 키가 없을 때 쓰는 통로 — 그 배역 하나짜리 지시문을 글로 내준다.

    보통 채팅 세션에는 임의의 주소로 요청을 보낼 손이 없다. 그래서 서버가 대신
    부를 수 없고, 사람이 이 글을 복사해 채팅에 넣고 돌아온 대사를 도로 붙여넣는다.
    ANTHROPIC_API_KEY를 넣으면 서버가 직접 부르므로 이 통로는 필요 없어진다.

    담기는 것은 공개 카드와 '그 배역 자신의 손패'뿐이다. 남의 손패는 들어가지 않는다.
    """
    if not (_agent_ok(key) or _is_host(clientId)):
        return PlainTextResponse("key", status_code=403)
    if not SC.get_character(role_id):
        return PlainTextResponse("없는 배역", status_code=404)
    with LOCK:
        r = ROOM["roles"].get(role_id) or {}
    if r.get("mode") != "ai":
        return PlainTextResponse("사람이 맡은 배역입니다", status_code=409)
    return _role_prompt(role_id, _pick_nudge(role_id))


@app.get("/relay")
def relay_page():
    return FileResponse(_HERE / "relay.html")


@app.get("/api/handoff", response_class=PlainTextResponse)
def handoff_brief(key: str = "", base: str = ""):
    """진행 세션이 스스로 받아 가는 지침. 배포된 코드에서 만들어지므로 낡을 일이 없다.

    저장소를 진행 세션에 주지 않기로 한 이상, 지침을 사람이 복사해 나르면 판마다
    조금씩 어긋난다. 이 주소 하나만 알려주면 그 문제가 없어진다.
    진상은 들어 있지 않다.
    """
    if not _agent_ok(key):
        return PlainTextResponse("key", status_code=403)
    # 배포에 LLM 키가 있느냐에 따라 지침이 갈린다 — 없는데 ai-react를 알려주면 502만 만난다
    has_llm = bool(ANTHROPIC_API_KEY and anthropic) or BACKEND == "ollama"
    return handoff.runner_brief(SC, base or "", key or "<AGENT_KEY>", has_llm=has_llm)


@app.get("/api/player-notice", response_class=PlainTextResponse)
def player_notice(base: str = ""):
    """플레이어에게 뿌릴 안내문. 비밀이 없으므로 키를 걸지 않는다."""
    return handoff.player_notice(SC, base or "")


@app.get("/handoff")
def handoff_page():
    return FileResponse(_HERE / "handoff.html")


@app.get("/api/brief")
def brief(key: str = ""):
    """세션 에이전트(코워크 GM)용 브리핑 — 각 배역 손패의 '내용 포함' + 공개 카드. GM 전용."""
    if not _agent_ok(key):
        return JSONResponse({"error": "key"}, status_code=403)
    with LOCK:
        cat = {c["id"]: c for c in SC.CARDS}
        # 손패는 '몇 장 들었나'까지만. 남이 조사한 카드의 내용은 진행 세션도 보지 않는다 —
        # 진행자가 그걸 다 보고 있으면 판이 끝나기 전에 답을 짚어낼 수 있고,
        # 그러면 '알아도 말하지 않는다'는 약속에 기대야 한다. 안 보는 게 낫다.
        hand_counts = {rid: len(ids) for rid, ids in ROOM["hands"].items() if ids}
        revealed = [{"id": i, "title": cat[i]["title"], "locName": cat[i]["locName"],
                     "text": cat[i].get("text", ""), "hint": cat[i].get("hint", "")}
                    for i in ROOM["revealed"] if i in cat]
        ph = SC.phase_by_seq(ROOM["seq"])
        return {"phase": ph["name"], "round": current_round(ROOM["seq"]), "turn": ROOM.get("turn"),
                "turnOrder": _turn_order(), "handCounts": hand_counts, "revealed": revealed}


@app.post("/api/agent/reveal")
def agent_reveal(b: AgentCard):
    if not _agent_ok(b.key):
        return JSONResponse({"error": "key"}, status_code=403)
    with LOCK:
        _publish(b.cardId)
    return {"ok": True}


@app.post("/api/agent/advance")
def agent_advance(b: KeyOnly):
    if not _agent_ok(b.key):
        return JSONResponse({"error": "key"}, status_code=403)
    return _advance()


@app.post("/api/agent/narrate")
def agent_narrate(b: AgentSay):  # roleId 무시, text=GM 내레이션(전체 방송)
    if not _agent_ok(b.key):
        return JSONResponse({"error": "key"}, status_code=403)
    with LOCK:
        ROOM["table"].append({"kind": "system", "broadcast": True, "text": b.text.strip()})
        bump()
    return {"ok": True}


@app.post("/api/advance")
def advance(b: HostReq):
    # 호스트가 지정돼 있으면 호스트만, 없으면 누구나(현행 앱 호환)
    if ROOM.get("host") is not None and not _is_host(b.clientId):
        return JSONResponse({"error": "host"}, status_code=403)
    return _advance()


def _advance():
    _ev("phase_leaving", name=SC.phase_by_seq(ROOM["seq"])["name"])
    with LOCK:
        if ROOM["seq"] < len(SC.PHASES):
            ROOM["seq"] += 1
            seq = ROOM["seq"]
            ph = SC.phase_by_seq(seq)
            il = SC.interlude_for(seq)
            if il:
                ROOM["table"].append({"kind": "system", "broadcast": True, "text": f"📻 교내방송 — {il}"})
            # phase.gm은 진행자에게 주는 지시문이다("…확실히 짚어주세요"). 테이블에 넣으면
            # 플레이어 대화창에 그대로 뜬다. 막이 바뀌었다는 표시만 남긴다.
            ROOM["table"].append({"kind": "system", "text": f'— {ph["name"]} —'})
            _ev("phase", name=ph["name"], key=ph.get("key", ""), min=ph.get("min", 0),
                ap=int(ph.get("ap", 0) or 0), gm=ph.get("gm", ""), interlude=il or "")
            _reset_turn_for_seq(seq)   # 조사 페이즈면 순번 초기화
            _auto_reveal_obligatory()
            bump()
        return {"seq": ROOM["seq"]}


@app.post("/api/human-say")
def human_say(b: HumanSay):
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["clientId"] != b.clientId:
            return JSONResponse({"error": "그 배역으로 말할 수 없습니다"}, status_code=403)
        c = SC.get_character(b.roleId)
        ROOM["table"].append({"kind": "human", "roleId": b.roleId, "speaker": c["name"], "text": b.text.strip()})
        _ev("say", who="human", roleId=b.roleId, speaker=c["name"], text=b.text.strip())
        bump()
    return {"ok": True}


class Busy(RuntimeError):
    """다른 배역이 말하는 중."""


def _role_prompt(role_id: str, nudge: str = "") -> str:
    """그 배역 하나짜리 연기 지시문.

    들어가는 것: 공개된 카드(모두가 아는 것) + **그 배역 자신의 손패**.
    들어가지 않는 것: 남의 손패, 남의 비밀, 진상.
    조사해놓고 자기가 뭘 찾았는지 모르면 그걸로 방어도 추궁도 못 한다.
    """
    with LOCK:
        seq = ROOM["seq"]
        revealed = list(ROOM["revealed"])
        table = list(ROOM["table"])
        hand = list(ROOM["hands"].get(role_id, []))   # 자기 것만. 남의 손패는 넘기지 않는다.
    c = SC.get_character(role_id)
    for args in ((nudge, hand), (nudge,), ()):        # 아직 손패·nudge를 안 받는 시나리오도 있다
        try:
            return SC.build_play_prompt(c, seq, revealed, table, *args)
        except TypeError:
            continue
    return SC.build_play_prompt(c, seq, revealed, table)


def _speak(role_id: str, nudge: str = "") -> dict:
    """AI 배역 한 명에게 한마디 시킨다. 프롬프트는 그 배역 것만 들어간다."""
    with LOCK:
        r = ROOM["roles"].get(role_id)
        if not r or r["mode"] != "ai":
            raise ValueError("AI 배역이 아닙니다")
        if ROOM["typing"]:
            raise Busy("다른 배역이 말하는 중입니다")
        ROOM["typing"] = role_id
        bump()
        seq = ROOM["seq"]
        revealed = list(ROOM["revealed"])
        table = list(ROOM["table"])
    c = SC.get_character(role_id)
    try:
        system = _role_prompt(role_id, nudge)
        reply = llm(system, f"이제 '{c['name']}'로서 다음 한마디를 하라 (1~3문장).", 400, fast=True)
        reply = re.sub(rf"^{re.escape(c['name'])}\s*[:：]\s*", "", reply or "").strip()
    except Exception:
        with LOCK:
            ROOM["typing"] = None
            bump()
        raise
    entry = {"kind": "ai", "roleId": role_id, "speaker": c["name"], "text": reply or "…"}
    with LOCK:
        ROOM["table"].append(entry)
        _ev("say", who="ai", roleId=role_id, speaker=c["name"], text=entry["text"])
        ROOM["typing"] = None
        bump()
    return entry


@app.post("/api/ai-say")
def ai_say(b: RoleOnly):
    try:
        _speak(b.roleId)
    except Busy as e:
        return JSONResponse({"error": str(e)}, status_code=429)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    return {"ok": True}


def _addressed_in(text: str, exclude: str = "") -> list[str]:
    """대사 안에서 이름이 불린 배역들. 이름을 부르면 그 사람이 대답한다 — 대화가 이어지는 핵심."""
    out = []
    for ch in SC.CHARACTERS:
        if ch["id"] == exclude:
            continue
        if ch["name"] in text or ch["name"][1:] in text:   # '문재이' / '재이' 둘 다
            out.append(ch["id"])
    return out


def _pick_reactor(exclude: list[str] | None = None) -> str | None:
    """지금 한마디 하기에 가장 자연스러운 AI 배역을 고른다.

    진행 세션이 매번 '누가 말할 차례냐'를 직접 판단하면 부담이 크고, 결국 한두 명만
    계속 떠들게 된다. 그래서 서버가 고른다 — 최근에 말한 사람은 빼고, 방금 공개된
    카드가 자기 구역·관심사인 배역에 가중치를 준다.
    """
    exclude = set(exclude or [])
    with LOCK:
        ais = [rid for rid, r in ROOM["roles"].items() if r["mode"] == "ai" and rid not in exclude]
        if not ais:
            return None
        # 최근 발언자 2명은 연속 발언을 피한다(그래도 후보가 없으면 되살린다)
        recent = [t.get("roleId") for t in ROOM["table"][-4:] if t.get("roleId")]
        fresh = [rid for rid in ais if rid not in recent[-2:]] or ais
        last_card = ROOM["revealed"][-1] if ROOM["revealed"] else None
        seq = ROOM["seq"]
        last = ROOM["table"][-1] if ROOM["table"] else {}
        last_text = str(last.get("text") or "")
        last_from = str(last.get("roleId") or "")
        spoke_n = {rid: sum(1 for t in ROOM["table"] if t.get("roleId") == rid) for rid in ais}
    card = SC.get_card(last_card) if last_card else None
    ai_cfg = getattr(SC, "INVEST_AI", {})
    chat_cfg = getattr(SC, "CHAT_AI", {})
    called = set(_addressed_in(last_text, exclude=last_from))

    def score(rid: str) -> tuple[float, int]:
        s = 0.0
        cfg = ai_cfg.get(rid) or {}
        if rid in called:
            s += 8.0                                       # 이름이 불렸으면 대답할 차례다
        if card:
            if card.get("loc") in (cfg.get("home") or []):
                s += 3.0                                   # 방금 열린 곳이 자기 구역이면 할 말이 있다
            s += float((cfg.get("interest") or {}).get(card["id"], 0) or 0)
        s += 2.0 * float((chat_cfg.get(rid) or {}).get("talk", 1.0))   # 원래 말이 많은 사람
        s -= spoke_n.get(rid, 0) * 0.8                     # 적게 말한 사람에게 자리를 준다
        return (s, -zlib.crc32(f"{rid}:{seq}".encode()) % 997)   # 동점은 결정적으로 가른다

    return max(fresh, key=score)


def _pick_nudge(rid: str) -> str:
    """이번 한마디의 결을 고른다. 매번 같은 결이면 금세 기계처럼 들린다."""
    nudges = getattr(SC, "CHAT_NUDGES", {})
    if not nudges:
        return ""
    with LOCK:
        last = ROOM["table"][-1] if ROOM["table"] else {}
        n_lines = len(ROOM["table"])
    ask_w = float((getattr(SC, "CHAT_AI", {}).get(rid) or {}).get("ask", 1.0))
    # 앞사람이 방금 말했으면 받아치는 쪽이 자연스럽고, 정적이 흘렀으면 새 화제를 꺼내야 한다.
    weights = {
        "react": 3.0 if last.get("text") else 0.5,
        "ask":   2.2 * ask_w,
        "press": 1.6 if last.get("kind") in ("ai", "human") else 0.3,
        "raise": 1.4,
        "mood":  0.7 if n_lines % 5 == 0 else 0.25,        # 가끔만. 자주 하면 겉돈다
    }
    keys = [k for k in weights if k in nudges]
    tot = sum(weights[k] for k in keys) or 1.0
    r = random.random() * tot
    for k in keys:
        r -= weights[k]
        if r <= 0:
            return nudges[k]
    return nudges.get("react", "")


# ── 자발 대화 ─────────────────────────────────────────────────────
# AI 배역이 불릴 때만 말하면 자판기처럼 보인다. 조용한 시간이 일정 이상 흐르면
# 서버가 스스로 한 명을 골라 말하게 한다. 사람이 말하면 물러나고, AI만 계속
# 떠들면 간격을 벌려서 사람이 낄 자리를 만든다.
CHAT = {
    "on": os.getenv("AUTO_CHAT", "1") != "0",
    "gap": float(os.getenv("AUTO_CHAT_GAP", "13")),   # 기본 침묵 허용치(초)
    "seenLen": 0, "lastAt": 0.0, "streak": 0, "busy": False,
}


def _chat_gap_now(ph: dict) -> float:
    """지금 얼마나 조용해야 AI가 입을 여는가."""
    gap = CHAT["gap"]
    if int(ph.get("ap", 0) or 0) > 0:
        gap *= 2.6                       # 조사 페이즈 — 다들 카드 보는 중이라 조용해야 한다
    gap *= 1.0 + CHAT["streak"] * 0.55   # AI만 연달아 떠들수록 물러난다
    return gap


def _chatter_tick():
    if not CHAT["on"]:
        return
    now = time.monotonic()
    with LOCK:
        ph = SC.phase_by_seq(ROOM["seq"])
        n = len(ROOM["table"])
        typing = ROOM["typing"]
        last = ROOM["table"][-1] if ROOM["table"] else {}
        has_ai = any(r["mode"] == "ai" for r in ROOM["roles"].values())
    if ph.get("key") == "reveal" or not has_ai:
        return
    if n != CHAT["seenLen"]:              # 방금 누가 말했다 — 시계를 다시 잡는다
        CHAT["seenLen"] = n
        CHAT["lastAt"] = now
        CHAT["streak"] = CHAT["streak"] + 1 if last.get("kind") == "ai" else 0
        return
    if typing or CHAT["busy"]:
        return
    if now - CHAT["lastAt"] < _chat_gap_now(ph):
        return
    CHAT["busy"] = True
    try:
        rid = _pick_reactor()
        if rid:
            _speak(rid, _pick_nudge(rid))
    except Exception:                    # 한 번 실패해도 루프는 계속 돈다
        pass
    finally:
        CHAT["busy"] = False
        CHAT["lastAt"] = time.monotonic()


def _chatter_loop():
    while True:
        time.sleep(2.0)
        try:
            _chatter_tick()
        except Exception:                # noqa: BLE001
            pass


@app.on_event("startup")
def _start_chatter():
    threading.Thread(target=_chatter_loop, daemon=True).start()


@app.post("/api/chat")
def chat_ctl(b: ChatCtl):
    """자발 대화 on/off와 속도. 토론이 뜨거우면 끄고, 식으면 켠다."""
    if not (_agent_ok(b.key) or _is_host(b.clientId) or ROOM.get("host") is None):
        return JSONResponse({"error": "권한 없음"}, status_code=403)
    if b.on is not None:
        CHAT["on"] = bool(b.on)
        CHAT["lastAt"] = time.monotonic()
    if b.gap is not None:
        CHAT["gap"] = max(4.0, min(90.0, float(b.gap)))
    with LOCK:
        bump()
    return {"ok": True, "on": CHAT["on"], "gap": CHAT["gap"]}


@app.post("/api/ai-react")
def ai_react(b: TurnReq):
    """AI 배역 중 하나를 골라 한마디 시킨다 — 진행 세션의 '누구 시킬까' 부담을 덜어준다."""
    rid = b.roleId or _pick_reactor()
    if not rid:
        return JSONResponse({"error": "AI 배역이 없습니다"}, status_code=409)
    try:
        entry = _speak(rid, _pick_nudge(rid))
    except Busy as e:
        return JSONResponse({"error": str(e)}, status_code=429)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    CHAT["lastAt"] = time.monotonic()          # 방금 말했으니 자발 발언 시계를 다시 잡는다
    return {"ok": True, "roleId": rid, "speaker": entry["speaker"], "text": entry["text"]}


def _grade(c: dict, answers: list[str]) -> dict:
    raw = llm(SC.build_grade_prompt(c, answers), "채점 JSON만 출력하라.", 500)
    o = _parse_json(raw)
    ncount = len(c["sins"]) if c["sins"] else 0
    g = {
        "name": c["name"],
        "selfAccused": bool(o.get("selfAccused", False)),
        "sinsAcknowledged": max(0, min(ncount, int(o.get("sinsAcknowledged", 0) or 0))),
        "osewonIdentified": bool(o.get("osewonIdentified", False)),
        "score": max(0, min(40, int(o.get("score", 0) or 0))),
        "verdict": str(o.get("verdict", "") or ""),
    }
    # 후더닛 시나리오(예: subway)용 추가 필드 — 있을 때만 보존(자기지목형 시나리오엔 영향 없음).
    if "culpritGuess" in o:
        g["culpritGuess"] = str(o.get("culpritGuess") or "unknown")
    if "correct" in o:
        g["correct"] = bool(o.get("correct", False))
    if "cluesFound" in o:
        g["cluesFound"] = max(0, int(o.get("cluesFound", 0) or 0))
    if isinstance(o.get("tags"), list):
        g["tags"] = o["tags"]
    return g


@app.post("/api/final-answers")
def final_answers(b: FinalAnswers):
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["clientId"] != b.clientId:
            return JSONResponse({"error": "그 배역의 답이 아닙니다"}, status_code=403)
    # 백엔드(API 키)가 없으면 AI 채점 대신 답변을 보관 → 진행자(GM)가 채점/엔딩 내레이션
    if not backend_ready()[0]:
        with LOCK:
            ROOM["finalAnswers"][b.roleId] = list(b.answers)
            bump()
        return {"pending": True, "answers": list(b.answers)}
    c = SC.get_character(b.roleId)
    try:
        grade = _grade(c, b.answers)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    with LOCK:
        ROOM["grades"][b.roleId] = grade
        ROOM["finalAnswers"][b.roleId] = list(b.answers)
        bump()
    return {"grade": grade}


@app.post("/api/ai-final")
def ai_final(b: RoleOnly):
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["mode"] != "ai":
            return JSONResponse({"error": "AI 배역이 아닙니다"}, status_code=409)
        revealed = list(ROOM["revealed"])
        table = list(ROOM["table"])
    c = SC.get_character(b.roleId)
    try:
        raw = llm(SC.build_final_answer_prompt(c, revealed, table), "JSON만 출력하라.", 700)
        answers = _parse_json(raw).get("answers", [])
        if not isinstance(answers, list) or not answers:
            answers = ["(답변 없음)"]
        grade = _grade(c, [str(x) for x in answers])
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    with LOCK:
        ROOM["grades"][b.roleId] = grade
        bump()
    return {"answers": answers, "grade": grade}


@app.post("/api/reset")
def reset(b: HostReq):
    global ROOM
    with LOCK:
        if ROOM.get("host") not in (None, b.clientId):
            return JSONResponse({"error": "host"}, status_code=403)
        ROOM = fresh_room()
        # 호스트도 함께 푼다. 붙들고 있으면 그 브라우저가 사라졌을 때 방이 영영 잠긴다 —
        # 초기화한 사람은 곧바로 다시 잡으면 된다(클라이언트가 이어서 요청한다).
    return {"ok": True}


@app.get("/")
def landing():
    # 노아르 허브(로고·포스터·호스트/참가자) — 여기서 사건을 골라 /play 로 진입
    p = _HERE / "landing.html"
    return FileResponse(p if p.exists() else _HERE / "index.html")


@app.get("/play")
def play():
    return FileResponse(_HERE / "index.html")


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    import uvicorn
    ok, label = backend_ready()
    ip = lan_ip()
    print("=" * 56)
    print("  PIMMmurderboard · 졸업사진(卒業寫眞)")
    print(f"  AI 백엔드: {label}" + ("" if ok else "  ⚠ (미준비 — .env 확인)"))
    print("  브라우저에서 열기:")
    print(f"    이 컴퓨터    →  http://127.0.0.1:{PORT}")
    print(f"    같은 와이파이 →  http://{ip}:{PORT}   (폰·다른 PC는 이 주소로)")
    print("=" * 56)
    uvicorn.run(app, host=HOST, port=PORT)
