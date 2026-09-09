from __future__ import annotations

from pathlib import Path

from ..core.models import ExcelSchedule, IniTemplate, Plan
from ..core.planner import build_plan


def build_time_state_plan(
    schedule: ExcelSchedule,
    template: IniTemplate,
    audio_folder: str | Path,
) -> Plan:
    """Usa sólo bloques activos y crea el primero cuando una hora está vacía."""
    return build_plan(schedule, template, audio_folder, strategy="active_only")

