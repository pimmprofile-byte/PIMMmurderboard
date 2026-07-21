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
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

_HERE = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(_HERE / ".env")
except Exception:
    pass

import scenario as SC  # noqa: E402

BACKEND = os.getenv("LLM_BACKEND", "claude").lower()
CLAUDE_MODEL = os.getenv("REUNION_MODEL") or os.getenv("PIMM_MODEL") or "claude-opus-4-8"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")
HOST = os.getenv("REUNION_HOST", "0.0.0.0")
# 호스팅(Render 등)은 PORT를 주입 → 그걸 우선 사용, 로컬은 REUNION_PORT/기본값
PORT = int(os.getenv("PORT") or os.getenv("REUNION_PORT", "8790"))
AGENT_KEY = os.getenv("AGENT_KEY", "")  # 에이전트(코드 세션) 원격 조종 키(설정 시 그 키 필요, 미설정 시 개방)

try:
    import anthropic
except Exception:
    anthropic = None
_ac = None


def _claude(system: str, user: str, mt: int) -> str:
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
            m = _ac.messages.create(model=CLAUDE_MODEL, max_tokens=mt, system=system,
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


def _ollama(system: str, user: str, mt: int) -> str:
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


def llm(system: str, user: str, mt: int = 400) -> str:
    return _ollama(system, user, mt) if BACKEND == "ollama" else _claude(system, user, mt)


def backend_ready() -> tuple[bool, str]:
    if BACKEND == "ollama":
        return True, f"Ollama · {OLLAMA_MODEL}"
    if not ANTHROPIC_API_KEY:
        return False, "Claude · API 키 미설정 (.env)"
    if anthropic is None:
        return False, "Claude · anthropic SDK 미설치"
    return True, f"Claude · {CLAUDE_MODEL}"


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
        "roles": {c["id"]: {"mode": "open", "clientId": None} for c in SC.CHARACTERS},
        "table": [{"kind": "system", "text": f'{SC.PHASES[0]["name"]} — {SC.PHASES[0]["gm"]}'}],
        "revealed": [],           # 전체공개 card id
        "hands": {},              # roleId -> [cardId] (손패, 비공개 · 조사/마킹 통합)
        "checkedRound": {},       # roleId -> {cardId: round} (턴별 조사 수 제한 계산용)
        "grades": {},             # roleId -> grade dict (name 포함)
        "finalAnswers": {},       # roleId -> [answer str] (백엔드 미설정 시 진행자 수동채점용 보관)
        "typing": None,
    }


ROOM = fresh_room()


def bump():
    ROOM["rev"] += 1


def _auto_reveal_obligatory():
    return  # '전체공개' 개념 미사용(우선) — 공개의무 카드도 GM이 대화로 내레이션한다


def public_state() -> dict:
    with LOCK:
        seq = ROOM["seq"]
        ph = SC.phase_by_seq(seq)
        ending = None
        g = ROOM["grades"]
        if all(rid in g for rid in ("sim", "yu", "lee")):
            ending = SC.compute_ending(g)
        cur = current_round(seq)
        ap = int(ph.get("ap", 0) or 0)
        # 내용 없는 마킹 현황(누가 어떤 카드를 조사했는지 id만) + 이번 턴 남은 조사 수
        checked = {rid: list(cs) for rid, cs in ROOM["hands"].items() if cs}
        used = {rid: sum(1 for r in cm.values() if r == cur) for rid, cm in ROOM["checkedRound"].items()}
        return {
            "rev": ROOM["rev"], "seq": seq, "round": cur,
            "phase": {"seq": ph["seq"], "key": ph["key"], "name": ph["name"], "gm": ph["gm"], "ap": ap, "min": ph["min"]},
            "roles": {rid: {"mode": r["mode"], "claimed": r["clientId"] is not None} for rid, r in ROOM["roles"].items()},
            "table": ROOM["table"],
            "revealed": [SC.public_card(cid) for cid in ROOM["revealed"]],
            "revealedIds": list(ROOM["revealed"]),
            "checked": checked,
            "usedAP": used,
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


class CardOnly(BaseModel):
    cardId: str


class ClientOnly(BaseModel):
    clientId: str


class Investigate(BaseModel):
    cardId: str
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
                         "requires": c.get("requires"), "obligatory": c.get("reveal") == "obligatory"}
                        for c in SC.CARDS]
    return d


@app.get("/api/state")
def state():
    return public_state()


@app.post("/api/claim")
def claim(b: Claim):
    with LOCK:
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
        r = ROOM["roles"].get(b.roleId)
        if r and r["clientId"] == b.clientId:
            r["clientId"] = None
            r["mode"] = "open"
            bump()
    return {"ok": True}


@app.post("/api/setai")
def setai(b: SetAI):
    with LOCK:
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


def _ap_for(seq: int) -> int:
    return int(SC.phase_by_seq(seq).get("ap", 0) or 0)


