# Image Asset Manifest — PIMM Murderboard

Noir murder-mystery web game. This catalogs every place an image would raise quality across the three scenarios (**graduation** 졸업사진, **subway** 막차, **submarine** 심연의 정원 / `abyss_garden.py`), so a human or the Cowork app can generate them systematically.

> **Scope note.** This is an asset plan only — no game code is changed. Where an asset "plugs in" is described per row; wiring it into `index.html` / `landing.html` is a separate task.

---

## 0. How to read this manifest

Every generation prompt below is written as a **specific subject line**. To get the final prompt, **append the shared HOUSE STYLE suffix** (Section 1) and, where noted, the **per-scenario MOOD tag**. This keeps all 50+ assets feeling like one set without repeating the long suffix on every row.

**Filename convention:** `<scenario>_<type>_<slot>.png`, all lowercase.
Scenario slugs match `landing.html` ids: `graduation`, `subway`, `submarine`.
Types: `poster`, `opening`, `portrait`, `card`, `zone`, plus `shared_*`.

**Priorities:** **P0** must-have (frames the whole session / reused on every screen) · **P1** high-impact (key reveals, card back) · **P2** nice-to-have (per-zone atmosphere, secondary cards, textures).

---

## 1. HOUSE STYLE (append to EVERY prompt)

```
cinematic noir, moody atmospheric lighting, muted desaturated palette with a single
blood-red accent (#C8392B), heavy film grain, shallow depth of field, volumetric haze,
painterly photographic realism, dramatic low-key shadows, high detail, 35mm still,
no text, no watermark, no signature, no lettering, no logo
```

**Per-scenario MOOD tag** (append after the subject, before the house style):

| Scenario | MOOD tag |
|---|---|
| graduation | `abandoned rural high school at night, moonlight through dusty cracked windows, cold winter stillness, time frozen ten years ago, faded chalk and peeling paint, melancholy` |
| subway | `deserted late-night subway station 1:20am, cold flickering fluorescent tubes, wet grey concrete platform, third rail, closed shutters, sodium-vapor grime, isolation` |
| submarine | `cramped deep-sea submarine interior, red emergency alert lighting, rising cold water, riveted steel bulkheads, condensation and pipes, claustrophobic pressure, gauges glowing` |

**Pollinations (Flux) URL pattern** — reference for generating each asset:

```
https://image.pollinations.ai/prompt/<urlencoded-prompt>?width=W&height=H&model=flux&nologo=true&seed=N
```

Keep a **fixed seed per scenario** (e.g. graduation=1010, subway=2020, submarine=3030) so portraits/cards within a scenario stay tonally consistent; vary only the trailing digit per asset if you need small variety.

---

## 2. Totals & "Generate these first (P0)"

| Type | graduation | subway | submarine | Total |
|---|---|---|---|---|
| Poster (already done) | 1 ✅ | 1 ✅ | 1 ✅ | **3 done** |
| Opening cinematic | 1 | 1 | 1 | 3 |
| Character portraits | 4 | 4 | 6 | 14 |
| Investigation card art | 6 | 6 | 5 | 17 |
| Zone / location art | 6 | 6 | 6 | 18 |
| Shared (card back, grain) | — | — | — | 2 |
| **New assets to generate** | | | | **54** |
| **Grand catalog (incl. posters)** | | | | **57** |

**P0 shortlist — generate these 17 first** (highest reuse + frames every session, all low spoiler risk):

1. `graduation_opening.png`, `subway_opening.png`, `submarine_opening.png` — 3 opening cinematics (shown to every player at "막이 오른다").
2. All 14 character portraits — reused on the role card, cue card, turn bar, and every chat message avatar:
   `graduation_portrait_{sim,yu,lee,ose}.png`,
   `subway_portrait_{han,ora,mun,yun}.png`,
   `submarine_portrait_{munjaei,kangyunseo,oserin,jinharam,yutaeo,handokyung}.png`.

---

## 3. POSTER — case-file poster (STATUS: all 3 ✅ DONE)

Already embedded as base64 JPEG in `landing.html` → `const SCEN=[…]` → each object's `img:` field. Rendered inside `.poster .frame .art` (aspect-ratio **3 / 4.2**). No action needed unless you want to re-master at higher resolution.

| Key | Filename (if re-mastering) | Dims (3:4.2) | Status |
|---|---|---|---|
| graduation · poster | `graduation_poster.png` | 896 × 1254 | ✅ in `landing.html` SCEN |
| subway · poster | `subway_poster.png` | 896 × 1254 | ✅ in `landing.html` SCEN |
| submarine · poster | `submarine_poster.png` | 896 × 1254 | ✅ in `landing.html` SCEN |

