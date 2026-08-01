"""시나리오 레지스트리 — 여러 시나리오를 id로 등록/조회한다.

각 시나리오 모듈은 동일한 인터페이스(ID/META/TITLE/CHARACTERS/CARDS/…,
public_scenario()/compute_ending()/build_*_prompt()/… )를 노출한다.
"""
from . import graduation, subway, abyss_garden

_MODS = {graduation.ID: graduation, subway.ID: subway, abyss_garden.ID: abyss_garden}
# 기본 시나리오는 졸업사진 유지(프로토타입 기준). 허브(landing.html)가 노출 순서를 따로 정한다.
_ORDER = [graduation.ID, subway.ID, abyss_garden.ID]


def get(sid):
    return _MODS.get(sid) or _MODS[_ORDER[0]]


def ids():
    return list(_ORDER)


def default_id():
    return _ORDER[0]


# 사건 하나가 「읽을거리」로서 얼마나 무거운가. 난이도(추리의 어려움)와는 다른 축이라,
# 고르는 사람이 미리 알아야 할 정보다 — 20분짜리인 줄 알고 앉았다가 한 시간을 읽게 되면
# 그건 재미가 아니라 사고다. 원고를 고칠 때마다 저절로 따라오게 계산해서 낸다.
def _text_load(m) -> dict:
    """플레이어 한 명이 실제로 읽게 되는 글자 수. 남의 롤카드는 안 읽으므로 1인분만 센다."""
    role = 0
    for c in getattr(m, "CHARACTERS", []):
        for k in ("hook", "storyPast", "storyToday", "tagline", "persona"):
            role += len(str(c.get(k) or ""))
        for sec in (c.get("sheet") or []):
            role += len(str(sec.get("h", ""))) + len(str(sec.get("b", "")))
        for x in (c.get("hide") or []) + (c.get("tips") or []):
            role += len(str(x))
        for r in (c.get("past") or []):
            role += len(str(r.get("w", ""))) + len(str(r.get("t", "")))
        for g in (c.get("goals") or []):
            role += len(str(g.get("t", "")))
    n = max(1, len(getattr(m, "CHARACTERS", []) or [1]))
    cards = sum(len(c.get("text", "")) + len(c.get("hint", "")) for c in getattr(m, "CARDS", []))
    common = len(str(getattr(m, "COMMON_INTRO", "") or "")) + len(str(getattr(m, "VICTIM", "") or ""))
    common += sum(len(str(x)) for x in (getattr(m, "ALIBI_LOG", []) or []))
    total = role // n + cards + common
    # 분당 500자 — 처음 보는 글을 곱씹으며 읽는 속도다(술술 읽는 속도의 절반쯤).
    mins = max(1, round(total / 500))
    if total < 5000:
        tier, label = 1, "가볍게"
    elif total < 9000:
        tier, label = 2, "보통"
    elif total < 15000:
        tier, label = 3, "읽을거리 많음"
    else:
        tier, label = 4, "장편"
    return {"chars": total, "minutes": mins, "tier": tier, "label": label,
            "bar": "▮" * tier + "▯" * (4 - tier)}


def meta_list():
    return [{"id": _MODS[i].ID, **_MODS[i].META, "text": _text_load(_MODS[i])} for i in _ORDER]
