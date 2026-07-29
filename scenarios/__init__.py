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


def meta_list():
    return [{"id": _MODS[i].ID, **_MODS[i].META} for i in _ORDER]