If re-mastering, reuse the poster subject lines implied by each scenario's opening (Section 4) in portrait 3:4.2 framing. **Placement:** `landing.html` scenario carousel. Priority **P2** (only if upscaling).

---

## 4. OPENING CINEMATIC — 1 wide atmospheric background per scenario  ·  P0

Plugs into `index.html` → `gmCinematic()` / `buildGMBody(k==="open")` panel ("막이 오른다 · 공통지문 낭독"), currently text-only over a flat panel. Use as a **full-width background** behind the animated intro lines. Aspect **16:9**, dims **1344 × 768**. No people, no gore — pure establishing shot.

| Key / slot | Filename | Prompt subject (+ MOOD + HOUSE STYLE) | Priority |
|---|---|---|---|
| graduation · opening | `graduation_opening.png` | `wide establishing shot of an empty moonlit classroom in an abandoned school, rows of dusty desks, a single spilled shaft of pale blue moonlight across the floor, faint red light bleeding from a doorway, utterly still` | P0 |
| subway · opening | `subway_opening.png` | `wide establishing shot down an empty late-night subway platform, one flickering fluorescent tube, "운행 종료" glow reflected on wet concrete, a lowered shutter at the far end, a faint red emergency lamp near the track edge` | P0 |
| submarine · opening | `submarine_opening.png` | `wide establishing shot of a dim submarine control corridor, red alert strobes, thin film of water on the deck plates, glowing depth gauges and valves, a heavy sealed bulkhead door at the end of the passage` | P0 |

---

## 5. CHARACTER PORTRAITS — one per character  ·  P0

Plugs into `index.html` avatar slots: `.role-card .av`, cue card, `gmTurnBar`/`renderTurnbar` turn chips, and `renderChat` message avatars (all currently `<div class="av">${c.avatar}</div>` emoji). Recommend **3:4** framing so it crops cleanly to a circular avatar and also works as a larger cue-card portrait. Dims **768 × 1024**. Bust/waist-up, single subject, plain moody background, matching each character's key color as the dominant accent.

> **Spoiler discipline:** portraits describe persona/age/job faithfully but must NOT reveal hidden roles. `ose` (graduation, hidden ghost/host), `yun` (subway, culprit), and `handokyung` (submarine, culprit) are drawn as their *cover* selves — no ghostly/guilty/villain cues.

### graduation (4)

| Key / slot | Filename | Prompt subject (+ MOOD + HOUSE STYLE) | Priority |
|---|---|---|---|
| graduation · portrait · 심상윤 (sim) | `graduation_portrait_sim.png` | `charismatic rugged man early 30s, faint stubble, easygoing confident half-smile, worn leather jacket, an old brass zippo lighter in hand, warm amber key light (#e6a355)` | P0 |
| graduation · portrait · 유지호 (yu) | `graduation_portrait_yu.png` | `reserved observant man early 30s, quiet perfectionist, art-school type, clay dust on careful hands, minimal expression, cool steel-blue key light (#7fb4d6)` | P0 |
| graduation · portrait · 이정민 (lee) | `graduation_portrait_lee.png` | `gentle warm approachable person early 30s, soft caring reassuring smile, tidy volunteer look, an embroidered handkerchief, sage-green key light (#8ec98a)` | P0 |
| graduation · portrait · 오세원 (ose) *(hidden)* | `graduation_portrait_ose.png` | `calm understated quiet man early 30s holding an old film camera, unreadable neutral half-step-behind expression, plain and unassuming, deep rust-red key light (#c8442f)` — **do NOT depict ghost, corpse, translucency, or the victim** | P0 |

### subway (4)

| Key / slot | Filename | Prompt subject (+ MOOD + HOUSE STYLE) | Priority |
|---|---|---|---|
| subway · portrait · 한지운 (han) | `subway_portrait_han.png` | `tired diligent male subway night-shift attendant mid 30s, rumpled navy uniform, lanyard and keys, fluorescent shadows under the eyes, defensive posture, cold blue key light (#5a8dd6)` | P0 |
| subway · portrait · 오세라 (ora) | `subway_portrait_ora.png` | `young woman 26, convenience-store night clerk in an apron, a bright brittle smile that hides fear, warm amber key light (#e8a13c)` | P0 |
| subway · portrait · 문상혁 (mun) | `subway_portrait_mun.png` | `disheveled drunk middle-aged salaryman early 40s, loosened tie, flushed face, bitter weary slump, rust-red key light (#c8442f)` | P0 |
| subway · portrait · 윤미래 (yun) *(culprit)* | `subway_portrait_yun.png` | `poised composed sharp-eyed woman early 30s, calm intelligent trustworthy expression, holding a reporter's notebook, the reliable one people lean on, sage-green key light (#8ec98a)` — **draw her as the trustworthy detective; NO guilt cues, no wounded hands, no scarf detail** | P0 |

