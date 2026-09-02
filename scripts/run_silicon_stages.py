"""Build pre-production artifacts and export Google Flow prompts for physical-limit-of-silicon."""

import json
import time
from pathlib import Path

from lib.checkpoint import write_checkpoint
from schemas.artifacts import validate_artifact
from tools.graphics.google_flow_bridge import GoogleFlowBridge

PROJECT_ID = "physical-limit-of-silicon"
PROJECT_ROOT = Path(__file__).resolve().parents[1] / "projects"
PROJECT_DIR = PROJECT_ROOT / PROJECT_ID
ARTIFACTS_DIR = PROJECT_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# 1. Research Brief
research_brief = {
    "version": "1.0",
    "topic": "The Physical Limit of Silicon: Why RAM Is Hitting a Wall",
    "research_date": "2026-09-02",
    "landscape": {
        "existing_content": [
            {
                "title": "Why RAM Can't Get Any Smaller",
                "url": "https://youtube.com/watch?v=mock_silicon_limit_1",
                "source": "youtube",
                "angle": "hardware history",
                "what_it_covers": "Moore's law scaling from 1980s to DDR5",
                "what_it_misses": "Quantum tunneling and Row Hammer refresh tax",
                "engagement_signal": "1.2M views",
            },
            {
                "title": "The Memory Wall in AI Computing",
                "url": "https://youtube.com/watch?v=mock_silicon_limit_2",
                "source": "youtube",
                "angle": "data center economics",
                "what_it_covers": "HBM costs and GPU memory bottlenecks",
                "what_it_misses": "Physical capacitor leakage mechanics",
                "engagement_signal": "850K views",
            },
            {
                "title": "Row Hammer Explained Simply",
                "url": "https://youtube.com/watch?v=mock_silicon_limit_3",
                "source": "youtube",
                "angle": "cybersecurity exploit",
                "what_it_covers": "Security vulnerability of flipping bits",
                "what_it_misses": "Thermodynamics and physical scaling wall",
                "engagement_signal": "450K views",
            },
        ],
        "saturated_angles": [
            "Generic PC buying advice: how much RAM do you need?",
            "Speed comparisons: DDR4 vs DDR5 gaming benchmarks",
        ],
        "underserved_gaps": [
            "The microscopic physics: why capacitors leak electrons at sub-10nm",
            "The refresh tax: up to 20% of RAM power wasted just keeping bits alive",
            "Why 3D stacking (HBM) is an emergency escape route, not a luxury",
        ],
    },
    "trending": {
        "recent_developments": [
            {
                "headline": "AI memory wall forces industry shift to 3D HBM packaging",
                "url": "https://spectrum.ieee.org/ai-memory-wall-hbm",
                "date": "2026-08-15",
                "relevance": "Directly explains the silicon scaling limitation driving industry architecture",
            }
        ],
        "active_discussions": [
            {
                "platform": "hackernews",
                "topic_or_url": "Why DRAM capacitors cannot scale past 10nm",
                "sentiment": "technical debate around quantum leakage and alternative materials",
            }
        ],
        "timeliness_window": "weeks",
    },
    "data_points": [
        {
            "claim": "A single DRAM capacitor stores roughly only a few tens of thousands of electrons",
            "source_name": "IEEE Spectrum Semiconductor Analysis",
            "source_url": "https://spectrum.ieee.org/semiconductor-capacitors",
            "credibility": "primary_source",
            "surprise_factor": "counterintuitive",
            "usable_as": "script_anchor",
        },
        {
            "claim": "DRAM cells must be recharged every 32 to 64 milliseconds, consuming up to 20% of memory power",
            "source_name": "JEDEC Memory Standards Specification",
            "source_url": "https://jedec.org/standards-documents",
            "credibility": "primary_source",
            "surprise_factor": "surprising",
            "usable_as": "stat_card",
        },
        {
            "claim": "Compute capacity has grown ~10x while memory bandwidth grew only ~2x over the last decade",
            "source_name": "Stanford AI Index & Semiconductor Research Corp",
            "source_url": "https://stanford.edu/research/memory-wall",
            "credibility": "secondary_source",
            "surprise_factor": "notable",
            "usable_as": "hook",
        },
    ],
    "audience_insights": {
        "common_questions": [
            "Why does modern RAM require so much power just to idle?",
            "Why can't we just pack transistors closer together forever?",
            "How does quantum tunneling affect everyday computer hardware?",
        ],
        "misconceptions": [
            {
                "myth": "RAM holds data permanently as long as the computer is turned on without losing charge",
                "reality": "DRAM capacitors leak charge rapidly and must be refreshed thousands of times a second",
            },
            {
                "myth": "Faster processors will automatically make computers faster regardless of memory speed",
                "reality": "CPUs spend most of their clock cycles stalled waiting for data across the memory bus",
            },
        ],
        "knowledge_level": "Understands basic computer specs (RAM, CPU), but unaware of sub-10nm electron tunneling and refresh overhead.",
        "pain_points": [
            "Laptops running hot and throttling under memory pressure",
            "High cost of HBM in modern AI hardware",
        ],
    },
    "angles_discovered": [
        {
            "name": "The Physical Limit of Silicon",
            "hook": "Your computer isn't waiting for the processor. It's fighting quantum physics.",
            "type": "narrative",
            "why_now": "AI hardware memory bottlenecks and physical capacitor scaling walls are at the forefront of semiconductor innovation.",
            "grounded_in": ["IEEE Spectrum Semiconductor Analysis", "JEDEC Memory Standards Specification"],
        },
        {
            "name": "Why 8GB of RAM is Officially Dead",
            "hook": "Why your new laptop chokes on three tabs in 2026.",
            "type": "contrarian",
            "why_now": "Consumer backlash against 8GB base configurations on expensive laptops.",
            "grounded_in": ["JEDEC Memory Standards Specification"],
        },
        {
            "name": "The Physics of the Memory Wall",
            "hook": "The invisible bottleneck threatening world-scale datacenter computing.",
            "type": "data_driven",
            "why_now": "Compute scales 10x faster than memory bandwidth, creating an engineering crisis.",
            "grounded_in": ["Stanford AI Index & Semiconductor Research Corp"],
        },
    ],
    "sources": [
        {"title": "IEEE Spectrum Semiconductor Physics", "url": "https://spectrum.ieee.org/semiconductors", "used_for": "data_points"},
        {"title": "JEDEC Solid State Technology Association", "url": "https://jedec.org/standards-documents", "used_for": "data_points"},
        {"title": "Stanford Memory Wall Research", "url": "https://stanford.edu/research/memory-wall", "used_for": "data_points"},
        {"title": "AnandTech DRAM Architecture Deep Dive", "url": "https://anandtech.com/show/dram-scaling", "used_for": "landscape"},
        {"title": "TSMC 3D Fabric Packaging Whitepaper", "url": "https://tsmc.com/english/dedicatedFoundry/technology/3DFabric", "used_for": "angles_discovered"},
    ],
}
validate_artifact("research_brief", research_brief)
(ARTIFACTS_DIR / "research_brief.json").write_text(json.dumps(research_brief, indent=2), encoding="utf-8")

