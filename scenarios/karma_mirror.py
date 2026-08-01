# -*- coding: utf-8 -*-
"""
업경 業鏡 — 2~3인 평행세계 머더미스터리 · **틀만 잡힌 상태(준비중)**

셋 중 하나가 죽었고 남은 둘이 범인을 쫓는다. 그런데 둘이 쫓는 사건이 같은 사건이 아니다 —
각자 다른 평행세계에 있고, 세계마다 죽은 사람이 다르다.

설계 정본: docs/업경_설계.md

⚠️ 이 시나리오는 아직 플레이할 수 없다. 지금 서버는 CARDS 하나를 모두가 공유하는 구조라
   「사람마다 다른 카드를 본다」가 성립하지 않는다. 필요한 엔진 변경은 설계 문서 7절에 있다.
   META["locked"]가 True인 동안 사건 선택창에서 회색으로 뜨고 고를 수 없다.
"""

ID = "karma_mirror"
TITLE = "업경"
SUBTITLE = "業鏡 · 거울은 자기 것만 비춘다"
META = {
    "title": TITLE, "subtitle": SUBTITLE,
    # 기믹을 여기서 말하면 안 된다. 선택창을 보는 사람은 아직 아무것도 몰라야 한다 —
    # 「말이 자꾸 어긋난다」까지가 1막에서 실제로 겪는 것이고, 그 너머는 게임이 알려준다.
    "blurb": "셋이 한집에 있었고 밤사이 하나가 죽었다. "
             "남은 사람들이 서로의 말을 맞춰보는데, 자꾸 어긋난다.",
    "players": "2~3인",
    "tone": "불안 · 진술 대조",
    "difficulty": "★★★★",
    "tagline": "거울은 자기 것만 비춘다",
    "locked": True,          # 준비중 — 사건 선택창에서 고를 수 없다
}

DIFFICULTY = "상"
HAND_LIMIT = 2
AP_BY_ROUND = {1: 3, 2: 2, 3: 2}

PA_LABEL = "거울 너머"
FRAGMENT_LABEL = "비친 것"
FRAGMENT_EYEBROW = "업경에 비친 조각"
FRAGMENT_NOTICE = "🪞 거울에 하나 더 비쳤다 — 아래 ‘내 정보’를 확인하세요."

# ── 세 세계 ──────────────────────────────────────────────────────
# 같은 셋이 세 세계에 존재하고, 세계마다 죽은 사람이 다르다.
# 플레이어는 각자 자기 세계의 생존자다.
WORLDS = [
    {"id": "A", "name": "첫 번째 거울", "victim": "gap", "alive": ["eul", "byeong"]},
    {"id": "B", "name": "두 번째 거울", "victim": "eul", "alive": ["gap", "byeong"]},
    {"id": "C", "name": "세 번째 거울", "victim": "byeong", "alive": ["gap", "eul"]},
]

MAP = [
    {"loc": "A", "name": "안방", "icon": "🛏️"},
    {"loc": "B", "name": "마루", "icon": "🪑"},
    {"loc": "C", "name": "부엌", "icon": "🍚"},
    {"loc": "D", "name": "마당", "icon": "🌳"},
    {"loc": "E", "name": "골방", "icon": "🚪"},
]

# 두루뭉실하게 쓴다. 이름도 나이도 확정하지 않는다 —
# 세계마다 조금씩 다른데, 그 어긋남이 이 게임의 전부다.
COMMON_INTRO = (
    "셋이 한집에 있었다.\n"
    "밤사이 하나가 죽었고, 아침에 남은 사람들이 그를 발견했다.\n\n"
    "집 밖으로 나가는 길은 하나뿐이고, 그 길에는 밤새 아무 발자국도 나지 않았다.\n"
    "그러니 이 안에 있는 사람 중 하나가 한 일이다.\n\n"
    "…그렇게 시작하는 이야기다. 셋 다 그렇게 시작한다."
)

VICTIM = (
    "죽은 사람 · 나이는 정확히 아무도 말하지 못한다\n"
    "안방에 누운 채로 발견됐다. 겉으로 보이는 상처는 없다.\n"
    "얼굴을 떠올리려고 하면 자꾸 다른 얼굴이 겹친다."
)

ALIBI_NOTE = "각자가 자기 자리에서 본 것을 옮겼다. 겹쳐 읽으면 맞지 않는 데가 있다."
ALIBI_LOG = []

TIMELINE = []
TRUTH_FULL = (
    "(미정 — 설계 문서 5절의 세 후보 중 확정 전이다.)\n\n"
    "기본안: 각 세계에서 죽지 않은 사람 중 하나가 범인이고, 세 세계를 겹쳐보면 "
    "셋 다 어느 세계에서는 사람을 죽였다. 업경은 각자에게 자기 죄만 비춘다."
)
REDHERRINGS = []