### submarine (6)

| Key / slot | Filename | Prompt subject (+ MOOD + HOUSE STYLE) | Priority |
|---|---|---|---|
| submarine · portrait · 문재이 (navigator) | `submarine_portrait_munjaei.png` | `determined resolute female navigator, survival-first intensity, damp jumpsuit, teal key light (#17B7A6)` | P0 |
| submarine · portrait · 강윤서 (comms) | `submarine_portrait_kangyunseo.png` | `focused communications operator clutching a headset, anxious to send a signal, amber key light (#E5A02C)` | P0 |
| submarine · portrait · 오세린 (medic) | `submarine_portrait_oserin.png` | `cool composed ship's medical officer, clinical detached calm, latex gloves, pale-silver key light (#D9E2EC)` | P0 |
| submarine · portrait · 진하람 (cargo) | `submarine_portrait_jinharam.png` | `wary cargo master holding a folded manifest close to the chest, guarded, amethyst-purple key light (#7C5CC0)` | P0 |
| submarine · portrait · 유태오 (junior helm) | `submarine_portrait_yutaeo.png` | `frightened young junior crewman, wide uncertain eyes, deep-blue key light (#2E5AAC)` | P0 |
| submarine · portrait · 한도경 (chief eng.) *(culprit)* | `submarine_portrait_handokyung.png` | `steady reassuring chief engineer, grease-stained coveralls, calm dependable protective leader, rust-red key light (#B33A2E)` — **draw as the devoted reliable leader; NO menace or villain cues** | P0 |

---

## 6. INVESTIGATION CARD ART — highest-impact cards  ·  P1

Plugs into `index.html` → `openCard()` modal (currently title + text only). Add art as a header/illustration above the card text. Aspect **3:4**, dims **896 × 1152**. Only the highest-impact cards are listed (crime scene / key evidence / reveal). Reveal cards are drawn to set mood **without solving the mystery**.

### graduation (6 of 29)

| Key / slot | Filename | Card title | Prompt subject (+ MOOD + HOUSE STYLE) | Why / spoiler note | Pri |
|---|---|---|---|---|---|
| graduation · card · A1 | `graduation_card_a1.png` | 쓰러진 남성 | `a young man in a school uniform lying collapsed on a moonlit classroom floor, face turned away, one hand clenched shut, eerily fresh and undecayed` | Crime-scene establishing shot | P1 |
| graduation · card · A3 | `graduation_card_a3.png` | 시체 주변 물품 3점 | `three objects laid on a dusty floor in moonlight: an old brass zippo lighter, a wooden carving knife, an embroidered handkerchief, still-life` | Central evidence trio | P1 |
| graduation · card · A4 | `graduation_card_a4.png` | 쥔 손의 사진 | `a crumpled old graduation photograph of five students, one face neatly cut out with scissors, held in a pale clenched hand` | Emotional reveal — cut-out face intrigues without naming who | P1 |
| graduation · card · A5 | `graduation_card_a5.png` | 재관찰 — 먼지 | `a clean dust-free silhouette on a thickly dust-covered classroom floor where a body has lain untouched for a decade, cold shaft of moonlight` | Shock beat (`box.classList shock`); implies time, not solution | P1 |
| graduation · card · D2 | `graduation_card_d2.png` | 부서진 캔버스 | `a slashed and thinner-soaked ruined painting on an easel in an abandoned art room, a single school-crest button on the floor, sharp chemical haze` | Key motive evidence | P1 |
| graduation · card · C3 | `graduation_card_c3.png` | 난간과 휴대폰 | `a corroded rooftop railing at night, an old cracked phone lying on the concrete with its screen faintly glowing, wind-blown, vertigo drop beyond` | Reveal-adjacent; sets dread, hides culprit | P1 |

### subway (6 of 21)

