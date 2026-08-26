"""Build scene_plan.json for Ink & Testimony E02 from script.json.

Grammar (documented, extends the E01-validated ink-testimony atelier grammar):
- Every script section (81 narration beats + 5 act-break cards = 86) gets its own scene,
  covering the full duration with no gaps -- same coverage rule as E01.
- Stat/date beats with exact numbers (script enhancement_cue type "stat_card") and the
  5 act-break cards become `text_card` scenes: ffmpeg drawtext over a dimmed still,
  never an AI-generated image, because AI models garble exact numbers/text (the
  mandatory guard). This is the same reasoning as E01 scene-11/13.
- Every other beat is either a fresh `generated` (or one `diagram`) ANCHOR frame, or it
  REUSEs the nearest preceding anchor's frame with continued/varied zoompan -- the same
  REUSE-vs-GENERATE tagging E01 used for its pre-approved sample assets, applied here
  internally across the episode. Deliberately held frames (documentary long-hold, not a
  cut-every-beat grammar) fit this piece's low motion_intensity/testimony pacing far
  better than a hard cut every ~7s for 10 straight minutes would.
- Two `transition` bookend scenes (s78, s81) return to and then fade the cold-open
  examination-table frame (s1), mirroring E01's scene-16 bookend.
"""
import json

script = json.load(open("projects/ink-testimony-e02/artifacts/script.json"))
sections = {s["id"]: s for s in script["sections"]}

