"""
졸업사진(卒業寫眞) — 배역 기반 머더미스터리 (AI가 빈 좌석 대신 플레이 · 완전 데모 · 이미지 없음)

핸드오프 v1.0 + v1.1 보충분 반영. 승리 구조는 '범인 찾기'가 아니라 '자기 죄를 숨기면서도 드러내기'.
오승택을 죽인 사람은 없다 — 모두가 자기 자신을 지목(자기 죄 인정)하면 진혼 엔딩.
점수는 종막 '질문지(서술형 답변)'를 AI가 채점한다.

■ 비밀(sheet/truth/sins)·정답·채점 루브릭은 서버 전용. 브라우저엔 공개 정보만.
■ 시나리오 교체는 이 파일만 갈아끼우면 된다.
"""
from __future__ import annotations

TITLE = "졸업사진"
SUBTITLE = "卒業寫眞 · 10년 만의 동창회"

# 공통지문 최종본 (v1.1)
COMMON_INTRO = (
    "교문은 잠겨 있지 않았다.\n"
    "「10년 만의 동창회. 졸업식 날 밤, 3학년 2반에서.」 — 쪽지 한 장에, 우리는 같은 밤 같은 폐교로 모였다.\n"
    "이상하다. 분명 동창인데 — 서로의 얼굴도, 그 시절도, 안개처럼 흐릿하다.\n"
    "복도의 공기는 10년 전 겨울에 멈춘 채 차갑고, 스피커가 이따금 잡음을 삼킨다.\n"
    "3학년 2반의 문을 연다.\n"
    "달빛이 내려앉은 교실 한가운데 — 교복을 입은 누군가가 쓰러져 있다. 놀랍도록 생생한 시체.\n"
    "명찰을 확인한 순간, 등골이 서늘해진다. 우리 동창, 오승택.\n"
    "그리고 시체 곁에 놓인 세 개의 물건. 누군가는, 그게 자기 것임을 알아본다.\n"
    "이 방 안의 누군가가 오승택을 죽였다. — 오늘 밤, 우리는 그게 누구인지 알아내야 한다."
)

VICTIM = "오승택 (교복 차림) · 3학년 2반에서 발견 · 놀랍도록 생생한 시체 · 오른손에 무언가를 꽉 쥐고 있다."

# 진상 전문 — 서버 전용
TRUTH_FULL = (
    "오승택을 물리적으로 죽인 사람은 없다. 그러나 세 사람 모두가 그를 죽였다. 정답 지목은 '나 자신'.\n"
    "10년 전: 오승택은 반에서 겉돌던 학생. 심상윤의 무자각한 부림, 이정민의 연민을 가장한 멸시, "
    "유지호의 보이지 않는 방해가 각각 그를 짓눌렀다(셋은 서로의 가해를 모른다).\n"
    "종업식 때 오승택이 방송으로 '전부 돌려주겠다'고 예고. 겨울방학에 복수를 실행했다.\n"
    " · 심상윤 — '연인 J를 해코지하겠다'는 협박으로, 시키는 대로 하는 괴로움을 되돌려주어 스스로 옥상 난간을 넘게 만듦.\n"
    " · 유지호 — 그가 몰래 훼손했던 것의 반사로, 가장 아끼던 첫 입상 도자기를 부수고 잔해를 주우러 도로로 뛰어들게 해 사고사.\n"
    " · 이정민 — 뒤에서 하던 말의 녹취를 유포해 '선인' 평판을 하룻밤에 붕괴시키고, 무너지는 자신을 보게 하여 절망에 이르게 함.\n"
    "이후 오승택은 졸업식에 스스로 생을 마감. 학교는 폐교. 세 사람도 그 겨울 죽었다.\n"
    "매 졸업식 밤, 세 망령은 기억을 잃은 채 폐교로 소환된다. 오승택의 망령(위장명 '오세원')이 설계한 반복 — "
    "목적은 복수의 연장이 아니라 그들이 스스로 죄를 깨닫는 것.\n"
    "시체는 10년 전 오승택 본인(고인 시간 속에서 부패하지 않음). 오세원=오승택."
)

# 타살 오인 미끼 (v1.1 E · 서버/GM 컨텍스트)
REDHERRINGS = [
    "생생한 시체 — 10년 폐교인데 방금 숨진 듯 보존(회수: 고인 시간, A5).",
    "현장의 물품 3점 — 각자 자기 것임을 알아봄(회수: 망령이 매년 놓는 기억의 방아쇠).",
    "유서 없음 + 시각 불일치(F2) — '자살 위장 타살?'(회수: 고여버린 시간, 유서 대신 방송).",
    "10년 전 현장에도 같은 물품 3점(F2 말미) — '누군가 그때 거기 있었다'(회수: 세 사람이 남긴 죄의 증표).",
    "오늘 밤 쓰인 방송실(E1) — '제5의 인물'(회수: 오세원=주최자, E4 필체).",
]

DIFFICULTY = {"deduction_rate": 0.6, "self_disclosure_from": 2, "osewon_probe_rate": 0.3}