| Key / slot | Filename | Card title | Prompt subject (+ MOOD + HOUSE STYLE) | Why / spoiler note | Pri |
|---|---|---|---|---|---|
| subway · card · A1 | `subway_card_a1.png` | 선로의 시신 | `a man face-down on subway tracks at the platform's end, fingertips scorched black against the third rail, cold blue light` | Crime-scene establishing shot | P1 |
| subway · card · A2 | `subway_card_a2.png` | 타살의 흔적 | `close macro of a dead hand clutching a few thin frayed fibers of yarn, a shove-shaped bruise implied, forensic tone` | Key clue; show only fibers — do NOT show whose scarf | P1 |
| subway · card · B4 | `subway_card_b4.png` | 승강장 끝 CCTV 사각지대 | `the far end of a subway platform behind a pillar, a pool of total darkness beyond the reach of a security camera, ominous blind spot` | Reveal (blind spot) — atmosphere only, no figure | P1 |
| subway · card · E2 | `subway_card_e2.png` | 목도리와 장갑 | `a discarded woolen scarf with one badly unraveled edge and a pair of gloves in a restroom bin, track gravel and dark grease staining them` | Culprit-pointing evidence; frame the objects only, NO face/identity | P1 |
| subway · card · E3 | `subway_card_e3.png` | 취재수첩과 미행 사진 | `a worn reporter's notebook open beside a spread of grainy surveillance photos of the same man, obsessively tracked, pinned and dated` | Reveal; keep the tracked subject generic, no culprit face | P1 |
| subway · card · F2 | `subway_card_f2.png` | 위조된 기자 신분 | `a cheaply printed press ID and business card beside a yellowed newspaper obituary clipping, laid on a ticket counter` | Reveal of forged identity; objects only, no name legible | P1 |

### submarine (5) — region-evidence, not a CARDS deck

`abyss_garden.py` uses region-based investigation (`INVESTIGATION_RULES.evidence_pool`) rather than a card list, so these illustrate the **key evidence beats / scenes**. Wire them into whatever evidence-reveal panel the submarine build uses. Aspect **3:4**, **896 × 1152**.

| Key / slot | Filename | Beat | Prompt subject (+ MOOD + HOUSE STYLE) | Why / spoiler note | Pri |
|---|---|---|---|---|---|
| submarine · card · victim | `submarine_card_victim.png` | 선장 검안 (의무실) | `a ship captain's body on a cold medical bunk, signs of asphyxiation and a head wound, a medic's gloved examination, sterile teal-lit infirmary` | Crime-scene / cause of death | P1 |
| submarine · card · ballast | `submarine_card_ballast.png` | 밸러스트 밸브 (기관실) | `a heavy ballast valve wheel in an engine room, freshly turned by hand, water seeping in, sabotage implied` | Sabotage clue | P1 |
| submarine · card · terminal | `submarine_card_terminal.png` | 선장 단말 (화물실 이중바닥) | `a hidden captain's handheld terminal concealed in a false cargo-floor compartment, faint screen glow in the dark hold` | The "one door" pivot object | P1 |
| submarine · card · manifest | `submarine_card_manifest.png` | 원자로 매니페스트 (진실 조각) | `an old redacted reactor cargo manifest with a signature partly blotted out, water-stained, held under a work light` | Truth fragment; keep names illegible — no solution | P1 |
| submarine · card · pod | `submarine_card_pod.png` | 탈출 포드 (4석 6인) | `a cramped escape pod interior with exactly four seats, a red launch panel counting down, the weight of two too few` | The central dilemma image | P1 |

---

## 7. ZONE / LOCATION ART — per MAP zone (secondary)  ·  P2

Plugs into `index.html` GM marking board `.gm-loc` headers (currently just `loc + locName` text). Empty rooms, no people. Aspect **4:3**, dims **1024 × 768**. `loc` letter follows each scenario's `MAP` / `REGIONS`. **Highest-value zones are flagged ★** — do those first if not doing all.

### graduation — `MAP` (6)

| Key / slot | Filename | Prompt subject (+ MOOD + HOUSE STYLE) | Value |
|---|---|---|---|
| graduation · zone · A 시체·교실 중앙 | `graduation_zone_a.png` | `center of a moonlit abandoned classroom, empty floor where a body lay, dust and cold light` | ★ |
| graduation · zone · B 3학년 2반 교실 | `graduation_zone_b.png` | `an abandoned classroom, a blackboard frozen with a decade-old graduation date, rows of empty desks` | ★ |
| graduation · zone · C 옥상 | `graduation_zone_c.png` | `a locked school rooftop at night, corroded railing, a withered bouquet wedged in the door, city lights far below` | ★ |
| graduation · zone · D 미술실 | `graduation_zone_d.png` | `an abandoned art room, easels and a ruined canvas, lingering thinner haze, moonlight` | |
| graduation · zone · E 방송실 | `graduation_zone_e.png` | `a dusty school broadcast room, one reel-tape deck with power inexplicably on, a single glowing button` | |
| graduation · zone · F 교무실 | `graduation_zone_f.png` | `an abandoned faculty office, a wall calendar stopped ten years ago, a key box, scattered papers` | |