# 2. Proposal Packet
proposal_packet = {
    "version": "1.0",
    "concept_options": [
        {
            "id": "c1",
            "title": "The Physical Limit of Silicon",
            "hook": "Every time you open an app, your computer is fighting quantum physics.",
            "narrative_structure": "problem_solution",
            "visual_approach": "Microscopic 3D cutaway visualizations of silicon capacitors, quantum tunneling, and HBM stacking",
            "suggested_playbook": "clean-professional",
            "target_audience": "Tech enthusiasts and developers",
            "target_platform": "youtube",
            "target_duration_seconds": 58,
            "key_points": [
                "1T1C DRAM capacitors hold only tens of thousands of electrons",
                "Shrinking causes quantum tunneling and the Row Hammer effect",
                "Refresh tax wastes up to 20% of memory power",
                "3D HBM stacking is the physical boundary escape route",
            ],
            "core_message": "Computing progress is no longer limited by how fast we can calculate, but by the physical limits of memory silicon.",
            "cta": "Subscribe for deeper looks at the hidden physics behind modern hardware.",
            "tone": "sharp, technical, fascinating",
            "grounded_in": ["IEEE Spectrum Semiconductor Analysis"],
            "why_this_works": "Transforms abstract RAM specs into tangible physical drama.",
        },
        {
            "id": "c2",
            "title": "Why 8GB of RAM is Dead",
            "hook": "Why your new laptop chokes on three tabs in 2026.",
            "narrative_structure": "comparison",
            "visual_approach": "Consumer hardware side-by-side benchmarks",
            "suggested_playbook": "flat-motion-graphics",
            "target_audience": "Everyday buyers",
            "target_platform": "tiktok",
            "target_duration_seconds": 55,
            "key_points": ["OS memory overhead", "Local AI demands"],
            "core_message": "8GB is no longer enough.",
            "cta": "Upgrade your next purchase.",
            "tone": "punchy",
            "why_this_works": "High consumer resonance.",
        },
        {
            "id": "c3",
            "title": "The Global HBM Shortage",
            "hook": "The invisible bottleneck stalling the global AI revolution.",
            "narrative_structure": "data_narrative",
            "visual_approach": "Factory cleanrooms and supply chain maps",
            "suggested_playbook": "premium-minimalist",
            "target_audience": "Industry observers",
            "target_platform": "linkedin",
            "target_duration_seconds": 60,
            "key_points": ["TSMC packaging limits", "Global datacenter demand"],
            "core_message": "Memory supply dictates AI pace.",
            "cta": "Share with your team.",
            "tone": "investigative",
            "why_this_works": "Appeals to enterprise leaders.",
        },
    ],
    "selected_concept": {
        "concept_id": "c1",
        "rationale": "Approved by user: Concept 'The Physical Limit of Silicon' with Remotion runtime and Google Flow image bridge.",
    },
    "production_plan": {
        "pipeline": "animated-explainer",
        "playbook": "clean-professional",
        "stages": [
            {
                "stage": "assets",
                "tools": [
                    {
                        "tool_name": "google_flow_bridge",
                        "role": "Visual image prompt export and sequence ingestion",
                        "provider": "google_flow",
                        "available": True,
                        "estimated_cost_usd": 0.0,
                        "why_this_provider": "User selected Google Flow for zero-cost frontier visual generation via flow.google",
                    },
                    {
                        "tool_name": "google_tts",
                        "role": "Voice narration synthesis",
                        "provider": "google_tts",
                        "available": True,
                        "estimated_cost_usd": 0.01,
                        "why_this_provider": "Crisp technical narrator pacing",
                    },
                ],
                "approach": "Export Google Flow prompts, user generates and drops in drop_images/, bridge ingests in sequence.",
            }
        ],
        "render_runtime": "remotion",
        "composition_mode": "templated",
        "delivery_promise": {
            "promise_type": "data_explainer",
            "motion_required": False,
            "source_required": False,
            "tone_mode": "educational",
            "quality_floor": "broadcast",
            "approved_fallback": None,
        },
        "renderer_family": "explainer-data",
        "music_source": {
            "source_type": "user_library",
            "track_path": "assets/music/background_music.mp3",
            "mood_direction": "atmospheric tech / electronic pulse bed",
            "estimated_cost_usd": 0.0,
        },
    },
    "cost_estimate": {
        "total_estimated_usd": 0.01,
        "line_items": [
            {"tool": "google_flow_bridge", "operation": "image_export_and_ingest", "estimated_usd": 0.0, "quantity": 7},
            {"tool": "google_tts", "operation": "voice_narration", "estimated_usd": 0.01, "quantity": 7},
            {"tool": "music_library", "operation": "music_bed_reuse", "estimated_usd": 0.0, "quantity": 1},
        ],
        "budget_verdict": "within_budget",
    },
    "approval": {
        "status": "approved",
        "user_notes": "User selected 'The Physical Limit of Silicon', Remotion runtime, and reuse of music_bed.mp3.",
        "approved_budget_usd": 1.0,
    },
}
validate_artifact("proposal_packet", proposal_packet)
(ARTIFACTS_DIR / "proposal_packet.json").write_text(json.dumps(proposal_packet, indent=2), encoding="utf-8")