# id -> anchor description dict. Only anchors (fresh frames) need full authored detail.
ANCHORS = {
    "s1": dict(desc="Ink illustration: an examination/postmortem table, instruments laid beside a tiger's still form, seen from the head end. Full-bleed, no border.",
               framing="full-frame still life, table centered", movement="slow push-in (zoompan 1.0->1.08)",
               shot=dict(shot_size="medium_close", camera_movement="dolly_in", lighting_key="low_key", depth_of_field="shallow", color_temperature="neutral"),
               intent="Cold-open on the examination table itself -- the recurring witness object for the whole piece.", role="establish_context", dark=False, hero=True),
    "s4": dict(desc="Ink illustration: a colonial-era district office interior, ledgers stacked on a desk, seen through an open doorway.",
               framing="medium wide, doorway frame within frame", movement="slow push-in",
               shot=dict(shot_size="medium_wide", camera_movement="dolly_in", lighting_key="natural", depth_of_field="medium", color_temperature="warm"),
               intent="Establish the bureaucratic, paper-and-policy origin of the bounty system before any tiger appears.", role="establish_context", dark=False, hero=False),
    "s9": dict(desc="Ink illustration: a stack of rupee notes and a tiger-claw trophy on a district officer's desk, no legible text on the notes.",
               framing="insert, desk surface", movement="static with micro push-in",
               shot=dict(shot_size="insert", camera_movement="zoom_in", lighting_key="natural", depth_of_field="shallow", color_temperature="warm"),
               intent="The bounty made concrete as an object -- money and trophy side by side.", role="evidence", dark=False, hero=False),
    "s11": dict(desc="Ink illustration: felled timber stacked beside a half-cleared forest edge, stumps in the foreground.",
                framing="wide, clearing in foreground, intact forest behind", movement="slow pull-back",
                shot=dict(shot_size="wide", camera_movement="dolly_out", lighting_key="overcast_soft", depth_of_field="deep", color_temperature="neutral"),
                intent="Visualize the Forest Acts as physical loss, not policy abstraction.", role="evidence", dark=False, hero=False),
    "s13": dict(desc="Ink illustration: a narrow tidal creek through dense mangrove, a small boat and clearing tools resting at the bank.",
                framing="medium wide, creek receding into the mangrove", movement="slow push-in",
                shot=dict(shot_size="medium_wide", camera_movement="dolly_in", lighting_key="overcast_soft", depth_of_field="deep", color_temperature="cool"),
                intent="Establish the Sundarbans as a place before the death-toll numbers land.", role="establish_context", dark=False, hero=False),
    "s19": dict(desc="Ink illustration: dense hill forest at dusk, a narrow footpath vanishing into the treeline.",
                framing="medium wide, path leading into shadow", movement="slow push-in",
                shot=dict(shot_size="medium_wide", camera_movement="dolly_in", lighting_key="blue_hour", depth_of_field="medium", color_temperature="cool"),
                intent="Open the Champawat act on unease -- a path into forest, not a tiger.", role="establish_context", dark=False, hero=False),
    "s21": dict(desc="Ink illustration: a weathered stone boundary marker beside a mountain trail, hills of two nations visible beyond.",
                framing="medium, marker foreground, trail receding", movement="slow pull-back",
                shot=dict(shot_size="medium", camera_movement="dolly_out", lighting_key="overcast_soft", depth_of_field="medium", color_temperature="neutral"),
                intent="Visualize the Nepal-India border crossing as a place, not a map.", role="build_tension", dark=False, hero=False),
    "s24": dict(desc="Ink illustration: a woman's dropped sickle and a bundle of cut grass on a forest path, no figure present.",
                framing="insert, ground-level", movement="static with micro drift",
                shot=dict(shot_size="insert", camera_movement="static", lighting_key="natural", depth_of_field="shallow", color_temperature="neutral"),
                intent="Absence stands in for the victims -- respectful restraint, no depicted violence.", role="emotional_beat", dark=False, hero=False),
    "s25": dict(desc="Ink illustration: a lean young man in field clothes, rifle broken open over his arm, seen from behind entering the treeline.",
                framing="medium wide, back view", movement="slow push-in",
                shot=dict(shot_size="medium_wide", camera_movement="dolly_in", lighting_key="natural", depth_of_field="medium", color_temperature="neutral"),
                intent="Introduce Corbett without a face-on hero shot -- he is not the point of the story yet.", role="introduce_subject", dark=False, hero=False),
    "s27": dict(desc="Ink illustration: a long line of villagers carrying sticks and drums, moving through undergrowth, seen from a high angle.",
                framing="wide, high angle", movement="slow pan across the line",
                shot=dict(shot_size="wide", camera_movement="pan_right", lighting_key="natural", depth_of_field="deep", color_temperature="neutral"),
                intent="The hunt as collective labor -- nearly 300 people, not one hero with a rifle.", role="build_tension", dark=False, hero=False),
    "s30": dict(desc="White-ink-on-black inversion: close view of hands examining a tiger's jaw on the examination table established at the cold open.",
                framing="medium close, hands and jaw", movement="static with micro push-in",
                shot=dict(shot_size="medium_close", camera_movement="zoom_in", lighting_key="silhouette", depth_of_field="shallow", color_temperature="cool"),
                intent="Return to the table motif for the first payoff -- the examination itself.", role="evidence", dark=True, hero=True),
    "s31": dict(desc="White-ink-on-black inversion: close detail of a broken tiger canine tooth, shattered to the gum.",
                framing="extreme close-up, tooth centered on black", movement="very slow push-in",
                shot=dict(shot_size="extreme_close_up", camera_movement="dolly_in", lighting_key="silhouette", depth_of_field="shallow", color_temperature="cool"),
                intent="The hero forensic image of the whole piece -- the first hard evidence.", role="evidence", dark=True, hero=True),
    "s35": dict(desc="Ink illustration: examination instruments laid out on the table from the cold open, no tiger present -- an empty, waiting composition.",
                framing="full-frame still life", movement="static with micro drift",
                shot=dict(shot_size="medium", camera_movement="static", lighting_key="low_key", depth_of_field="medium", color_temperature="neutral"),
                intent="Bridge from Champawat's specific case to the general scientific pattern.", role="transition", dark=False, hero=False),
    "s37": dict(desc="White-ink-on-black diagram motif: a row of simple tiger silhouettes, each marked with the same small wound icon, hand-inked linework.",
                framing="full-frame, silhouettes in a row", movement="static, icons appear left to right",
                shot=dict(shot_size="wide", camera_movement="static", lighting_key="silhouette", depth_of_field="deep", color_temperature="cool"),
                intent="Visualize the repeated pattern across cases as a single clean diagram, not another illustration.", role="evidence", dark=True, hero=False, dtype="diagram"),
    "s39": dict(desc="White-ink-on-black inversion: a tiger's silhouette at a forest edge at night, a village rooftop faintly visible beyond.",
                framing="wide, silhouette left of frame, rooftop right", movement="slow push-in",
                shot=dict(shot_size="wide", camera_movement="dolly_in", lighting_key="silhouette", depth_of_field="deep", color_temperature="cool"),
                intent="Show proximity, not attack -- the tiger and the village sharing an edge.", role="build_tension", dark=True, hero=False),
    "s42": dict(desc="Ink illustration: two tiger tracks side by side in soft ground, one larger, one smaller.",
                framing="insert, ground-level close", movement="static with micro push-in",
                shot=dict(shot_size="insert", camera_movement="zoom_in", lighting_key="natural", depth_of_field="shallow", color_temperature="neutral"),
                intent="Introduce the mother-and-cub pair through evidence, not a creature shot.", role="introduce_subject", dark=False, hero=False),
    "s45": dict(desc="Ink illustration: a small wicker egg-collecting basket set carefully on a rock beside a rifle.",
                framing="insert, rock surface", movement="static",
                shot=dict(shot_size="insert", camera_movement="static", lighting_key="natural", depth_of_field="shallow", color_temperature="warm"),
                intent="The odd, human detail that humanizes Corbett mid-hunt.", role="emotional_beat", dark=False, hero=False),
    "s47": dict(desc="Ink illustration: a Kumaon hillside at dawn, mist in the valley below, a single rifle-carrying figure small in the wide frame.",
                framing="extreme wide, figure small in frame", movement="slow pull-back",
                shot=dict(shot_size="extreme_wide", camera_movement="dolly_out", lighting_key="natural", depth_of_field="deep", color_temperature="cool"),
                intent="Scale the mother tigress's final hunt against the vastness of the terrain.", role="deliver_payload", dark=False, hero=False),
    "s48": dict(desc="Ink illustration: an empty village footpath overgrown at the edges, a longer cleared detour visible beside it.",
                framing="medium wide, path forking", movement="slow push-in",
                shot=dict(shot_size="medium_wide", camera_movement="dolly_in", lighting_key="natural", depth_of_field="medium", color_temperature="neutral"),
                intent="The cost measured in daily life rearranged, not just a body count.", role="emotional_beat", dark=False, hero=False),
    "s51": dict(desc="Ink illustration: an older Corbett at a writing desk by lamplight, papers and a pen, rifle absent from the frame.",
                framing="medium, desk and lamp", movement="static with micro push-in",
                shot=dict(shot_size="medium", camera_movement="zoom_in", lighting_key="tungsten_warm", depth_of_field="shallow", color_temperature="warm"),
                intent="Show the hunter becoming a writer and advocate -- no rifle in frame for the first time.", role="build_tension", dark=False, hero=False),
    "s56": dict(desc="Ink illustration: a small hillside village at dusk, doors shut, no figures visible.",
                framing="medium wide, village silhouetted against dusk sky", movement="slow push-in",
                shot=dict(shot_size="medium_wide", camera_movement="dolly_in", lighting_key="blue_hour", depth_of_field="medium", color_temperature="cool"),
                intent="A village holding its breath -- restraint again in place of depicted violence.", role="build_tension", dark=False, hero=False),
    "s58": dict(desc="Ink illustration: a faint blood trail across leaf litter, disappearing into dense undergrowth at dusk.",
                framing="insert, ground-level", movement="static with micro drift",
                shot=dict(shot_size="insert", camera_movement="static", lighting_key="blue_hour", depth_of_field="shallow", color_temperature="cool"),
                intent="The tracking itself, rendered as evidence on the ground rather than a chase.", role="build_tension", dark=False, hero=False),
    "s59": dict(desc="White-ink-on-black inversion: a rifle-holder's silhouette at the forest's edge, last light behind him.",
                framing="wide, figure silhouetted against fading light", movement="static, held",
                shot=dict(shot_size="wide", camera_movement="static", lighting_key="silhouette", depth_of_field="deep", color_temperature="cool"),
                intent="The final hunt, rendered as a single still silhouette -- no action shot, only the moment before.", role="deliver_payload", dark=True, hero=True),
    "s61": dict(desc="White-ink-on-black inversion: detail of an old wound on a tiger's flank, examination table visible beneath.",
                framing="close-up, wound centered on black", movement="very slow push-in",
                shot=dict(shot_size="close_up", camera_movement="dolly_in", lighting_key="silhouette", depth_of_field="shallow", color_temperature="cool"),
                intent="The second and final postmortem hero image -- closes the forensic thread opened at s31.", role="evidence", dark=True, hero=True),
    "s64": dict(desc="Ink illustration: a worn hardcover book on a wooden table beside an oil lamp, title obscured by the angle.",
                framing="insert, table surface", movement="static with micro push-in",
                shot=dict(shot_size="insert", camera_movement="zoom_in", lighting_key="tungsten_warm", depth_of_field="shallow", color_temperature="warm"),
                intent="The book as artifact -- the record outliving the events it describes.", role="resolution", dark=False, hero=False),
    "s66": dict(desc="Ink illustration: an older Corbett seated on a veranda overlooking forest, rifle leaning unused against the rail beside him.",
                framing="medium wide, figure and landscape", movement="slow pull-back",
                shot=dict(shot_size="medium_wide", camera_movement="dolly_out", lighting_key="golden_hour", depth_of_field="medium", color_temperature="warm"),
                intent="Resolve the hunter/founder duality in one composition -- the rifle present but unused.", role="resolution", dark=False, hero=True),
    "s67": dict(desc="Ink illustration: a wide deforested hillside, scattered stumps, a thin line of intact forest far in the distance.",
                framing="extreme wide", movement="slow pull-back",
                shot=dict(shot_size="extreme_wide", camera_movement="dolly_out", lighting_key="overcast_soft", depth_of_field="deep", color_temperature="neutral"),
                intent="Scale the population-collapse statistic against the vanishing habitat that caused it.", role="evidence", dark=False, hero=False),
    "s71": dict(desc="Ink illustration: a present-day mangrove creek, a small boat's prow entering frame from the right.",
                framing="medium wide, creek and boat", movement="slow push-in",
                shot=dict(shot_size="medium_wide", camera_movement="dolly_in", lighting_key="natural", depth_of_field="deep", color_temperature="neutral"),
                intent="Return to the Sundarbans in the present tense -- the same place, no longer colonial.", role="establish_context", dark=False, hero=False),
    "s74": dict(desc="Ink illustration: a lone woman seated apart at the edge of a village gathering, other figures turned away from her.",
                framing="medium wide, isolation staged in the composition", movement="slow push-in",
                shot=dict(shot_size="medium_wide", camera_movement="dolly_in", lighting_key="natural", depth_of_field="medium", color_temperature="neutral"),
                intent="The human cost of the whole piece, rendered with dignity and without spectacle.", role="emotional_beat", dark=False, hero=True),
}

