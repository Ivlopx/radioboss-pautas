from __future__ import annotations

from pathlib import Path

from ..core.models import ExcelSchedule, IniTemplate, Plan
from ..core.planner import build_plan


def build_generic_plan(
    schedule: ExcelSchedule,
    template: IniTemplate,
    audio_folder: str | Path,
) -> Plan:
    """Compara todos los minutos habilitados y elige siempre el menos cargado."""
    return build_plan(schedule, template, audio_folder, strategy="least_loaded")