PHASES = [
    {"seq": 1, "key": "open", "name": "오프닝", "min": 6, "ap": 0,
     "gm": "각자 자기가 본 것을 말하게 하세요. 아직 아무도 어긋남을 눈치채지 못한 상태입니다."},
    {"seq": 2, "key": "invest", "name": "조사 R1", "min": 12, "ap": 3,
     "gm": "집 안을 뒤집니다. 같은 자리를 뒤져도 사람마다 다른 것이 나옵니다."},
    {"seq": 3, "key": "talk", "name": "토론 1", "min": 10, "ap": 0,
     "gm": "말이 안 맞기 시작합니다. 여기서는 아직 서로 거짓말을 한다고 믿게 두세요."},
    {"seq": 4, "key": "invest", "name": "조사 R2", "min": 12, "ap": 2,
     "gm": "어긋남이 우연으로는 설명이 안 되는 지점까지 갑니다."},
    {"seq": 5, "key": "talk", "name": "토론 2", "min": 10, "ap": 0,
     "gm": "여기가 1막의 끝입니다. 아무도 거짓말하지 않았다는 것을 받아들이게 하세요."},
    {"seq": 6, "key": "invest", "name": "조사 R3", "min": 10, "ap": 2,
     "gm": "이제 남의 세계를 듣기 시작합니다. 내 답은 저쪽에 있습니다."},
    {"seq": 7, "key": "talk", "name": "최종 토론", "min": 12, "ap": 0,
     "gm": "각자 자기 세계의 범인을 정합니다. 정답이 사람마다 다릅니다."},
    {"seq": 8, "key": "reveal", "name": "진상 공개", "min": 10, "ap": 0,
     "gm": "세 거울을 겹쳐 봅니다."},
]

INTERLUDES = {}

CULPRIT_ID = ""      # 세계마다 다르다 — 엔진이 배역별 판정을 지원한 뒤에 채운다
HIDDEN_ID = ""

CHARACTERS = []      # 미정 (설계 문서 9절)
CARDS = []           # 미정 — 세계당 10~12장, 같은 번호가 사람마다 다른 것을 보여준다
CARD_PAIRS = []
KEEP_GOALS = {}
INVEST_AI = {}
CARD_POINTS_AT = {}
MEMORY = {}
FINAL_QUESTIONS = [
    "당신의 세계에서 죽은 사람은 누구이고, 죽인 사람은 누구인가?",
    "다른 사람의 말 중에 당신의 세계와 맞지 않았던 것은 무엇인가?",
    "그 어긋남을 언제 눈치챘는가?",
]
ENDINGS = {}
OPENING_CUTS = [
    {"img": "calm", "fx": "hush",
     "lines": ["셋이 한집에 있었다.", "밤사이 하나가 죽었다."]},
    {"img": "body", "fx": "thud",
     "lines": ["남은 사람들이 아침에 그를 발견했다.",
               "겉으로 보이는 상처는 없었다."]},
    {"img": "scene", "fx": "static",
     "lines": ["밖으로 나가는 길은 하나뿐이고, 밤새 아무 발자국도 나지 않았다.",
               "그러니 이 안에 있는 사람 중 하나가 한 일이다."]},
    {"img": "scene", "fx": "",
     "lines": ["…그렇게 시작하는 이야기다.", "셋 다, 그렇게 시작한다."]},
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
            "spot": c.get("spot", ""), "hint": c.get("hint", ""), "unlocks": c.get("unlocks", "")}


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
        "alibiLog": ALIBI_LOG, "alibiNote": ALIBI_NOTE, "map": MAP,
        "phases": [{"seq": p["seq"], "key": p["key"], "name": p["name"], "min": p["min"],
                    "ap": p["ap"], "gm": p["gm"]} for p in PHASES],
        "characters": [],
        "pairKeys": [], "cardCatalog": [],
        "openingCuts": OPENING_CUTS,
        "finalQuestions": FINAL_QUESTIONS,
        "interludes": {},
        "paLabel": PA_LABEL,
        "fragLabel": FRAGMENT_LABEL, "fragEyebrow": FRAGMENT_EYEBROW, "fragNotice": FRAGMENT_NOTICE,
    }


def build_play_prompt(c, seq, revealed_ids, table, nudge="", hand_ids=None, crisis_solved=None) -> str:
    return f"《{TITLE}》는 아직 준비 중인 사건입니다."


def build_final_answer_prompt(c, revealed_ids, table) -> str:
    return "{}"


def build_grade_prompt(c, answers) -> str:
    return "{}"


def compute_ending(grades: dict):
    return None