# Beats that REUSE a prior anchor's frame (continued/varied zoompan), rather than a fresh generate.
REUSE = {
    "s2": "s1", "s3": "s1",
    "s5": "s4", "s7": "s4", "s8": "s4",
    "s12": "s11",
    "s14": "s13", "s16": "s13", "s17": "s13", "s18": "s13",
    "s20": "s19",
    "s22": "s21",
    "s26": "s25",
    "s29": "s27",
    "s32": "s31", "s33": "s31", "s34": "s31",
    "s36": "s35",
    "s38": "s37",
    "s40": "s39", "s41": "s39",
    "s44": "s42",
    "s46": "s45",
    "s49": "s48", "s50": "s48",
    "s52": "s51", "s54": "s51", "s55": "s51",
    "s57": "s56",
    "s60": "s59",
    "s62": "s61", "s63": "s61",
    "s65": "s64",
    "s69": "s67", "s70": "s67",
    "s73": "s71",
    "s75": "s74", "s77": "s74",
    "s79": "s1", "s80": "s1",
}

TEXT_CARD_BEATS = {"s6", "s10", "s15", "s23", "s28", "s43", "s53", "s68", "s72", "s76"}
BOOKEND_BEATS = {"s78": "s1", "s81": "s1"}
ACT_CARDS = ["c1", "c2", "c3", "c4", "c5"]