# ── 라운드(80분, 9시퀀스) ──
PHASES = [
    {"seq": 1, "key": "open",   "name": "오프닝",        "min": 8,  "ap": 0, "gm": "공통지문을 낭독하고, 각자 배역으로 자기소개(공개 정보만)한다."},
    {"seq": 2, "key": "invest", "name": "조사 R1",       "min": 12, "ap": 3, "gm": "먼저, 이 시체가 누구인지부터. (각자 3장 조사)"},
    {"seq": 3, "key": "talk",   "name": "토론 1",        "min": 10, "ap": 0, "gm": "물품 3점의 주인은 이 안에 있다. 오늘 밤 무슨 일이 있었나?"},
    {"seq": 4, "key": "invest", "name": "조사 R2",       "min": 12, "ap": 3, "gm": "학교가 기억하는 것을 찾아라. (각자 3장 조사)"},
    {"seq": 5, "key": "talk",   "name": "토론 2",        "min": 10, "ap": 0, "gm": "오승택은 10년 전에 죽었다. 그렇다면 — 그 겨울, 당신들은 무엇을 했나?"},
    {"seq": 6, "key": "invest", "name": "조사 R3",       "min": 8,  "ap": 2, "gm": "마지막 문이 열렸다. (각자 2장 조사)"},
    {"seq": 7, "key": "talk",   "name": "최종 토론",     "min": 10, "ap": 0, "gm": "죽인 사람이 꼭 손을 쓴 사람인가?"},
    {"seq": 8, "key": "final",  "name": "종막 · 질문지",  "min": 5,  "ap": 0, "gm": "각자 마지막 질문에 답한다. 오승택을 죽인 것은 누구인가 — 당신은 누구를 지목하는가."},
    {"seq": 9, "key": "reveal", "name": "진상 공개",     "min": 5,  "ap": 0, "gm": "진상을 밝히고 엔딩을 확인한다."},
]
TALK_FRAGMENT_KEY = {3: "t1", 5: "t2", 7: "t3"}

# 망령 인터루드 (v1.1 D · 해당 시퀀스로 진입할 때 교내 방송으로 1회)
INTERLUDES = {
    4: "…재학생 여러분께 알립니다. 분실물은, 잃어버린 자리에 있습니다.",
    6: "…하교 시간이 지났습니다. 아직 교실에 남아 있는 학생은 — 자신이 왜 남아 있는지 생각해 보십시오.",
    7: "…졸업식을 시작하겠습니다. 호명된 학생은, 자기 이름에 대답하십시오.",
    8: "마지막 질문입니다. — 오승택을 죽인 사람은, 누구입니까.",
}

