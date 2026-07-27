"""Main Review repository intelligence package.

Sergeant's permanent-officer reviewer is model-free by default. Provider-backed
reasoning is an optional owner-enabled capability, so every Python entrypoint
starts with the model-support enable switch off unless the process supplied an
explicit Sergeant or legacy enable setting before importing this package.
"""
from __future__ import annotations

import os


__all__ = ["__version__"]
__version__ = "0.1.0"


def _apply_model_free_default() -> None:
    """Disable provider calls without overwriting dormant route preferences.

    The compatibility provider layer still uses ``preferred`` / ``auto`` as its
    dormant routing metadata. Those values cannot discover or call a provider
    while ``SERGEANT_CPL_ENABLED`` is false. An owner who explicitly sets the
    new or legacy enable switch to true retains the existing provider-selection
    behavior and may then choose one model or a bounded council.
    """

    explicit_enable = os.getenv("SERGEANT_CPL_ENABLED")
    if explicit_enable is None:
        explicit_enable = os.getenv("SERGEANT_LLM_ENABLED")
    if explicit_enable is None:
        os.environ["SERGEANT_CPL_ENABLED"] = "false"


_apply_model_free_default()