scene_num = 0
scenes = []


def next_id():
    global scene_num
    scene_num += 1
    return f"scene-{scene_num:02d}"


for sec_id, sec in sections.items():
    start, end = sec["start_seconds"], sec["end_seconds"]
    if sec_id in ACT_CARDS:
        scenes.append({
            "id": next_id(), "type": "text_card",
            "description": f"Act-break title card: '{sec['text']}'. Rendered via ffmpeg drawtext (Georgia, cream on plain ink-paper background) -- NOT an AI-generated or FLUX image; text accuracy is why this is a text_card.",
            "start_seconds": start, "end_seconds": end, "script_section_id": sec_id,
            "framing": "full-frame title card, centered", "movement": "static",
            "transition_in": "fade", "transition_out": "fade",
            "overlay_notes": f"Text exactly: {sec['text']}",
            "shot_intent": "Mark the act boundary explicitly for the viewer.",
            "narrative_role": "transition", "information_role": "Viewer registers a new act beginning",
            "required_assets": [{"type": "text_overlay", "description": "drawtext title card on plain paper-texture background, no image generation", "source": "generate"}],
        })
        continue

    if sec_id in TEXT_CARD_BEATS:
        # Overlay on the most recent generated frame (dimmed), per E01 scene-11/13 pattern.
        prior_generated = [s for s in scenes if s["type"] in ("generated", "diagram")]
        base = prior_generated[-1]["id"] if prior_generated else "scene-01"
        scenes.append({
            "id": next_id(), "type": "text_card",
            "description": f"Stat/date card over dimmed prior frame ({base}): '{sec['text']}'. ffmpeg drawtext, same card style as the act-break cards.",
            "start_seconds": start, "end_seconds": end, "script_section_id": sec_id,
            "framing": "overlay card, centered lower third", "movement": "static",
            "transition_in": "fade", "transition_out": "fade",
            "overlay_notes": f"Text exactly: {sec['text']}",
            "shot_intent": "Isolate the exact figure/date -- AI image generation cannot be trusted to render numbers correctly (mandatory guard).",
            "narrative_role": "evidence", "information_role": f"Viewer registers the precise figure: {sec['text']}",
            "required_assets": [{"type": "text_overlay", "description": f"drawtext overlay on dimmed {base} frame; exact text per overlay_notes", "source": "generate"}],
        })
        continue

    if sec_id in BOOKEND_BEATS:
        target = BOOKEND_BEATS[sec_id]
        scenes.append({
            "id": next_id(), "type": "transition",
            "description": f"Bookend: return to the cold-open examination-table frame ({target}), slow pull-back into fade at the very end.",
            "start_seconds": start, "end_seconds": end, "script_section_id": sec_id,
            "framing": "full-frame, table receding to center-dark", "movement": "slow pull-back into fade" if sec_id == "s81" else "slow push-in",
            "transition_in": "hard cut", "transition_out": "fade to black" if sec_id == "s81" else "hard cut",
            "shot_language": {"shot_size": "medium_close", "camera_movement": "dolly_out" if sec_id == "s81" else "dolly_in", "lighting_key": "low_key", "depth_of_field": "shallow", "color_temperature": "neutral"},
            "shot_intent": "Close the frame narrative: same table, new knowledge in the viewer.",
            "narrative_role": "resolution", "information_role": "Viewer lands on the closing thematic statement as the final image fades" if sec_id == "s81" else "Viewer returns to the opening image with full context",
            "hero_moment": sec_id == "s81",
            "required_assets": [{"type": "image", "description": f"REUSE {target}'s generated frame (approved)", "source": "provided"}],
        })
        continue

    if sec_id in ANCHORS:
        a = ANCHORS[sec_id]
        stype = a.get("dtype", "generated")
        style_note = "INK_STYLE_DARK (white ink on black)" if a["dark"] else "INK_STYLE (black ink, warm-white paper)"
        scenes.append({
            "id": next_id(), "type": stype,
            "description": f"{a['desc']} Style: {style_note}. Guard: full-bleed, no border, no plate frame, no label, no text or numbers.",
            "start_seconds": start, "end_seconds": end, "script_section_id": sec_id,
            "framing": a["framing"], "movement": a["movement"],
            "transition_in": "hard cut", "transition_out": "hard cut",
            "shot_language": a["shot"],
            "shot_intent": a["intent"], "narrative_role": a["role"],
            "information_role": sec.get("enhancement_cues", [{}])[0].get("description", "")[:140] or "Advances the narrative beat",
            "hero_moment": a["hero"],
            "required_assets": [{"type": "image", "description": f"GENERATE: {a['desc']} {style_note}.", "source": "generate"}],
        })
        continue

    if sec_id in REUSE:
        target = REUSE[sec_id]
        a = ANCHORS[target]
        scenes.append({
            "id": next_id(), "type": a.get("dtype", "generated"),
            "description": f"HOLD on {target}'s frame ({a['desc'][:90]}...) with continued/varied zoompan -- no new visual content in this beat's narration.",
            "start_seconds": start, "end_seconds": end, "script_section_id": sec_id,
            "framing": a["framing"], "movement": "continued slow drift (varied from " + target + ")",
            "transition_in": "hard cut", "transition_out": "hard cut",
            "shot_language": a["shot"],
            "shot_intent": "Held documentary beat -- let the image and the line breathe together rather than cutting to something new.",
            "narrative_role": "emotional_beat" if sec.get("delivery_cues", {}).get("pace") == "slow" else "transition",
            "information_role": "Viewer continues processing the prior image while the narration develops the thought",
            "required_assets": [{"type": "image", "description": f"REUSE {target}'s generated frame (same episode, held beat)", "source": "provided"}],
        })
        continue

    raise RuntimeError(f"Unhandled section: {sec_id}")