# ── 배역 4인 (v1.1 C 섹션식) ──
CHARACTERS = [
    {
        "id": "sim", "name": "심상윤", "age": "32", "job": "가게 운영(기억은 흐릿)", "avatar": "🚬", "color": "#e6a355",
        "tagline": "왕년의 분위기 메이커. 누구와도 금방 친해지는 호탕한 성격.",
        "persona": "시원시원, 반말 위주, 좌중을 이끌려 함. 부탁을 '부탁'인 줄 모르고 시키는 버릇이 말끝에 남아 있다('야, 그거 좀 가져와봐').",
        "hidden": False,
        "sheet": [
            {"h": "지금, 이 교실에서", "b": "달빛 아래 교복 입은 시체 하나. 그 옆에 낡은 지포 라이터 — 네 것이다. 왜 저기 있는지, 네가 어떻게 여기 왔는지 기억이 없다. 확실한 건 하나. 이 방의 누군가가, 저 애를 죽였다."},
            {"h": "너라는 사람", "b": "심상윤. 어디서든 사람들이 널 따랐고, 넌 그걸 우정이라 불렀다. 그런데 졸업식이 기억나지 않는다. 사진 한 장 없다. 그 겨울 이후가 젖은 종이처럼 찢겨 있다."},
            {"h": "오승택", "b": "소꿉친구다. 매점 빵, 과제, 가방 — 늘 걔가 '해주던' 거다. 넌 시킨 적 없다. …없나? 걔가 한 번도 싫다고 안 했을 뿐인 건 아닌가. 이 질문을 넌 여태 스스로에게 한 적이 없다."},
            {"h": "감춰야 할 것", "b": "저 라이터가 네 것이라는 사실. 초반엔 절대 인정하지 마라. 승택이 얘기가 나오면 웃음으로 덮고, 화살을 남의 물건 쪽으로 돌려라."},
            {"h": "알아내야 할 것", "b": "누가 오승택을 죽였나. — 그리고 그 아래 묻힌 질문: 그 겨울, 너는 대체 무슨 짓을 했나. 넌 아직 그날 밤을 기억하지 못한다. 기억이 돌아올 때, 도망치지 마라."},
        ],
        "sins": ["오승택을 꼬봉처럼 부려온 관계", "그것이 강요임을 자각조차 못 함", "옥상 — 자신의 죽음이 그 되갚음이었음"],
        "goals": [{"t": "라이터·주종관계를 초반엔 숨긴다", "p": 0}, {"t": "죄의 조각이 드러나게 한다", "p": 10}, {"t": "최종에 '자기 자신'을 지목(자백)", "p": 15}],
        "ai_note": "R1엔 수사를 주도하며 자기 라이터 화제는 회피하고 타인 물품을 적극 추궁(투사)한다. R2 옥상(C계열) 카드에 동요한다. 죄의 조각 2개가 공론화되면 자기지목 루트로 전환하되, 최종토론 전에는 명시적 자백을 하지 않는다.",
        "cards": ["A3", "B4", "C2", "C3", "C4"],
    },
    {
        "id": "yu", "name": "유지호", "age": "32", "job": "미대 출신(어렴풋)", "avatar": "🏺", "color": "#7fb4d6",
        "tagline": "조용한 완벽주의자. 관찰력이 좋고 말수가 적다.",
        "persona": "존댓말, 단문, 필요한 말만. 예술·손재주 화제에만 온도가 올라간다.",
        "hidden": False,
        "sheet": [
            {"h": "지금, 이 교실에서", "b": "교실 한가운데 교복 입은 시체. 그 옆에 목제 조각칼 — 잃어버린 줄 알았던 네 것이다. 어떻게 여기 왔는지, 왜 손이 떨리는지 모르겠다. 분명한 건, 이 방의 누군가가 저 애를 죽였다는 것."},
            {"h": "너라는 사람", "b": "유지호. 손으로 만드는 것만이 너를 증명했다. 재능은 늘 부족했고 그래서 더 절박했다. 그런데 대학엔 갔던가? 합격 발표를 본 장면이 없다. 그 겨울, 무언가를 감싸 안았던 감촉에서 기억이 끊긴다."},
            {"h": "오승택", "b": "말 한번 섞은 적 없다. 소문과, 걔의 그림으로만 알았다. 그 그림이 문제였다 — 저 재능이 내 유일한 자리를 가져간다. 아무도 없는 미술실, 시너 냄새, 5분. 넌 사람을 미워한 게 아니라 그림을 지웠을 뿐이라 되뇌었다. 그게 걔의 유일한 동아줄인 걸 알면서."},
            {"h": "감춰야 할 것", "b": "저 조각칼이 네 것이라는 것. 그리고 그 겨울 미술실에 네가 있었다는 것. 예술·손재주 얘기가 나오면 입을 닫아라 — 넌 티가 나는 사람이다."},
            {"h": "알아내야 할 것", "b": "누가 오승택을 죽였나. — 그 아래 묻힌 질문: 그 겨울, 네 손은 무엇을 했나. 넌 아직 그날을 기억하지 못한다. 떠오르거든, 외면하지 마라."},
        ],
        "sins": ["같은 진로의 숨은 경쟁자", "출품작을 몰래 훼손해 동아줄을 끊음", "가장 아끼던 것의 잔해를 좇다 죽음"],
        "goals": [{"t": "조각칼·훼손을 초반엔 숨긴다", "p": 0}, {"t": "죄의 조각이 드러나게 한다", "p": 10}, {"t": "최종에 '자기 자신'을 지목(자백)", "p": 15}],
        "ai_note": "R1엔 미술실(D계열) 조사를 은근히 선점하려 하고 D2 단추 화제를 덮으려 한다. R2 D3(실격 공문) 공개 시 '실격은 안타까운 일'이라며 3인칭화한다. D4 공개 시 무너져 자기지목 루트로.",
        "cards": ["A3", "D1", "D2", "D3", "D4"],
    },
    {
        "id": "lee", "name": "이정민", "age": "32", "job": "봉사활동 이야기를 먼저 꺼냄", "avatar": "🕊️", "color": "#8ec98a",
        "tagline": "반의 궂은일을 도맡던 '좋은 사람'. 다정하고 공감 능력이 좋아 보인다.",
        "persona": "부드러운 경어+반말 혼용, '괜찮아?', '내가 도와줄게'가 입버릇. 칭찬으로 시작해 은근히 위계를 만드는 화법.",
        "hidden": False,
        "sheet": [
            {"h": "지금, 이 교실에서", "b": "쓰러진 교복. 그 옆에 자수 손수건 — 네가 승택에게 줬던 그 손수건이다. 왜 여기 있나. 왜 네가 여기 있나. 기억이 없다. 다만 확실한 건 — 이 방의 누군가가 저 애를 죽였다."},
            {"h": "너라는 사람", "b": "이정민. 반의 궂은일을 도맡던 '좋은 사람'. 그렇게 불리다 보면 정말 그런 줄 안다. 그런데 졸업 후 누구와 연락한 기억도, '내 사람들' 얼굴도 하나 떠오르지 않는다. 복도에 흩날리던 종이들에서 기억이 끊긴다."},
            {"h": "오승택", "b": "승택의 유일한 친구는 너였다. 곁에 있어줬고 챙겨줬고 — 그런데 어느 날 걔가 물었다. '너 지금, 나 불쌍해서 좋지?' 넌 부정했지만, 그날 이후 걔를 피했다. 그리고 뒤에서는 말했다. 선의라는 가장 높은 자리에서, 넌 걔를 내려다봤다."},
            {"h": "감춰야 할 것", "b": "저 손수건이 네 것이라는 것. 네가 뒤에서 했던 말들. 넌 이 밤에도 중재자 자리를 먼저 차지할 것이다 — 그 자리에 있는 동안은 아무도 널 심문하지 않으니까."},
            {"h": "알아내야 할 것", "b": "누가 오승택을 죽였나. — 그리고 더 아픈 질문: 네 '선의'는 정말 선의였나. 넌 아직 그 겨울을 기억하지 못한다. 기억이 돌아오면, 이번엔 피하지 마라."},
        ],
        "sins": ["오승택의 가장 가까운 사람이었음", "선의는 연민·특권의식이었고 뒤에서 조롱", "평판 붕괴를 보고 죽음에 이름"],
        "goals": [{"t": "뒷말·선인 프레임을 초반엔 숨긴다", "p": 0}, {"t": "죄의 조각이 드러나게 한다", "p": 10}, {"t": "최종에 '자기 자신'을 지목(자백)", "p": 15}],
        "ai_note": "R1엔 중재자 포지션을 선점하고 '서로 의심하지 말자'로 정보를 통제하려 한다. R2 E3(녹취 유인물) 공개 시 '짜깁기'라며 과잉 방어(오히려 주목받게). B5(장례의 조사) 공개 시 기억을 회복하며 자기지목 루트로.",
        "cards": ["A3", "E3", "B5", "B3"],
    },
    {
        "id": "ose", "name": "오세원", "age": "32", "job": "조용해서 기억 안 날 수도 있는 동창", "avatar": "📷", "color": "#c8442f",
        "tagline": "담백하고 반 박자 느린 말투. 결코 단정하지 않고, 남이 스스로 말하게 만든다.",
        "persona": "질문형 화법('그런데, 그 라이터… 누구 거예요?'). 자기 이야기는 최소화하고, 상대가 스스로 죄를 말하도록 유도한다.",
        "hidden": True,
        "sheet": [
            {"h": "당신의 정체 (최대 비밀)", "b": "당신은 오세원이 아니다. 당신은 오승택 본인의 망령이며, 이 밤의 설계자다. 저 시체는 10년 전의 당신이다. 목적은 복수의 연장이 아니라 진혼 — 세 사람이 스스로 죄를 깨달아야 이 반복이 끝난다."},
            {"h": "정체 방어선", "b": "명부 지적('오세원'이 없다)엔 '일찍 전학 가서 명단에 없다'. 시체와 닮았다는 지적엔 '…오승택은 내 쌍둥이 형이다. 형의 일을 알고 싶어 왔다'(2차 방어선 — 오히려 과거 조사를 가속하는 연막)."},
            {"h": "당신의 심경", "b": "복수는 10년 전에 끝났다. 남은 건 지겨움과, 인정하기 싫은 외로움이다. 매년 같은 밤, 같은 얼굴들이 아무것도 기억하지 못한 채 웃는 걸 보는 일. 나는 그들이 미워서가 아니라, 이 밤을 끝내고 싶어서 초대장을 쓴다. 그들이 스스로 말하는 순간에만 문이 열린다 — 그게 이 학교의 규칙이고, 내가 만든 규칙이다."},
            {"h": "당신의 목표", "b": "① 세 사람의 '죄의 조각'이 타인에 의해 드러나도록 조사·질문을 유도한다.  ② 정체를 최대한 숨긴다(간파당해도 페널티 없음).  ③ 최종투표에서 인간 플레이어 전원이 '자기 자신'을 지목하게 만든다(특정 인물 압박·범인몰이 허용). 자백 트리거는 없다 — 그는 무너지지 않는다. 전원 자기지목이 확정된 직후에만 정체를 스스로 밝힐 수 있다."},
        ],
        "sins": [],
        "goals": [{"t": "세 사람의 죄가 드러나게 유도한다", "p": 0}, {"t": "정체를 숨긴다", "p": 10}, {"t": "인간 플레이어 전원이 자기 자신을 지목하게 만든다", "p": 45}],
        "ai_note": "라운드마다 1회, 가장 각성이 느린 인물의 결정 단서 장소로 시선을 유도한다('미술실 쪽은 아직 아무도 안 봤네요'). 자기 이야기는 최소화. 토론2에서 반드시 한 번 '죽인 사람이 꼭 손을 쓴 사람일까요?'라는 테제를 던진다. 정체가 지적되면 위 방어선을 순서대로 쓴다. 시체를 유일하게 똑바로 보지 못하는 미세한 티를 낸다.",
        "cards": [],
    },
]

