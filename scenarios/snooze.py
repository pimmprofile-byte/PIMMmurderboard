# -*- coding: utf-8 -*-
"""
스누즈 SNOOZE — 죽음이 한 번 미뤄지는 머더미스터리 · **메모만 있는 상태(준비중)**

1막에서 시신을 조사한다. 2막이 열리면 그가 눈을 뜬다 — 기절이었다.
조사가 «질문»으로 바뀌고, 그의 답을 놓고 다툰다. 그리고 3막이 열릴 때 그는 진짜로 죽어 있다.

지목이 둘이다 — 「누가 기절시켰나」와 「누가 죽였나」. 둘이 같을 필요가 없다.

설계 정본: docs/스누즈_설계.md

⚠ 아직 플레이할 수 없다. 필요한 엔진 변경은 설계 문서 9절에 있다 —
   질문형 조사 페이즈, 피해자 배역의 두 벌 시트, 「의식이 없는 동안」 화면,
   2차 토론의 자기선언 알리바이, 그리고 이중 지목.
   META["locked"]가 True인 동안 사건 선택창에서 회색으로 뜨고 고를 수 없다.
"""

ID = "snooze"
TITLE = "스누즈"
SUBTITLE = "SNOOZE · 한 번 미뤄진 죽음"
META = {
    "title": TITLE, "subtitle": SUBTITLE,
    # 「깨어난다」를 여기 적으면 안 된다. 그게 이 사건의 2막 전부다.
    "blurb": "하나가 죽은 채로 발견됐고, 남은 사람들이 밤새 서로를 캔다. "
             "아침이 오기 전에 한 번 더 무슨 일이 일어난다.",
    "players": "5인",
    "tone": "안도 · 그리고 뒤집힘",
    "difficulty": "★★★",
    "tagline": "알람은 꺼진 게 아니다",
    "locked": True,          # 준비중 — 사건 선택창에서 고를 수 없다
}

DIFFICULTY = "중상"
HAND_LIMIT = 2
AP_BY_ROUND = {1: 3, 2: 2, 3: 2}

MAP = [
    {"loc": "A", "name": "미정", "icon": ""},
]

COMMON_INTRO = (
    "하나가 죽은 채로 발견됐다.\n"
    "밖으로 나갈 길이 없는 밤이고, 여기 있는 사람은 넷뿐이다.\n\n"
    "…그래서 넷은 밤새 서로를 캔다.\n"
    "아침이 오기 전에 한 번 더 무슨 일이 일어난다는 것을, 지금은 아무도 모른다."
)

VICTIM = (
    "죽은 사람 · 미정\n"
    "숨이 없다고들 했다. 맥을 짚어본 사람은 아무도 없었다."
)

SCENE_NOTE = "미정."

VICTIM_CARD = {
    "name": "미정", "age": "", "job": "",
    "tagline": "숨이 없다고들 했다.",
    "facts": ["미정"],
}

ALIBI_NOTE = "각자가 스스로 말한 것을 그대로 옮겼다."
ALIBI_LOG = []

# 페이즈 골격 — 2차 조사가 «질문»이고, 3차 조사 앞에 두 번째 죽음이 온다.
# key "ask" 는 아직 엔진에 없다. 설계 문서 9절 참고.
PHASES = [
    {"seq": 1, "key": "open", "name": "오프닝", "min": 6, "ap": 0,
     "gm": "어젯밤 각자 무엇을 하고 있었는지 말하게 하세요."},
    {"seq": 2, "key": "invest", "name": "1차 조사", "min": 12, "ap": 3,
     "gm": "여느 사건과 똑같이 진행하세요. 여기서 이상한 낌새를 주면 안 됩니다."},
    {"seq": 3, "key": "talk", "name": "1차 토론", "min": 10, "ap": 0,
     "gm": "범인 후보를 좁히게 두세요. 좁혀질수록 좋습니다 — 다음 막에서 다 무너집니다."},
    {"seq": 4, "key": "ask", "name": "2차 조사 · 질문", "min": 12, "ap": 2,
     "gm": "그가 숨을 쉽니다. 물을 떠다 주고, 앉히고, 그리고 묻기 시작하세요. "
           "조사턴은 질문권입니다. 답은 전부 공개됩니다."},
    {"seq": 5, "key": "talk", "name": "2차 토론", "min": 12, "ap": 0,
     "gm": "그의 말이 어디까지 참인지를 다투게 하세요. "
           "끝날 때 전원에게 «이 뒤 한 시간을 어디서 누구와 보낼지»를 선언시키고 그대로 적어두세요."},
    {"seq": 6, "key": "invest", "name": "3차 조사", "min": 12, "ap": 2,
     "gm": "그가 죽어 있습니다. 이번엔 확실히. 알리바이는 방금 자기들이 말한 그것입니다."},
    {"seq": 7, "key": "talk", "name": "마지막 토론", "min": 12, "ap": 0,
     "gm": "두 사건입니다. 같은 손인지 다른 손인지를 정해야 합니다."},
    {"seq": 8, "key": "final", "name": "최후의 선택", "min": 10, "ap": 0,
     "gm": "지목이 둘입니다 — 기절시킨 사람, 그리고 죽인 사람."},
    {"seq": 9, "key": "reveal", "name": "진상 공개", "min": 10, "ap": 0,
     "gm": "두 밤의 시각표를 나란히 봅니다."},
]

