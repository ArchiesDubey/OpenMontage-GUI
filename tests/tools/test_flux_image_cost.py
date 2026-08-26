"""Regression tests: flux_image cost estimates must scale with resolution.

Bug: estimate_cost returned a flat $0.03 for every non-pro model regardless of
width/height, while fal.ai actually bills flux/dev at $0.025 per megapixel and
flux/schnell at $0.003 per megapixel. A 1216x1344 portrait (~1.63 MP, ~$0.041
real) was under-quoted as $0.03; a schnell batch (8x cheaper than dev) was
over-quoted at the dev rate — distorting video_selector/image_selector cost
scoring and proposal budgets.

Verified against dark-history-channel ep1 actuals: 105 frames @ 1344x768
(~1.03 MP) = $2.70 (~$0.026/frame), confirming exact-MP billing rather than
fal's documented "round up to nearest megapixel".
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.graphics.flux_image import FluxImage


@pytest.fixture
def tool() -> FluxImage:
    return FluxImage()


def test_dev_scales_with_megapixels(tool):
    # 1344x768 = 1.0322 MP x $0.025/MP = $0.02581 -> rounds up to $0.026.
    assert tool.estimate_cost({"model": "flux/dev", "width": 1344, "height": 768}) == 0.026
    assert tool.estimate_cost({"model": "flux/dev", "width": 1024, "height": 1024}) == 0.027


def test_dev_portrait_costs_more_than_landscape_at_same_area_class(tool):
    # The $0.04 the user saw in fal's UI: 1216x1344 = 1.634 MP -> ~$0.041.
    assert tool.estimate_cost({"model": "flux/dev", "width": 1216, "height": 1344}) == 0.041


def test_default_size_matches_schema_defaults(tool):
    schema_w = tool.input_schema["properties"]["width"]["default"]
    schema_h = tool.input_schema["properties"]["height"]["default"]
    assert tool.estimate_cost({"model": "flux/dev"}) == tool.estimate_cost(
        {"model": "flux/dev", "width": schema_w, "height": schema_h}
    )


def test_pro_stays_flat_per_image(tool):
    assert tool.estimate_cost({"model": "flux-pro/v1.1", "width": 512, "height": 512}) == 0.05
    assert tool.estimate_cost({"model": "flux-pro/v1.1", "width": 2048, "height": 2048}) == 0.05


def test_schnell_bills_at_its_own_rate_not_dev_rate(tool):
    # 1024x1024 @ $0.003/MP = $0.00315 -> rounds up to $0.004 (not dev's 0.027).
    assert tool.estimate_cost({"model": "flux/schnell", "width": 1024, "height": 1024}) == 0.004


def test_estimates_never_underquote(tool):
    import math

    for model, rate in (("flux/dev", 0.025), ("flux/schnell", 0.003)):
        for w, h in ((512, 512), (1024, 768), (1344, 768), (1216, 1344), (2048, 1152)):
            mp = (w * h) / 1_000_000
            actual = mp * rate
            est = tool.estimate_cost({"model": model, "width": w, "height": h})
            assert est >= actual - 1e-9
            assert abs(est * 1000 - math.ceil(est * 1000)) < 1e-9  # tenth-cent grid


def test_no_inputs_path_matches_schema_default_model(tool):
    # Mirrors tests/tools/test_provider_model_defaults.py governance: omitting
    # `model` must price identically to the schema default (flux-pro/v1.1).
    schema_default = tool.input_schema["properties"]["model"]["default"]
    assert tool.estimate_cost({}) == tool.estimate_cost({"model": schema_default})