### subway — `MAP` (6)

| Key / slot | Filename | Prompt subject (+ MOOD + HOUSE STYLE) | Value |
|---|---|---|---|
| subway · zone · A 선로·시체 | `subway_zone_a.png` | `the end of a subway platform and the tracks below, the third rail gleaming, cold and empty` | ★ |
| subway · zone · B 승강장 | `subway_zone_b.png` | `a long deserted subway platform at night, a lone bench, flickering fluorescent tubes` | ★ |
| subway · zone · C 역내 편의점 | `subway_zone_c.png` | `a small lit convenience store inside a subway station at night, a counter with a card terminal, a wall CCTV` | |
| subway · zone · D 관제실 | `subway_zone_d.png` | `a station control room, a wall of CCTV monitors glowing, a master-key cabinet, night shift` | ★ |
| subway · zone · E 화장실·통로 | `subway_zone_e.png` | `a grimy subway restroom and connecting corridor, one dead camera, a trash bin, cold tile` | |
| subway · zone · F 개찰구·매표소 | `subway_zone_f.png` | `subway ticket gates and a shuttered ticket booth, a "운행 종료" board glowing, a lowered shutter` | |

### submarine — `REGIONS` (6)

| Key / slot | Filename | Prompt subject (+ MOOD + HOUSE STYLE) | Value |
|---|---|---|---|
| submarine · zone · 함교 | `submarine_zone_bridge.png` | `a submarine bridge, periscope and helm, tilted horizon warning lights, red alert glow` | ★ |
| submarine · zone · 기관실 | `submarine_zone_engine.png` | `a cramped engine room, ballast valves and pipes, rising water on the deck plates, rust-red light` | ★ |
| submarine · zone · 화물실 | `submarine_zone_cargo.png` | `a shadowy cargo hold, stacked crates and a false-bottom floor panel, a single work lamp` | ★ |
| submarine · zone · 의무실 | `submarine_zone_infirmary.png` | `a small submarine infirmary, a cold bunk and medical trays, pale teal sterile light` | |
| submarine · zone · 통신실 | `submarine_zone_comms.png` | `a submarine communications room, dead radio racks, a severed-signal warning light` | |
| submarine · zone · 선실·격벽통로 | `submarine_zone_corridor.png` | `a narrow bulkhead corridor with sealed watertight doors, a taped-up family photo, flooding underfoot` | |

---

## 8. SHARED — card back, textures, UI atmosphere  ·  P1–P2

| Key / slot | Filename | Dims | Prompt subject (+ HOUSE STYLE) | Placement | Pri |
|---|---|---|---|---|---|
| shared · card back | `shared_cardback.png` | 896 × 1152 (3:4) | `an ornate art-deco noir playing-card back pattern, dark charcoal with a thin blood-red (#C8392B) geometric border and a small central magnifier-and-moon emblem, symmetrical, tileable feel` | `index.html` `openCard()` for face-down / hand (비공개) cards; investigation matrix cells | P1 |
| shared · grain / vignette overlay | `shared_grain.png` | 1344 × 768 (transparent PNG) | `a subtle transparent film-grain and soft dark vignette overlay, 6% opacity dust and scratches, edge falloff` | CSS overlay over cinematic/board panels (matches existing `.art .grain`) | P2 |
| shared · background texture | *(already ✅)* | — | — | `landing.html` `.bg` already embeds a base64 texture; `index.html` uses CSS gradients. Reuse existing. | — |

---

## 9. Wiring reference (where each type renders in code)

| Asset type | File · function / selector | Current state |
|---|---|---|
| Poster | `landing.html` → `SCEN[].img`, `.poster .frame .art` (3:4.2) | ✅ base64 present |
| Opening cinematic | `index.html` → `gmCinematic()` / `buildGMBody(k==="open")` | text-only, no bg image |
| Portrait | `index.html` → `.role-card .av`, `gmTurnBar`/turn chips, `renderChat` `.av`; cue card | emoji `c.avatar` only |
| Card art | `index.html` → `openCard()` modal body | title + text only |
| Zone art | `index.html` → `buildGMBody` `.gm-loc .lh` headers | text label only |
| Card back / grain | `index.html` face-down cards / panel overlays | CSS only |
