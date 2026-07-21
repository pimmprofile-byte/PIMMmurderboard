"""
PIMMmurderboard · 그해 여름, 동창회 — 로컬 멀티플레이 게임 서버

각자 자기 PC/폰으로 접속해 함께 플레이한다(같은 와이파이). 서버가 '방(room)' 상태를
쥐고, 각 기기는 폴링으로 동기화한다. 배역의 비밀은 그 배역을 맡은 기기에만 내려간다.
사람이 맡지 않은 배역은 AI가 대본대로 참여한다(거짓말·의심·투표까지).

백엔드 교체형:
    - 기본: Claude API  (.env 의 ANTHROPIC_API_KEY · 한국어·연기 최상, 종량 과금)
    - 무료: 로컬 Ollama (.env 에 LLM_BACKEND=ollama · 한국어는 qwen2.5 권장)

실행:
    pip install -r requirements.txt
    cp .env.example .env      # ANTHROPIC_API_KEY 입력 (Ollama면 키 불필요)
    python server.py          # 켜지면 접속 주소가 출력됩니다 (같은 와이파이면 폰으로도 접속)
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

# ── 설정 ──
BACKEND = os.getenv("LLM_BACKEND", "claude").lower()
CLAUDE_MODEL = os.getenv("REUNION_MODEL") or os.getenv("PIMM_MODEL") or "claude-opus-4-8"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")
HOST = os.getenv("REUNION_HOST", "0.0.0.0")  # 같은 와이파이의 다른 기기 접속 허용
PORT = int(os.getenv("REUNION_PORT", "8790"))

# ── LLM ──
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


def _table_text(table: list[dict]) -> str:
    talk = [t for t in table if t.get("kind") != "system" and t.get("text")]
    if not talk:
        return "(아직 아무 말도 오가지 않았다. 네가 먼저 운을 떼도 된다.)"
    return "\n".join(f"{t.get('speaker','?')}: {t['text']}" for t in talk)


# ── 방(room) 상태 ──
LOCK = threading.RLock()
ROOM: dict = {}


def fresh_room() -> dict:
    return {
        "rev": 1,
        "roles": {c["id"]: {"mode": "open", "clientId": None} for c in SC.CHARACTERS},  # open|human|ai
        "table": [{"kind": "system", "text": f'{SC.PHASES[0]["name"]} — {SC.PHASES[0]["gm"]}'}],
        "round": 1,
        "votes": {},        # roleId -> suspectId
        "voteReasons": {},  # roleId -> reason (AI)
        "typing": None,     # roleId 생성 중
        "revealed": False,
    }


ROOM = fresh_room()


def bump():
    ROOM["rev"] += 1


def public_state() -> dict:
    with LOCK:
        return {
            "rev": ROOM["rev"],
            "roles": {rid: {"mode": r["mode"], "claimed": r["clientId"] is not None}
                      for rid, r in ROOM["roles"].items()},
            "table": ROOM["table"],
            "round": ROOM["round"],
            "votes": ROOM["votes"],
            "voteReasons": ROOM["voteReasons"],
            "typing": ROOM["typing"],
            "revealed": ROOM["revealed"],
            "culprit": ({"id": SC.CULPRIT_ID, "name": SC.get_character(SC.CULPRIT_ID)["name"],
                         "solution": SC.SOLUTION} if ROOM["revealed"] else None),
        }


# ── API ──
app = FastAPI(title="PIMMmurderboard")


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


class HumanVote(BaseModel):
    roleId: str
    clientId: str
    suspectId: str


@app.get("/api/scenario")
def scenario():
    ok, label = backend_ready()
    d = SC.public_scenario()
    d["backend"] = {"ok": ok, "label": label}
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
        # 같은 clientId가 다른 배역을 갖고 있으면 해제
        for rr in ROOM["roles"].values():
            if rr["clientId"] == b.clientId:
                rr["clientId"] = None
                rr["mode"] = "open"
        r["clientId"] = b.clientId
        r["mode"] = "human"
        bump()
    return {"ok": True}


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
        if not r:
            return JSONResponse({"error": "없는 배역"}, status_code=404)
        if r["clientId"] and r["clientId"] != clientId:
            return JSONResponse({"error": "자기 배역만 열람할 수 있습니다"}, status_code=403)
    s = SC.private_sheet(role_id)
    return s


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
        snapshot = list(ROOM["table"])
    c = SC.get_character(b.roleId)
    try:
        reply = llm(SC.build_play_prompt(c),
                    f"다음은 지금까지 테이블에서 오간 대화다.\n\n{_table_text(snapshot)}\n\n이제 '{c['name']}'로서 다음 한마디를 하라 (1~3문장).", 400)
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


@app.post("/api/next-round")
def next_round():
    with LOCK:
        if ROOM["round"] < len(SC.PHASES):
            ROOM["round"] += 1
            ph = SC.PHASES[ROOM["round"] - 1]
            ROOM["table"].append({"kind": "system", "text": f'{ph["name"]} — {ph["gm"]}'})
            bump()
        return {"round": ROOM["round"]}


@app.post("/api/human-vote")
def human_vote(b: HumanVote):
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["clientId"] != b.clientId:
            return JSONResponse({"error": "그 배역의 표가 아닙니다"}, status_code=403)
        ROOM["votes"][b.roleId] = b.suspectId
        ROOM["voteReasons"].pop(b.roleId, None)
        bump()
    return {"ok": True}


@app.post("/api/ai-vote")
def ai_vote(b: RoleOnly):
    with LOCK:
        r = ROOM["roles"].get(b.roleId)
        if not r or r["mode"] != "ai":
            return JSONResponse({"error": "AI 배역이 아닙니다"}, status_code=409)
        snapshot = list(ROOM["table"])
    c = SC.get_character(b.roleId)
    try:
        raw = llm(SC.build_vote_prompt(c),
                  f"지금까지 오간 대화다.\n\n{_table_text(snapshot)}\n\n이제 투표하라. JSON만.", 200)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)
    sid, reason = _parse_vote(raw, c)
    with LOCK:
        ROOM["votes"][b.roleId] = sid
        ROOM["voteReasons"][b.roleId] = reason
        bump()
    t = SC.get_character(sid)
    return {"suspectId": sid, "suspectName": t["name"] if t else sid, "reason": reason}


def _parse_vote(raw: str, voter: dict) -> tuple[str, str]:
    valid = [o["id"] for o in SC.CHARACTERS if o["id"] != voter["id"]]
    sid, reason = "", ""
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        obj = json.loads(m.group(0)) if m else {}
        sid = str(obj.get("suspect", "")).strip()
        reason = str(obj.get("reason", "")).strip()
    except Exception:  # noqa: BLE001
        pass
    if sid not in valid:
        for o in SC.CHARACTERS:
            if o["id"] in valid and (o["name"] in raw or o["id"] in raw):
                sid = o["id"]
                break
    if sid not in valid:
        sid = random.choice(valid)
    return sid, reason or "왠지 그런 느낌이 들어."


@app.post("/api/reveal")
def reveal():
    with LOCK:
        ROOM["revealed"] = True
        bump()
    return {"ok": True}


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
    print("  PIMMmurderboard · 그해 여름, 동창회")
    print(f"  AI 백엔드: {label}" + ("" if ok else "  ⚠ (미준비 — .env 확인)"))
    print("  브라우저에서 열기:")
    print(f"    이 컴퓨터   →  http://127.0.0.1:{PORT}")
    print(f"    같은 와이파이 →  http://{ip}:{PORT}   (폰·다른 PC는 이 주소로)")
    print("  각자 접속해 배역을 고르세요. 빈 자리는 'AI로 채우기'.")
    print("=" * 56)
    uvicorn.run(app, host=HOST, port=PORT)