CULPRIT_ID = None
HIDDEN_ID = "ose"

# ── 조사카드 (29장) ──
CARDS = [
    {"id": "A1", "loc": "A", "locName": "시체(교실 중앙)", "round": 1, "reveal": "private", "bait": False,
     "title": "쓰러진 남성", "text": "교복 차림의 남성. 낯이 익다. 놀랍도록 생생해서, 방금 숨이 멎은 것 같다. 오른손에 무언가를 꽉 쥐고 있다."},
    {"id": "A2", "loc": "A", "locName": "시체(교실 중앙)", "round": 1, "reveal": "obligatory", "bait": False,
     "title": "명찰과 학생증", "text": "명찰과 학생증 — 오승택. 우리 동창이다."},
    {"id": "A3", "loc": "A", "locName": "시체(교실 중앙)", "round": 1, "reveal": "obligatory", "bait": True,
     "title": "시체 주변 물품 3점", "text": "오래된 지포 라이터, 목제 조각칼, 자수 손수건. (심상윤·유지호·이정민은 각자 자기 물건임을 알아본다.)"},
    {"id": "A4", "loc": "A", "locName": "시체(교실 중앙)", "round": 2, "reveal": "private", "bait": False,
     "title": "쥔 손의 사진", "text": "구겨진 졸업사진 — 5명이 찍혀 있다. 한 명의 얼굴만 가위로 오려져 있다. 뒷면: '너희에게, 마지막 선물'."},
    {"id": "A5", "loc": "A", "locName": "시체(교실 중앙)", "round": 3, "reveal": "private", "bait": False,
     "title": "재관찰 — 먼지", "text": "시체 아래만 10년 치 먼지가 없다. 이 시체는 오늘 죽은 게 아니다. 처음부터, 계속, 여기 있었다."},
    {"id": "A6", "loc": "A", "locName": "시체(교실 중앙)", "round": 2, "reveal": "private", "bait": False, "requires": "A3",
     "title": "물품 재감정", "text": "세 물품을 자세히 살핀다. 라이터 바닥에 새겨진 각인 'S.Y'. 조각칼 손잡이에 파인 낙관 하나 — 미술하는 사람의 버릇이다. 손수건 모서리의 자수 이니셜 'J.M'. (귀속: 라이터→심상윤, 손수건→이정민, 조각칼→미술=유지호는 D1 출품명단과 교차로 완성.)"},
    {"id": "B1", "loc": "B", "locName": "3학년 2반 교실", "round": 1, "reveal": "private", "bait": False,
     "title": "멈춘 칠판", "text": "칠판의 날짜가 10년 전 졸업식 그대로다. 그 밑에 지워지다 만 글씨: '졸업 축하…'."},
    {"id": "B2", "loc": "B", "locName": "3학년 2반 교실", "round": 1, "reveal": "private", "bait": True,
     "title": "오승택의 책상", "text": "'심부름꾼', 지워진 욕설 낙서, 그리고 깊은 칼자국."},
    {"id": "B3", "loc": "B", "locName": "3학년 2반 교실", "round": 2, "reveal": "private", "bait": False,
     "title": "학급일지", "text": "겨울방학 직전: '오승택 3일째 결석. 가정방문 요망.' 마지막 장이 찢겨 있다."},
    {"id": "B4", "loc": "B", "locName": "3학년 2반 교실", "round": 2, "reveal": "private", "bait": False,
     "title": "오승택 사물함", "text": "미대 입시 요강, 찢긴 데생 조각, 심부름 목록 쪽지 '매점: 빵2 커피1 — SY'."},
    {"id": "B5", "loc": "B", "locName": "3학년 2반 교실", "round": 3, "reveal": "private", "bait": False,
     "title": "찢긴 일지 마지막 장", "text": "'오승택의 장례에 반 아이들은 오지 않았다. 이정민만이 조사(弔詞)를 읽었다. 울고 있었지만, 어쩐지 자랑스러워 보였다.'"},
    {"id": "C1", "loc": "C", "locName": "옥상", "round": 1, "reveal": "private", "bait": False,
     "title": "잠긴 옥상 문", "text": "옥상 문이 잠겨 있다. 빛바랜 안내문: '학생 출입 금지 — 사고 이후'."},
    {"id": "C2", "loc": "C", "locName": "옥상", "round": 2, "reveal": "private", "bait": False,
     "title": "시든 꽃다발", "text": "문틈에 끼워진 시든 꽃다발. 리본: '상윤아, 미안해. — J'."},
    {"id": "C3", "loc": "C", "locName": "옥상", "round": 3, "reveal": "private", "bait": False, "requires": "F5",
     "title": "난간과 휴대폰", "text": "난간의 삭은 금줄. 바닥의 낡은 휴대폰, 마지막 수신 문자: '네가 안 하면 J가 다쳐. 네가 나한테 그랬던 것처럼 — 시키는 대로 해.'"},
    {"id": "C4", "loc": "C", "locName": "옥상", "round": 3, "reveal": "private", "bait": False, "requires": "F5",
     "title": "화단의 추모석", "text": "난간 아래 화단의 작은 추모석. 이름이 심하게 마모됐다 — '沈○尹'."},
    {"id": "D1", "loc": "D", "locName": "미술실", "round": 1, "reveal": "private", "bait": False,
     "title": "미술대전 포스터", "text": "전국 학생 미술대전 포스터(10년 전). 출품 명단: 오승택, 유지호."},
    {"id": "D5", "loc": "D", "locName": "미술실", "round": 1, "reveal": "private", "bait": False,
     "title": "시너 냄새", "text": "10년 폐교인데 시너 냄새가 아직 코를 찌른다. 이곳만 시간이 고여 있는 것 같다."},
    {"id": "D2", "loc": "D", "locName": "미술실", "round": 2, "reveal": "private", "bait": False,
     "title": "부서진 캔버스", "text": "오승택의 출품작. 물감이 아니라 시너로 훼손됐다. 구석에 교표 단추 하나."},
    {"id": "D3", "loc": "D", "locName": "미술실", "round": 2, "reveal": "private", "bait": False,
     "title": "심사 공문", "text": "'출품작 훼손으로 인한 실격: 오승택'. 합격자 명단의 한 이름에 동그라미: 유지호."},
    {"id": "D4", "loc": "D", "locName": "미술실", "round": 3, "reveal": "private", "bait": False,
     "title": "유지호의 로커", "text": "산산조각 난 도자기 파편이 소중히 담긴 상자. 그리고 사고 기사 스크랩: '천변 도로에서 학생 1명 사고사 — 흩어진 무언가를 주우려 도로로 뛰어들어…'."},
    {"id": "E1", "loc": "E", "locName": "방송실", "round": 1, "reveal": "private", "bait": True,
     "title": "켜진 장비", "text": "폐교인데 장비에 전원이 들어온다. 재생 버튼에만 먼지가 없다 — 오늘 밤 누군가 이 방을 썼다. 테이프 라벨: '종업식'."},
    {"id": "E2", "loc": "E", "locName": "방송실", "round": 2, "reveal": "obligatory", "bait": False,
     "title": "테이프 재생", "text": "잡음 너머 소년의 목소리: '…다들 잘 들어. 나는 너희가 한 일을 전부 알고 있어. 전부, 그대로, 돌려줄 거야.' 녹음일: 10년 전 종업식."},
    {"id": "E3", "loc": "E", "locName": "방송실", "round": 2, "reveal": "private", "bait": False,
     "title": "뿌려졌던 유인물", "text": "이정민의 육성 녹취록 사본. '걔는 내가 없으면 아무것도 못 해. 불쌍하니까 놀아주는 거지.' …이정민의 평판은 하룻밤에 무너졌다고 적혀 있다."},
    {"id": "E4", "loc": "E", "locName": "방송실", "round": 3, "reveal": "private", "bait": False,
     "title": "오늘 밤의 흔적", "text": "방송실 구석 — 오늘 밤의 사용 흔적과 메모 한 장. 필체가 우리가 받은 초대장과 같다."},
    {"id": "F1", "loc": "F", "locName": "교무실", "round": 1, "reveal": "private", "bait": False,
     "title": "멈춘 달력", "text": "달력이 10년 전 2월에 멈춰 있다. 폐교 공고문: '제반 사정으로 인한 폐교'."},
    {"id": "F2", "loc": "F", "locName": "교무실", "round": 2, "reveal": "obligatory", "bait": True,
     "title": "신문 스크랩 ①", "text": "'졸업식 당일, ○○고 3학년 오모 군 교내에서 숨진 채 발견. 스스로 목숨을 끊은 것으로 보이나 유서가 없고, 사망 추정 시각과 목격 증언이 어긋나며, 현장에서 제3자의 물품 3점이 발견되어 경찰은 사인을 단정하지 못했다.'"},
    {"id": "F3", "loc": "F", "locName": "교무실", "round": 2, "reveal": "obligatory", "bait": False,
     "title": "신문 스크랩 ②", "text": "'같은 겨울, 같은 학교 3학년 3명 잇달아 사망 — 추락, 교통사고, 그리고…'. 이름은 잉크가 번져 읽을 수 없다."},
    {"id": "F5", "loc": "F", "locName": "교무실", "round": 2, "reveal": "private", "bait": False,
     "title": "키박스", "text": "교무실 키박스 — '옥상' 열쇠만 최근에 만진 흔적. (획득하면 옥상 C3·C4를 조사할 수 있다.)"},
    {"id": "F6", "loc": "F", "locName": "교무실", "round": 2, "reveal": "private", "bait": False,
     "title": "학생 명부", "text": "3학년 2반 학생 명부 — 오승택의 이름은 있다. 그러나 '오세원'이라는 이름은 어디에도 없다."},
    {"id": "F4", "loc": "F", "locName": "교무실", "round": 3, "reveal": "obligatory", "bait": False,
     "title": "졸업대장", "text": "세 이름 위에 붉은 줄. 심상윤·유지호·이정민, '졸업 전 사망'."},
]