def _round_checks(role_id: str, rnd: int) -> int:
    """이번 조사 라운드에 이 배역이 조사한 카드 수."""
    return sum(1 for r in ROOM["checkedRound"].get(role_id, {}).values() if r == rnd)


def _try_investigate(role_id: str, card_id: str, enforce_ap: bool = True) -> str | None:
    c = SC.get_card(card_id)
    if not c:
        return "없는 카드"
    cur = current_round(ROOM["seq"])
    if c["round"] > cur:
        return f"아직 조사할 수 없습니다 (조사 R{c['round']}에 열림)"
    ap = _ap_for(ROOM["seq"])
    already = card_id in ROOM["hands"].get(role_id, [])
    if enforce_ap and not already:
        if ap <= 0:
            return "지금은 조사 턴이 아닙니다 (조사 페이즈에서만 열 수 있어요)"
        if _round_checks(role_id, cur) >= ap:
            return f"이번 조사 턴({cur}라운드)에 열 수 있는 {ap}장을 모두 사용했습니다"
    req = c.get("requires")
    seen = set(ROOM["revealed"]) | set(ROOM["hands"].get(role_id, []))
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
    return _try_investigate(role_id, card_id)


def _publish(card_id: str) -> None:
    for hl in ROOM["hands"].values():
        if card_id in hl:
            hl.remove(card_id)
    if card_id not in ROOM["revealed"]:
        ROOM["revealed"].append(card_id)
        bump()


@app.post("/api/investigate")
def investigate(b: Investigate):
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["clientId"] != b.clientId:
            return JSONResponse({"error": "그 배역으로 조사할 수 없습니다"}, status_code=403)
        err = _try_investigate(b.roleId, b.cardId)
        if err:
            return JSONResponse({"error": err}, status_code=409)
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
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["clientId"] != b.clientId:
            return JSONResponse({"error": "권한 없음"}, status_code=403)
        _publish(b.cardId)
    return {"ok": True}


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
    return advance()


@app.post("/api/agent/narrate")
def agent_narrate(b: AgentSay):  # roleId 무시, text=GM 내레이션(전체 방송)
    if not _agent_ok(b.key):
        return JSONResponse({"error": "key"}, status_code=403)
    with LOCK:
        ROOM["table"].append({"kind": "system", "broadcast": True, "text": b.text.strip()})
        bump()
    return {"ok": True}


@app.post("/api/advance")
def advance():
    with LOCK:
        if ROOM["seq"] < len(SC.PHASES):
            ROOM["seq"] += 1
            seq = ROOM["seq"]
            ph = SC.phase_by_seq(seq)
            il = SC.interlude_for(seq)
            if il:
                ROOM["table"].append({"kind": "system", "broadcast": True, "text": f"📻 교내방송 — {il}"})
            ROOM["table"].append({"kind": "system", "text": f'{ph["name"]} — {ph["gm"]}'})
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
        bump()
    return {"ok": True}


@app.post("/api/ai-say")
def ai_say(b: RoleOnly):
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["mode"] != "ai":
            return JSONResponse({"error": "AI 배역이 아닙니다"}, status_code=409)
        if ROOM["typing"]:
            return JSONResponse({"error": "다른 배역이 말하는 중입니다"}, status_code=429)
        ROOM["typing"] = b.roleId
        bump()
        seq = ROOM["seq"]
        revealed = list(ROOM["revealed"])
        table = list(ROOM["table"])
    c = SC.get_character(b.roleId)
    try:
        reply = llm(SC.build_play_prompt(c, seq, revealed, table),
                    f"이제 '{c['name']}'로서 다음 한마디를 하라 (1~3문장).", 400)
        reply = re.sub(rf"^{re.escape(c['name'])}\s*[:：]\s*", "", reply or "").strip()
    except Exception as e:  # noqa: BLE001
        with LOCK:
            ROOM["typing"] = None
            bump()
        return JSONResponse({"error": str(e)}, status_code=502)
    with LOCK:
        ROOM["table"].append({"kind": "ai", "roleId": b.roleId, "speaker": c["name"], "text": reply or "…"})
        ROOM["typing"] = None
        bump()
    return {"ok": True}


def _grade(c: dict, answers: list[str]) -> dict:
    raw = llm(SC.build_grade_prompt(c, answers), "채점 JSON만 출력하라.", 500)
    o = _parse_json(raw)
    ncount = len(c["sins"]) if c["sins"] else 0
    return {
        "name": c["name"],
        "selfAccused": bool(o.get("selfAccused", False)),
        "sinsAcknowledged": max(0, min(ncount, int(o.get("sinsAcknowledged", 0) or 0))),
        "osewonIdentified": bool(o.get("osewonIdentified", False)),
        "score": max(0, min(40, int(o.get("score", 0) or 0))),
        "verdict": str(o.get("verdict", "") or ""),
    }


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
def reset():
    global ROOM
    with LOCK:
        ROOM = fresh_room()
    return {"ok": True}


@app.get("/")
def index():
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