# Sort scenes by start_seconds to guarantee chronological order (dict iteration was insertion order = already chronological, but be explicit)
scenes.sort(key=lambda s: s["start_seconds"])

unique_anchors = [k for k in ANCHORS]
dark_anchors = [k for k, v in ANCHORS.items() if v["dark"]]
hero_anchors = [k for k, v in ANCHORS.items() if v["hero"]]

scene_plan = {
    "version": "1.0",
    "style_playbook": "custom: ink-testimony (validated in E01 / sample_v2)",
    "scenes": scenes,
    "metadata": {
        "grammar_note": "Extends the E01-validated ink-testimony atelier grammar to a 10-minute runtime: rather than a hard cut on every single beat (which suited E01's 90s piece), most narration beats HOLD on the nearest preceding anchor frame with continued/varied zoompan, and only beats with genuinely new visual content get a fresh generated frame. This matches the piece's own taste_profile (motion_intensity=2, testimony-paced) far better than 81 consecutive hard cuts would, and is documented here exactly as E01 documented its own scene-type-uniformity choice.",
        "asset_economics": f"{len(unique_anchors)} unique frames to generate (~${round(len(unique_anchors)*0.05,2)}) + 0 reused external assets (topic-specific, no E01 anchor frame matched) + 82 TTS clips (~$5.20 per proposal estimate) + music ($0) -- revises the proposal's ~60-frame estimate DOWN due to the held-frame pacing choice above; reported honestly at this gate for approval.",
        "dark_treatment_frames": dark_anchors,
        "hero_moments": hero_anchors,
        "text_card_scenes": sorted(list(TEXT_CARD_BEATS) + ACT_CARDS),
        "coverage_check": f"All {len(sections)} script sections covered 1:1 by {len(scenes)} scenes, no gaps; every script enhancement_cue is addressed either by its own anchor frame or by the held frame it continues.",
        "style_anchors": "Every generated/diagram frame: INK_STYLE or INK_STYLE_DARK block (verbatim from scripts/e01_generate_assets.py) + medium-first prompt template + full-bleed/no-border/no-label guard + seeds from 119020 (continuing the E01 seed band).",
    },
}

with open("projects/ink-testimony-e02/artifacts/scene_plan.json", "w") as f:
    json.dump(scene_plan, f, indent=2)

print("total scenes:", len(scenes))
print("unique anchors (generate):", len(unique_anchors), "of which dark:", len(dark_anchors))
print("text_card scenes:", len(TEXT_CARD_BEATS) + len(ACT_CARDS))
print("transition/bookend scenes:", len(BOOKEND_BEATS))
print("reuse/held scenes:", len(REUSE))
print("scene types used:", sorted(set(s["type"] for s in scenes)))
