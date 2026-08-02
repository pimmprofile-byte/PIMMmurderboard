# -*- coding: utf-8 -*-
"""
회전목마 CAROUSEL — 판을 두 번 도는 머더미스터리 · **메모만 있는 상태(준비중)**

폐장한 놀이공원에서 직원 하나가 죽는다. 이 공원에는 괴담과 미신이 잔뜩 도는데,
개중 몇 가지는 진짜다. 속는 셈 치고 돌린 회전목마가 정말로 그 하루를 되돌린다.

2회차에는 전원이 1회차의 기억을 갖고 같은 하루를 다시 산다. 다만 회전목마는
한 바퀴에 한 사람의 기억을 먹는다. 사건이 아예 안 일어날 수도, 범인이 바뀔 수도 있다.

설계 정본: docs/회전목마_설계.md

⚠ 아직 플레이할 수 없다. 이 사건은 엔진 부담이 제일 크다 —
   회차 개념(페이즈 되감기와 상태 스냅샷), 되감기지 않는 개인 열람 기록,
   미신 카드의 참/거짓, 2회차 행동 선택, 그리고 가변 진범.
   필요한 변경은 설계 문서 9절에 있다.
   META["locked"]가 True인 동안 사건 선택창에서 회색으로 뜨고 고를 수 없다.
"""

ID = "carousel"
TITLE = "회전목마"
SUBTITLE = "CAROUSEL · 한 바퀴 돌면 제자리"
META = {
    "title": TITLE, "subtitle": SUBTITLE,
    # 「시간이 돌아간다」는 1막 끝에 겪는 것이다. 선택창에서 미리 말하지 않는다.
    "blurb": "폐장한 놀이공원에서 직원 하나가 죽었다. "
             "이 공원에는 괴담이 많고, 그중 몇 가지는 진짜다.",
    "players": "5인",
    "tone": "괴담 · 형광색",
    "difficulty": "★★★★",
    "tagline": "한 바퀴 돌면 제자리",
    "locked": True,          # 준비중 — 사건 선택창에서 고를 수 없다
}

DIFFICULTY = "상"
HAND_LIMIT = 2
AP_BY_ROUND = {1: 3, 2: 2, 3: 2}

MAP = [
    {"loc": "A", "name": "회전목마", "icon": ""},
    {"loc": "B", "name": "관람차", "icon": ""},
    {"loc": "C", "name": "유령의 집", "icon": ""},
    {"loc": "D", "name": "기계실", "icon": ""},
    {"loc": "E", "name": "정문·관제실", "icon": ""},
    {"loc": "F", "name": "매점 뒤", "icon": ""},
]

# 미신 덱 — 참/거짓이 섞여 있다. 참인 것은 실제로 효과가 있고,
# 거짓인 것은 믿고 행동한 만큼 알리바이에 구멍을 낸다.
# 아래는 결을 잡아두기 위한 예시이고, 장수와 비율은 미정이다(참 4 : 거짓 7쯤).
SUPERSTITIONS = [
    {"id": "S1", "true": True,
     "say": "폐장 뒤 회전목마를 거꾸로 한 바퀴 돌리면 그 하루가 되돌아온다.",
     "why": "…아무도 이유를 모른다. 이 하나만은 정말로 설명이 안 된다."},
    {"id": "S2", "true": True,
     "say": "관람차 12번 칸은 밤에 혼자 움직인다.",
     "why": "브레이크 라이닝이 닳았다. 참이지만 초자연이 아니다."},
    {"id": "S3", "true": False,
     "say": "유령의 집 세 번째 거울에 비친 사람이 다음 차례다.",
     "why": "그냥 거울이다. 다만 이걸 믿은 사람은 그 앞에서 오래 서 있었다."},
    {"id": "S4", "true": False,
     "say": "매점 뒷문으로 나가면 아무한테도 안 보인다.",
     "why": "재작년에 카메라가 붙었다. 믿고 나간 사람이 그대로 찍혔다."},
]

COMMON_INTRO = (
    "간판 불이 반쯤 나간 채로 스피커에서는 아직 캐럴이 흐른다. 오늘 폐장이다.\n"
    "직원은 다섯이었고, 문을 잠그고 나오니 넷이었다.\n\n"
    "이 공원에는 괴담이 많다. 다들 웃어넘기는 이야기들이다.\n"
    "…대부분은."
)

VICTIM = (
    "죽은 사람 · 미정\n"
    "미정."
)

SCENE_NOTE = "미정."

VICTIM_CARD = {
    "name": "미정", "age": "", "job": "",
    "tagline": "문을 잠그고 나오니 하나가 없었다.",
    "facts": ["미정"],
}