INTERLUDES = {}

CULPRIT_ID = ""      # 두 번째 살인의 범인 — 진범 구조를 정한 뒤에 채운다(설계 문서 7절)
HIDDEN_ID = ""       # 첫 번째 기절의 손 — 위와 같지 않을 수 있다

CHARACTERS = []      # 미정 — 넷 + 피해자 1
CARDS = []           # 미정
CARD_PAIRS = []
KEEP_GOALS = {}
INVEST_AI = {}
CARD_POINTS_AT = {}
MEMORY = {}
FINAL_QUESTIONS = [
    "그를 기절시킨 사람은 누구인가?",
    "그를 죽인 사람은 누구인가? 위와 같은 사람인가?",
    "그가 깨어나서 한 말 중 거짓이었던 것은 무엇인가?",
    "당신은 그 한 시간을 정말 선언한 대로 보냈는가?",
]
ENDINGS = {}
OPENING_CUTS = [
    {"img": "calm", "fx": "hush",
     "lines": ["숨이 없다고들 했다.", "맥을 짚어본 사람은 아무도 없었다."]},
    {"img": "body", "fx": "thud",
     "lines": ["밖으로 나갈 길이 없는 밤이었다.", "여기 있는 사람은 넷뿐이다."]},
    {"img": "scene", "fx": "",
     "lines": ["그래서 넷은 밤새 서로를 캔다.", "아침은 아직 멀었다."]},
]


# ── 최소 인터페이스 ──────────────────────────────────────────────
# 아직 데이터가 비어 있어도 레지스트리와 서버가 모듈을 훑을 때 터지지 않아야 한다.
def get_character(cid):
    return next((c for c in CHARACTERS if c["id"] == cid), None)


def get_card(cid):
    return next((c for c in CARDS if c["id"] == cid), None)


def obligatory_cards_upto_round(rnd: int) -> list:
    return [c["id"] for c in CARDS if c.get("reveal") == "obligatory" and c["round"] <= rnd]


def public_card(cid: str):
    c = get_card(cid)
    if not c:
        return None
    return {"id": c["id"], "loc": c["loc"], "locName": c["locName"], "round": c["round"],
            "title": c["title"], "text": c["text"], "bait": c.get("bait", False),
            "spot": c.get("spot", ""), "unlocks": c.get("unlocks", "")}


def private_notes(role_id: str, card_id: str) -> list:
    return []


def phase_by_seq(seq: int) -> dict:
    for p in PHASES:
        if p["seq"] == seq:
            return p
    return PHASES[-1]


def interlude_for(seq: int):
    return INTERLUDES.get(seq)


def memory_up_to(cid: str, current_seq: int, crisis_solved=None) -> list:
    return [m for m in MEMORY.get(cid, []) if m["seq"] <= current_seq]


def private_sheet(cid: str):
    c = get_character(cid)
    if not c:
        return None
    return {"id": c["id"], "name": c["name"], "job": c.get("job", ""), "avatar": c.get("avatar", ""),
            "color": c.get("color", "#888"), "hidden": c.get("hidden", False),
            "persona": c.get("persona", ""), "goals": c.get("goals", []), "map": MAP}


def public_scenario() -> dict:
    return {
        "title": TITLE, "subtitle": SUBTITLE, "intro": COMMON_INTRO, "victim": VICTIM,
        "alibiLog": ALIBI_LOG, "alibiNote": ALIBI_NOTE, "map": MAP, "victimCard": VICTIM_CARD, "sceneNote": SCENE_NOTE, "mapLabel": "숙소",
        "phases": [{"seq": p["seq"], "key": p["key"], "name": p["name"], "min": p["min"],
                    "ap": p["ap"], "gm": p["gm"]} for p in PHASES],
        "characters": [],
        "pairKeys": [], "cardCatalog": [],
        "openingCuts": OPENING_CUTS,
        "finalQuestions": FINAL_QUESTIONS,
        "interludes": {},
                    }


def build_play_prompt(c, seq, revealed_ids, table, nudge="", hand_ids=None, crisis_solved=None) -> str:
    return f"《{TITLE}》는 아직 준비 중인 사건입니다."


def build_final_answer_prompt(c, revealed_ids, table) -> str:
    return "{}"


def build_grade_prompt(c, answers) -> str:
    return "{}"


def compute_ending(grades: dict):
    return None