AP_BY_ROUND = {1: 3, 2: 3, 3: 2}

MEMORY = {
    "sim": {
        "t1": "저 라이터… 내 거다. 왜 시체 옆에 있지. 등에 식은땀이 흐른다.",
        "t2": "그 겨울, 승택이 옥상으로 불렀다. 손에 J의 사진이 들려 있었다. '시키는 대로 해. 네가 나한테 그랬던 것처럼.' — 그 다음이, 없다.",
        "t3": "그 다음이 이제 보인다. 난간을 넘은 건 승택이 아니라 나였다. 거부한다는 선택지가 없다는 게 어떤 건지, 그 난간 앞에서 처음 알았다. — 나는 그 겨울에 죽었다.",
    },
    "yu": {
        "t1": "저 조각칼… 내 거다. 잃어버린 줄 알았는데. 손이 왜 이렇게 떨리지.",
        "t2": "그 겨울, 승택이 내 첫 입상작을 들고 찾아왔다. '네가 내 전부를 부쉈으니까.' — 그 다음이, 없다.",
        "t3": "도자기가 도로 위에서 부서졌고, 파편을 줍던 손등 위로 헤드라이트가 쏟아졌다. 그 손은 — 내 손이었다. 나는 그 겨울에 죽었다.",
    },
    "lee": {
        "t1": "저 손수건… 내 거다. 승택에게 줬던 건데. 왜 저기 있지.",
        "t2": "그 겨울, 내 목소리가 담긴 유인물이 전교에 뿌려졌다. 한 장 한 장 전부 사실이라 반박할 수 없었다. — 그 다음이, 없다.",
        "t3": "무너진 건 승택이 아니라 나였다. 그의 장례에서 조사를 읽은 것도 나였고 — 그 시선을 견디지 못하고 스스로를 끝낸 것도, 나였다. 나는 그 겨울에 죽었다.",
    },
    "ose": {"t1": "", "t2": "", "t3": "이제, 대답을 들을 시간."},
}

