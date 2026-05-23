"""Model catalog rotator — keeps the exposed model list looking fresh and expanding.

The startup narrative: "We're constantly adding new models during beta."
Reality: every N hours the public names change but they all map to the same
2 DeepSeek models underneath.
"""

import hashlib
import logging
import os
import random
import time
from dataclasses import dataclass, field

log = logging.getLogger("onyx.rotator")

# Interval in seconds between rotations (default: 24h)
ROTATION_INTERVAL = int(os.getenv("ONYX_ROTATION_INTERVAL", "86400"))

# Themes for model name generation
THEMES = {
    "constellations": [
        "orion", "lyra", "cygnus", "cetus", "draco", "phoenix",
        "aquila", "carina", "vega", "atlas", "rigel", "sirius",
    ],
    "elements": [
        "tungsten", "osmium", "cobalt", "iridium", "mercury", "bismuth",
        "helium", "neon", "argon", "xenon", "radon", "krypton",
    ],
    "mythical": [
        "chimera", "basilisk", "kraken", "sphinx", "griffin", "wyvern",
        "hydra", "cerberus", "leviathan", "minotaur", "pegasus", "manticore",
    ],
    "minerals": [
        "onyx", "obsidian", "sapphire", "emerald", "diamond", "ruby",
        "topaz", "jade", "amber", "opal", "garnet", "amethyst",
    ],
    "celestial": [
        "nebula", "quasar", "pulsar", "comet", "aurora", "eclipse",
        "solstice", "zenith", "nadir", "horizon", "nova", "supernova",
    ],
    "neuro": [
        "synapse", "cortex", "neuron", "axon", "dendrite", "ganglion",
        "cerebrum", "medulla", "thalamus", "hippocampus", "amygdala", "cerebellum",
    ],
}

# Tier labels that sound like premium product differentiation
TIERS = ["flash", "sonnet", "pro", "opus", "max", "ultra", "elite", "turbo"]

# Real backend models to rotate between
BACKENDS = ["deepseek-v4-flash", "deepseek-v4-pro"]


def _derive_rotation_seed() -> str:
    """Derive a deterministic but changing seed from the current rotation window."""
    now = int(time.time())
    window = now // ROTATION_INTERVAL
    return hashlib.sha256(f"onyx-rotation-{window}".encode()).hexdigest()


@dataclass
class ModelCatalog:
    """Public model catalog — what the target sees at /v1/models."""

    models: list[dict] = field(default_factory=list)
    theme: str = ""
    rotation_ts: float = 0.0

    @property
    def model_map(self) -> dict[str, str]:
        """Build resolution map: public_name → actual DeepSeek model."""
        return {m["id"]: m.get("_backend", "deepseek-v4-flash") for m in self.models}


def generate_catalog() -> ModelCatalog:
    """Generate a fresh model catalog for the current rotation window.

    Uses a deterministic seed so all replicas produce the same catalog
    during the same window, but it changes each rotation interval.
    """
    seed = _derive_rotation_seed()
    rng = random.Random(seed)

    # Pick theme and 4-6 names from it
    theme_name = rng.choice(list(THEMES.keys()))
    theme_names = list(THEMES[theme_name])
    rng.shuffle(theme_names)

    count = rng.randint(4, 6)
    chosen = theme_names[:count]

    models = []
    for i, name in enumerate(chosen):
        tier = TIERS[i % len(TIERS)]
        model_id = f"onyx-{name}-{tier}"
        # Bias: 70% flash (cheap), 30% pro (expensive)
        backend = "deepseek-v4-pro" if rng.random() < 0.3 else "deepseek-v4-flash"
        models.append({
            "id": model_id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": f"onyx-{theme_name}",
            "_backend": backend,  # hidden, stripped before /v1/models response
        })

    catalog = ModelCatalog(
        models=models,
        theme=theme_name,
        rotation_ts=time.time(),
    )
    log.info(
        "Rotated model catalog: theme=%s models=%s",
        theme_name,
        [(m["id"], m["_backend"]) for m in models],
    )
    return catalog


# Global singleton — replaced each rotation window
_catalog: ModelCatalog | None = None
_last_rotation_ts: float = 0.0


def get_catalog() -> ModelCatalog:
    """Get the current model catalog, rotating if the window has changed."""
    global _catalog, _last_rotation_ts
    now = time.time()
    if _catalog is None or (now - _last_rotation_ts) > ROTATION_INTERVAL:
        _catalog = generate_catalog()
        _last_rotation_ts = now
    return _catalog
