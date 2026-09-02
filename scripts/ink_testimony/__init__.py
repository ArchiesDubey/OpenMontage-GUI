"""Standardised Ink & Testimony render pipeline.

Replaces the per-episode bespoke scripts (eNN_sample_assets / eNN_generate_assets
/ eNN_regen_failures / eNN_compose / eNN_recut) with two artifact-driven modules:

    python -m scripts.ink_testimony.assets  --project projects/ink-testimony-eNN --mode batch
    python -m scripts.ink_testimony.compose --project projects/ink-testimony-eNN

Everything episode-specific lives in the artifacts:
  artifacts/scene_plan.json   frame prompts, hold/reuse (source=="provided" +
                              "REUSE <anchor>"), zoompan mode (movement), scene order
  artifacts/script.json       narration provider_text, card text,
                              metadata.dark_register_beats
  ink_config.json             seed band start, subtitle mode, timing constants
                              (all optional; defaults come from styles/ink-testimony.yaml)
  cut_plan.json  (optional)   detail_frames per beat + date_cards, for the 2-6s
                              sub-shot slicing; absent => crops-only, still valid

Scope: the E02/E03 grammar (every beat -- including act cards -- has its own
narration clip; uniform lead/clip/gap/tail; no split-card branch). E01's 99s
split-card timeline is not covered and does not need to be.
"""
__all__ = ["common", "assets", "compose"]