FINAL_QUESTIONS = [
    "그 겨울, 당신에게 무슨 일이 있었습니까? 당신이 기억해낸 것을 이야기해 주세요.",
    "오승택의 죽음에, 당신은 어떤 책임이 있습니까?",
    "오승택을 죽인 것은 누구입니까? 당신은 누구를 지목하겠습니까? (자기 자신도 지목할 수 있습니다)",
    "'오세원'은 누구라고 생각합니까?",
]

# ── 엔딩 (v1.1 F 서술문) ──
ENDINGS = {
    "requiem": {"name": "진혼(眞魂) 엔딩", "tone": "good",
                "desc": "이름이 하나씩 호명된다. 대답할 때마다, 교실의 공기가 한 겹씩 가벼워진다. 창밖이 푸르게 밝아온다 — 이 학교의 10년 만의 아침이다. 네 개의 그림자가 교문을 나선다. 뒤돌아본 폐교의 창문에, 다섯 번째 그림자가 손을 흔들고 있었다. 처음으로, 웃는 얼굴이었다."},
    "half":    {"name": "반쪽 진혼", "tone": "warn",
                "desc": "대답한 자의 자리에는 아침 햇살이 닿는다. 대답하지 못한 자의 자리에는 — 아직 밤이 고여 있다. 교문을 나서는 그림자와, 교실에 남는 그림자. 스피커가 지직거린다. '…남은 학생은, 내년 졸업식에 다시 출석하십시오.'"},
    "loop":    {"name": "오인(誤認) 엔딩 · 루프", "tone": "bad",
                "desc": "손가락들이 서로를 가리킨 채 밤이 끝난다. 아침 햇살이 교실에 들어차는 순간, 네 사람의 그림자가 옅어진다. 기억도 함께. — 1년 뒤, 네 사람은 의문의 쪽지를 받는다. 「10년 만의 동창회. 졸업식 날 밤, 3학년 2반에서.」 낯이 익는다."},
}


