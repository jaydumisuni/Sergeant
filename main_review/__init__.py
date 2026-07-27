"""Main Review repository intelligence package.

Sergeant's permanent-officer reviewer is model-free by default.  Provider-backed
reasoning is an optional owner-enabled capability, so every Python entrypoint
starts with model support disabled unless the process supplied an explicit
Sergeant or legacy enable setting before importing this package.
"""
from __future__ import annotations

import os


__all__ = ["__version__"]
__version__ = "0.1.0"


def _apply_model_free_defaults() -> None:
    """Install fail-closed model defaults without overriding explicit policy.

    The legacy ``SERGEANT_LLM_*`` names remain valid compatibility inputs.  If
    either naming family explicitly supplies the enable switch, this package
    leaves every routing choice to ``LLMSettings``.  Otherwise model support is
    disabled before any CLI, service, IDE bridge, or benchmark imports the
    provider layer.
    """

    explicit_enable = os.getenv("SERGEANT_CPL_ENABLED")
    if explicit_enable is None:
        explicit_enable = os.getenv("SERGEANT_LLM_ENABLED")
    if explicit_enable is not None:
        return

    os.environ.setdefault("SERGEANT_CPL_ENABLED", "false")
    if "SERGEANT_CPL_POLICY" not in os.environ and "SERGEANT_LLM_POLICY" not in os.environ:
        os.environ["SERGEANT_CPL_POLICY"] = "disabled"
    if "SERGEANT_CPL_PROVIDER" not in os.environ and "SERGEANT_LLM_PROVIDER" not in os.environ:
        os.environ["SERGEANT_CPL_PROVIDER"] = "disabled"


_apply_model_free_defaults()