ALIBI_NOTE = "각자가 스스로 말한 것을 그대로 옮겼다."
ALIBI_LOG = []

# 페이즈 골격 — 1회차가 끝나면 «역행»이 오고, 같은 하루를 다시 산다.
# key "rewind" 와 "act" 는 아직 엔진에 없다. 설계 문서 9절 참고.
PHASES = [
    {"seq": 1, "key": "open", "name": "오프닝", "min": 6, "ap": 0,
     "gm": "폐장 직후입니다. 각자 마지막으로 그를 본 때를 말하게 하세요."},
    {"seq": 2, "key": "invest", "name": "1차 조사", "min": 12, "ap": 3,
     "gm": "공원을 뒤집니다. 미신 카드가 섞여 나오는데, 참인지 거짓인지는 아직 안 나옵니다."},
    {"seq": 3, "key": "talk", "name": "1차 토론", "min": 10, "ap": 0,
     "gm": "누가 어느 미신을 믿고 움직였는지가 알리바이를 가릅니다."},
    {"seq": 4, "key": "invest", "name": "2차 조사", "min": 12, "ap": 2,
     "gm": "미신의 참/거짓이 밝혀지기 시작합니다. 밝힌 사람에게 점수가 붙습니다."},
    {"seq": 5, "key": "talk", "name": "1회차 지목", "min": 12, "ap": 0,
     "gm": "여기서 한 번 지목합니다. 이게 최종이 아니라는 걸 아직 말하지 마세요."},
    {"seq": 6, "key": "rewind", "name": "역행", "min": 6, "ap": 0,
     "gm": "속는 셈 치고 회전목마를 거꾸로 돌립니다. 정말로 돌아갑니다. "
           "한 바퀴에 한 사람의 기억을 먹습니다 — 누구를 내놓을지 표결하세요."},
    {"seq": 7, "key": "act", "name": "2회차 · 행동", "min": 14, "ap": 2,
     "gm": "같은 하루입니다. 각자 어디서 무엇을 할지 «동시에» 제출합니다. "
           "1회차에 밝힌 미신은 값 없이 씁니다."},
    {"seq": 8, "key": "talk", "name": "2회차 토론", "min": 12, "ap": 0,
     "gm": "이번 하루에 무슨 일이 났는지를 맞춰봅니다. 아무도 안 죽었을 수도 있습니다."},
    {"seq": 9, "key": "final", "name": "마지막 표결", "min": 10, "ap": 0,
     "gm": "「사람은 살았는데 아무것도 안 밝혀진 세계」와 「사람은 죽었는데 다 밝혀진 세계」 중에 고릅니다."},
    {"seq": 10, "key": "reveal", "name": "진상 공개", "min": 10, "ap": 0,
     "gm": "두 바퀴를 겹쳐 봅니다."},
]

INTERLUDES = {}

CULPRIT_ID = ""      # 가변이다 — 2회차 행동의 조합으로 정해진다. 상수로 둘 수 없다
HIDDEN_ID = ""

CHARACTERS = []      # 미정 — 정비 · 탈인형 · 매표(관제) · 신입 · 점장
CARDS = []           # 미정 — 조사카드 + 미신 카드
CARD_PAIRS = []
KEEP_GOALS = {}
INVEST_AI = {}
CARD_POINTS_AT = {}
MEMORY = {}
FINAL_QUESTIONS = [
    "1회차에 죽은 사람은 누구이고, 2회차에 죽은 사람은 누구인가?",
    "당신이 참이라고 믿은 미신 중에 거짓이었던 것은 무엇인가?",
    "기억을 먹힌 사람은 누구였고, 그 선택은 옳았는가?",
    "이 하루를 한 번 더 돌릴 수 있다면 돌리겠는가?",
]
ENDINGS = {}
OPENING_CUTS = [
    {"img": "calm", "fx": "hush",
     "lines": ["간판 불이 반쯤 나갔다.", "스피커에서는 아직 캐럴이 흐른다."]},
    {"img": "scene", "fx": "static",
     "lines": ["직원은 다섯이었고,", "문을 잠그고 나오니 넷이었다."]},
    {"img": "body", "fx": "thud",
     "lines": ["이 공원에는 괴담이 많다.", "…대부분은 웃어넘길 만한 것들이다."]},
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
        "alibiLog": ALIBI_LOG, "alibiNote": ALIBI_NOTE, "map": MAP, "victimCard": VICTIM_CARD, "sceneNote": SCENE_NOTE, "mapLabel": "공원",
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