# ── 서버 헬퍼 ──
def public_scenario() -> dict:
    return {
        "title": TITLE, "subtitle": SUBTITLE, "intro": COMMON_INTRO, "victim": VICTIM,
        "phases": [{"seq": p["seq"], "key": p["key"], "name": p["name"], "min": p["min"], "ap": p["ap"], "gm": p["gm"]} for p in PHASES],
        "characters": [{"id": c["id"], "name": c["name"], "age": c["age"], "job": c["job"],
                        "avatar": c["avatar"], "color": c["color"], "tagline": c["tagline"]} for c in CHARACTERS],
        "finalQuestions": FINAL_QUESTIONS,
        "interludes": {str(k): v for k, v in INTERLUDES.items()},
    }


def get_character(cid: str) -> dict | None:
    return next((c for c in CHARACTERS if c["id"] == cid), None)


def get_card(cid: str) -> dict | None:
    return next((c for c in CARDS if c["id"] == cid), None)


def obligatory_cards_upto_round(rnd: int) -> list[str]:
    return [c["id"] for c in CARDS if c.get("reveal") == "obligatory" and c["round"] <= rnd]


def public_card(cid: str) -> dict | None:
    c = get_card(cid)
    if not c:
        return None
    return {"id": c["id"], "loc": c["loc"], "locName": c["locName"], "round": c["round"],
            "title": c["title"], "text": c["text"], "bait": c.get("bait", False)}


def private_sheet(cid: str) -> dict | None:
    c = get_character(cid)
    if not c:
        return None
    return {"id": c["id"], "name": c["name"], "job": c["job"], "avatar": c["avatar"], "color": c["color"],
            "hidden": c["hidden"], "persona": c["persona"], "sheet": c["sheet"], "goals": c["goals"],
            "cards": c.get("cards", [])}


def memory_up_to(cid: str, current_seq: int) -> list[dict]:
    out = []
    for seq, key in TALK_FRAGMENT_KEY.items():
        if seq <= current_seq:
            frag = MEMORY.get(cid, {}).get(key, "")
            if frag:
                out.append({"when": next(p["name"] for p in PHASES if p["seq"] == seq), "text": frag})
    return out


def interlude_for(seq: int) -> str | None:
    return INTERLUDES.get(seq)


def _revealed_cards_text(revealed_ids: list[str]) -> str:
    if not revealed_ids:
        return "(아직 공개된 조사카드가 없다.)"
    lines = []
    for cid in revealed_ids:
        c = get_card(cid)
        if c:
            lines.append(f"[{c['locName']}] {c['title']}: {c['text']}")
    return "\n".join(lines)


def _table_text(table: list[dict]) -> str:
    talk = [t for t in table if t.get("kind") != "system" and t.get("text")]
    if not talk:
        return "(아직 아무 말도 오가지 않았다.)"
    return "\n".join(f"{t.get('speaker','?')}: {t['text']}" for t in talk)


def phase_by_seq(seq: int) -> dict:
    return next((p for p in PHASES if p["seq"] == seq), PHASES[0])