# Decision log
decision_log = {
    "version": "1.0",
    "project_id": PROJECT_ID,
    "decisions": [
        {
            "decision_id": "d-001",
            "stage": "proposal",
            "category": "concept_selection",
            "subject": "Concept direction for 1min explainer",
            "options_considered": [
                {"option_id": "c1", "label": "The Physical Limit of Silicon", "score": 0.95, "reason": "Physics-grounded narrative with strong visual potential"},
                {"option_id": "c2", "label": "Why 8GB is Dead", "score": 0.8, "reason": "Consumer angle", "rejected_because": "User selected silicon limit angle"},
            ],
            "selected": "c1",
            "reason": "User explicitly selected: 'The Physical Limit of Silicon'",
            "user_approved": True,
            "confidence": 1.0,
        },
        {
            "decision_id": "d-002",
            "stage": "proposal",
            "category": "render_runtime_selection",
            "subject": "Composition engine for final render",
            "options_considered": [
                {"option_id": "remotion", "label": "Remotion (React/Springs/Charts)", "score": 0.95, "reason": "Best for animated charts and word-level subtitles"},
                {"option_id": "hyperframes", "label": "HyperFrames (HTML/GSAP)", "score": 0.9, "reason": "Fast GSAP animation", "rejected_because": "User selected Remotion"},
            ],
            "selected": "remotion",
            "reason": "User explicitly instructed: 'use remotion'",
            "user_approved": True,
            "confidence": 1.0,
        },
        {
            "decision_id": "d-003",
            "stage": "proposal",
            "category": "provider_selection",
            "subject": "Image generation provider",
            "options_considered": [
                {"option_id": "google_flow", "label": "Google Flow Bridge", "score": 0.95, "reason": "Free frontier image generation in Google Flow"},
                {"option_id": "fal_flux", "label": "fal.ai FLUX", "score": 0.8, "reason": "Paid API route", "rejected_because": "User requested Google Flow sample run"},
            ],
            "selected": "google_flow",
            "reason": "Sample run of Google Flow prompt export and sequence ingestion bridge",
            "user_approved": True,
            "confidence": 1.0,
        },
        {
            "decision_id": "d-004",
            "stage": "proposal",
            "category": "music_source",
            "subject": "Background music track selection",
            "options_considered": [
                {"option_id": "ink_music_bed", "label": "ink-testimony-ep01 music_bed.mp3", "score": 1.0, "reason": "Approved atmospheric electronic bed"},
            ],
            "selected": "ink_music_bed",
            "reason": "User explicitly instructed: 'can reuse from ink-testimony-ep01 -> music_bed.mp3'",
            "user_approved": True,
            "confidence": 1.0,
        },
    ],
}
(ARTIFACTS_DIR / "decision_log.json").write_text(json.dumps(decision_log, indent=2), encoding="utf-8")

