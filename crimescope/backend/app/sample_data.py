from copy import deepcopy
from typing import Any

from app.core.sample_loader import load_sample


def tract_risk_package() -> dict[str, Any]:
    return deepcopy(load_sample("tract_risk_package.sample.json"))


def live_event_package() -> dict[str, Any]:
    return deepcopy(load_sample("live_event_package.sample.json"))


def persona_decision_package() -> dict[str, Any]:
    return deepcopy(load_sample("persona_decision_package.sample.json"))


def report_summary_package() -> dict[str, Any]:
    return deepcopy(load_sample("report_summary_package.sample.json"))


def compare_package() -> dict[str, Any]:
    return deepcopy(load_sample("compare_package.sample.json"))