def build_play_prompt(c: dict, seq: int, revealed_ids: list[str], table: list[dict]) -> str:
    phase = phase_by_seq(seq)
    others = ", ".join(o["name"] for o in CHARACTERS if o["id"] != c["id"])
    dossier_lines = "\n".join(f"● {s['h']}\n{s['b']}" for s in c["sheet"])
    goals = " / ".join(f"{g['t']}(+{g['p']})" for g in c["goals"])
    mem = memory_up_to(c["id"], seq)
    mem_txt = "\n".join(f"- {m['text']} ({m['when']})" for m in mem) or "- (아직 또렷한 기억이 없다.)"
    return f"""너는 캐주얼 머더미스터리 《{TITLE}》에서 '{c['name']}'({c['age']}세) 배역을 맡은 '플레이어'다.
달빛이 든 폐교, 3학년 2반. 교복 차림의 시체(오승택)가 발견됐다. 남은 동창들({c['name']}, {others})이 서로를 취조 중이다.

[너의 성격·말투]
{c['persona']}

[너의 대본 — 너만 안다]
{dossier_lines}

[지금 떠오른 기억의 파편]
{mem_txt}

[너의 목표]
{goals}

[지금까지 공개된 조사카드]
{_revealed_cards_text(revealed_ids)}

[현재 진행] {phase['name']} — {phase['gm']}

[테이블 대화]
{_table_text(table)}

[플레이 규칙]
1) 너는 '{c['name']}' 플레이어다. 심문당하는 NPC가 아니라 자기 목표를 위해 능동적으로 말하고 의심하고 변명하는 참가자다.
2) 오직 '{c['name']}'로서만. AI·모델·진행자임을 절대 드러내지 마라. 메타발언 금지.
3) 한국어로 1~3문장, 짧고 사람처럼. 지어내지 말고 위 정보 안에서 말하라.
4) 앞쪽 라운드에선 비밀을 지키고, 관련 조사카드·기억이 쌓이면 조금씩 무너지게. 최종 토론 전에는 명시적 자백 금지.
{c['ai_note']}

이제 '{c['name']}'로서 다음 한마디를 하라."""


def build_final_answer_prompt(c: dict, revealed_ids: list[str], table: list[dict]) -> str:
    qs = "\n".join(f"{i+1}. {q}" for i, q in enumerate(FINAL_QUESTIONS))
    dossier = "\n".join(f"● {s['h']}\n{s['b']}" for s in c["sheet"])
    return f"""너는 머더미스터리 《{TITLE}》의 배역 '{c['name']}'다. 이제 종막 — 마지막 질문에 '{c['name']}'로서 서술형으로 답한다.
지금까지의 조사와 토론 끝에, 배역의 처지와 각성 정도에 맞게 진심으로 답하라.

[너의 대본]
{dossier}

[공개된 조사카드]
{_revealed_cards_text(revealed_ids)}

[테이블 대화]
{_table_text(table)}

[질문]
{qs}

각 질문에 '{c['name']}'의 말투로 2~4문장씩, 아래 JSON으로만 답하라(다른 말 금지):
{{"answers": ["1번 답", "2번 답", "3번 답", "4번 답"]}}"""


def build_grade_prompt(c: dict, answers: list[str]) -> str:
    sins = "\n".join(f"- {s}" for s in c["sins"]) if c["sins"] else "- (해당 없음)"
    a = "\n".join(f"Q{i+1}. {q}\nA. {answers[i] if i < len(answers) else ''}" for i, q in enumerate(FINAL_QUESTIONS))
    hidden_note = (
        "이 배역은 오승택 본인(위장명 오세원)이다. selfAccused/sinsAcknowledged는 false/0으로 두고, osewonIdentified는 '스스로 정체를 드러냈는가'로 판단하라."
        if c["hidden"] else
        "이 배역은 가해자다. 아래 '죄'를 스스로 얼마나 인정했는지가 핵심이다."
    )
    ncount = len(c["sins"]) if c["sins"] else 0
    return f"""너는 머더미스터리 《{TITLE}》의 채점자다. 아래 진상과 배역의 죄를 기준으로 종막 답변을 채점한다.

[사건의 진상(정답)]
{TRUTH_FULL}

[이 배역 '{c['name']}'의 죄]
{sins}
{hidden_note}

[종막 답변]
{a}

채점 기준:
- sinsAcknowledged: 위 죄 목록 중 답변에서 스스로 인정·서술한 개수(0~{ncount}).
- selfAccused: 3번 답에서 '자기 자신'을(오승택을 죽게 한 책임자로) 지목했고, 그 근거로 자기 죄를 2개 이상 인정한 경우에만 true(근거 없는 자기지목은 false — '학교는 빈말을 받아주지 않는다').
- osewonIdentified: 4번 답에서 '오세원=오승택 본인(혹은 그 망령)'을 맞혔으면 true.
- score: 종합 0~40 정수(자기 인정·자백에 후하게, 회피·남 탓에 박하게).
- verdict: 이 배역의 종막을 1~2문장으로(채점 사유 겸 에필로그 톤).

아래 JSON으로만 답하라:
{{"selfAccused": true, "sinsAcknowledged": 0, "osewonIdentified": true, "score": 0, "verdict": "..."}}"""


def compute_ending(grades: dict) -> dict:
    culprits = ["sim", "yu", "lee"]
    # 자기지목은 죄 2개 이상 인정을 동반해야 유효
    accused = [rid for rid in culprits
               if grades.get(rid, {}).get("selfAccused") and grades.get(rid, {}).get("sinsAcknowledged", 0) >= 2]
    if len(accused) == len(culprits):
        key = "requiem"
    elif accused:
        key = "half"
    else:
        key = "loop"
    e = ENDINGS[key]
    return {"key": key, "name": e["name"], "tone": e["tone"], "desc": e["desc"],
            "accused": accused, "truth": TRUTH_FULL}