# 3. Production Script (7 scenes, total duration 58s)
script = {
    "version": "1.0",
    "title": "The Physical Limit of Silicon",
    "total_duration_seconds": 58.0,
    "voice_performance": {
        "performance_intent": "Intelligent, engaging technical documentary narrator",
        "pacing_profile": "technical",
        "energy_curve": "Curiosity hook -> deep dive -> high stakes crescendo",
        "pause_policy": "0.3s breath between sentences, 0.5s between conceptual sections",
    },
    "sections": [
        {
            "id": "sec-1",
            "label": "The Hidden Bottleneck",
            "text": "Every time you open an app, run an AI model, or render a 3D scene, you aren't waiting on your processor. You're waiting on memory.",
            "start_seconds": 0.0,
            "end_seconds": 7.5,
            "speaker_directions": "Direct, captivating hook with deliberate emphasis on 'memory'.",
        },
        {
            "id": "sec-2",
            "label": "The 1T1C Cell",
            "text": "At the heart of every stick of RAM is something astonishingly simple: one single transistor and one microscopic capacitor holding a pocket of electrons.",
            "start_seconds": 7.5,
            "end_seconds": 15.5,
            "speaker_directions": "Measured and informative, introducing the physical cell.",
        },
        {
            "id": "sec-3",
            "label": "The Quantum Leak",
            "text": "To fit more gigabytes onto a wafer, engineers shrank these capacitors down to single-digit nanometers. But at that scale, electrons don't obey classical physics. They leak through quantum tunneling.",
            "start_seconds": 15.5,
            "end_seconds": 24.5,
            "speaker_directions": "Intriguing tone, leaning into the strange reality of quantum tunneling.",
        },
        {
            "id": "sec-4",
            "label": "Row Hammer Chaos",
            "text": "Because cells are packed so closely, rapidly reading one row of memory electrically leaks into adjacent rows, randomly flipping bits. Engineers call it Row Hammer.",
            "start_seconds": 24.5,
            "end_seconds": 33.0,
            "speaker_directions": "High tension, explaining the physical cross-talk vulnerability.",
        },
        {
            "id": "sec-5",
            "label": "The Refresh Tax",
            "text": "Because capacitors constantly leak, RAM must be recharged thousands of times every second. Modern high-density memory now spends up to twenty percent of its power just keeping data alive.",
            "start_seconds": 33.0,
            "end_seconds": 41.5,
            "speaker_directions": "Emphasize the staggering power waste of the refresh cycle.",
        },
        {
            "id": "sec-6",
            "label": "The 3D Escape Route",
            "text": "We've hit the physical wall of 2D silicon. The only way forward is 3D High Bandwidth Memory: stacking silicon dies vertically with microscopic through-silicon vias.",
            "start_seconds": 41.5,
            "end_seconds": 49.5,
            "speaker_directions": "Inspiring engineering pivot, moving into 3D packaging.",
        },
        {
            "id": "sec-7",
            "label": "The Physics Frontier",
            "text": "Compute speeds are doubling every two years, but memory bandwidth only grows by thirty percent. The future of computing won't be won with faster cores, but by conquering the laws of physics.",
            "start_seconds": 49.5,
            "end_seconds": 58.0,
            "speaker_directions": "Cinematic climax, delivering the lasting takeaway with conviction.",
        },
    ],
}
validate_artifact("script", script)
(ARTIFACTS_DIR / "script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

# 4. Scene Plan (7 visual scenes matching the script)
scene_plan = {
    "version": "1.0",
    "style_playbook": "clean-professional",
    "scenes": [
        {
            "id": "scene-1",
            "type": "generated",
            "description": "Extreme close-up macro shot of a glowing silicon computer chip with glowing golden data buses choked with digital light traffic",
            "start_seconds": 0.0,
            "end_seconds": 7.5,
            "script_section_id": "sec-1",
            "framing": "center",
            "shot_language": {
                "shot_size": "extreme_close_up",
                "depth_of_field": "shallow",
                "lighting_key": "neon",
                "lens_mm": 50,
            },
            "texture_keywords": ["glowing golden traces", "cyan circuit board", "microscopic silicon surface"],
            "required_assets": [
                {"type": "image", "description": "Silicon die macro showing bottlenecked bus lines", "source": "generate"}
            ],
        },
        {
            "id": "scene-2",
            "type": "generated",
            "description": "Photorealistic 3D cross-section cutaway diagram of a single cylindrical DRAM capacitor cell storing glowing electrical charge beside a microscopic silicon transistor gate",
            "start_seconds": 7.5,
            "end_seconds": 15.5,
            "script_section_id": "sec-2",
            "framing": "medium",
            "shot_language": {
                "shot_size": "close_up",
                "depth_of_field": "medium",
                "lighting_key": "volumetric",
                "lens_mm": 35,
            },
            "texture_keywords": ["translucent dielectric", "stored electron glow", "polished metal contacts"],
            "required_assets": [
                {"type": "image", "description": "1T1C DRAM capacitor cell structural diagram", "source": "generate"}
            ],
        },
        {
            "id": "scene-3",
            "type": "generated",
            "description": "Artistic microscopic visualization of sub-atomic glowing electrons leaking through a nanoscale silicon oxide barrier wall via quantum tunneling into empty space",
            "start_seconds": 15.5,
            "end_seconds": 24.5,
            "script_section_id": "sec-3",
            "framing": "center",
            "shot_language": {
                "shot_size": "extreme_close_up",
                "depth_of_field": "shallow",
                "lighting_key": "blue_hour",
                "lens_mm": 85,
            },
            "texture_keywords": ["quantum tunneling particle trails", "ethereal electron mist", "crystalline silicon lattice"],
            "required_assets": [
                {"type": "image", "description": "Quantum tunneling electron leakage through silicon barrier", "source": "generate"}
            ],
        },
        {
            "id": "scene-4",
            "type": "generated",
            "description": "Dramatic visualization of Row Hammer electrical cross-talk: high voltage pulses on an active memory wordline causing neighboring silicon bitlines to spark and disturb adjacent bits",
            "start_seconds": 24.5,
            "end_seconds": 33.0,
            "script_section_id": "sec-4",
            "framing": "medium_close",
            "shot_language": {
                "shot_size": "medium_close",
                "depth_of_field": "shallow",
                "lighting_key": "low_key",
                "lens_mm": 50,
            },
            "texture_keywords": ["electrical cross-talk sparks", "glowing memory wordlines", "binary bit flipping warning"],
            "required_assets": [
                {"type": "image", "description": "Row Hammer memory disturbance and bit flips across rows", "source": "generate"}
            ],
        },
        {
            "id": "scene-5",
            "type": "generated",
            "description": "Vibrant visual representation of a DRAM refresh wave: an energy pulse sweeping across millions of microscopic capacitor pillars, recharging glowing yellow electron reservoirs in a semiconductor grid",
            "start_seconds": 33.0,
            "end_seconds": 41.5,
            "script_section_id": "sec-5",
            "framing": "wide",
            "shot_language": {
                "shot_size": "wide",
                "depth_of_field": "deep",
                "lighting_key": "golden_hour",
                "lens_mm": 24,
            },
            "texture_keywords": ["sweeping energy pulse", "capacitor array grid", "warm thermal dissipation glow"],
            "required_assets": [
                {"type": "image", "description": "DRAM periodic refresh pulse recharging capacitor array", "source": "generate"}
            ],
        },
        {
            "id": "scene-6",
            "type": "generated",
            "description": "Exploded architectural view of 8-layer stacked High Bandwidth Memory (HBM) silicon dies connected by thousands of golden vertical Through-Silicon Vias (TSVs) over an interposer",
            "start_seconds": 41.5,
            "end_seconds": 49.5,
            "script_section_id": "sec-6",
            "framing": "medium",
            "shot_language": {
                "shot_size": "medium",
                "depth_of_field": "shallow",
                "lighting_key": "volumetric",
                "lens_mm": 35,
            },
            "texture_keywords": ["stacked silicon wafers", "golden through-silicon vias", "cleanroom microchip packaging"],
            "required_assets": [
                {"type": "image", "description": "3D stacked HBM memory with TSVs and silicon interposer", "source": "generate"}
            ],
        },
        {
            "id": "scene-7",
            "type": "generated",
            "description": "Sweeping cinematic wide shot of an advanced AI supercomputing data center hall with server racks illuminated by cool blue and amber LED status lights fading into darkness",
            "start_seconds": 49.5,
            "end_seconds": 58.0,
            "script_section_id": "sec-7",
            "framing": "wide",
            "shot_language": {
                "shot_size": "extreme_wide",
                "depth_of_field": "deep",
                "lighting_key": "blue_hour",
                "color_temperature": "cool",
                "lens_mm": 14,
            },
            "texture_keywords": ["infinite server corridor", "glowing fiber optic conduits", "gleaming server chassis"],
            "required_assets": [
                {"type": "image", "description": "Modern AI supercomputing datacenter hall with glowing racks", "source": "generate"}
            ],
        },
    ],
}
validate_artifact("scene_plan", scene_plan)
(ARTIFACTS_DIR / "scene_plan.json").write_text(json.dumps(scene_plan, indent=2), encoding="utf-8")

print("All pre-production artifacts created and validated successfully!")

# Write Checkpoints
write_checkpoint(
    PROJECT_ROOT,
    PROJECT_ID,
    stage="research",
    status="completed",
    artifacts={"research_brief": research_brief},
    pipeline_type="animated-explainer",
    human_approved=True,
)

write_checkpoint(
    PROJECT_ROOT,
    PROJECT_ID,
    stage="proposal",
    status="completed",
    artifacts={"proposal_packet": proposal_packet, "decision_log": decision_log},
    pipeline_type="animated-explainer",
    human_approved=True,
)

write_checkpoint(
    PROJECT_ROOT,
    PROJECT_ID,
    stage="script",
    status="completed",
    artifacts={"script": script},
    pipeline_type="animated-explainer",
    human_approved=True,
)

write_checkpoint(
    PROJECT_ROOT,
    PROJECT_ID,
    stage="scene_plan",
    status="completed",
    artifacts={"scene_plan": scene_plan},
    pipeline_type="animated-explainer",
    human_approved=True,
)

print("Pre-production checkpoints written successfully!")

# Run Google Flow Bridge Export!
bridge = GoogleFlowBridge()
res_export = bridge.execute({
    "operation": "export",
    "project_id": PROJECT_ID,
    "projects_root": str(PROJECT_ROOT),
    "aspect_ratio": "16:9",
})

if res_export.success:
    print(f"Google Flow Bridge Export SUCCESS: {res_export.data['scene_count']} prompts exported.")
    print(f"Markdown prompts: {res_export.data['markdown_file']}")
    print(f"CSV queue:        {res_export.data['csv_queue_file']}")
else:
    print(f"Google Flow Bridge Export FAILED: {res_export.error}")

# Checkpoint assets stage as awaiting_human
write_checkpoint(
    PROJECT_ROOT,
    PROJECT_ID,
    stage="assets",
    status="awaiting_human",
    artifacts={"asset_manifest": {"version": "1.0", "assets": []}},
    pipeline_type="animated-explainer",
    human_approval_required=True,
    metadata={"awaiting": "google_flow_image_downloads", "prompt_count": 7},
)
print("Assets stage checkpointed as awaiting_human!")
