from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .barra_generica.distribution import build_generic_plan
from .barra_generica.excel import read_generic_schedule
from .core.ini import read_ini, render_ini
from .core.models import ExcelSchedule, IniTemplate, Plan
from .tiempo_estado.distribution import build_time_state_plan
from .tiempo_estado.excel import read_schedule


@dataclass
class AnalysisResult:
    schedule: ExcelSchedule
    template: IniTemplate
    plan: Plan


@dataclass
class GenerationResult:
    output_path: Path
    backup_path: Path | None
    assignment_count: int


def analyze(
    excel_path: str | Path,
    audio_folder: str | Path,
    ini_path: str | Path,
    mode: str = "tiempo_estado",
    program_minutes: int | None = None,
    schedule_hours: list[int] | None = None,
) -> AnalysisResult:
    if mode == "barra_generica":
        if program_minutes is None or schedule_hours is None:
            raise ValueError("Selecciona la duración y los horarios de la barra genérica.")
        schedule = read_generic_schedule(excel_path, program_minutes, schedule_hours)
    elif mode == "tiempo_estado":
        schedule = read_schedule(excel_path)
    else:
        raise ValueError("El tipo de pauta no es válido.")
    template = read_ini(ini_path)
    if mode == "barra_generica":
        disabled_hours = sorted(set(schedule_hours or []) - set(template.configured_hours))
        if disabled_hours:
            formatted = ", ".join(f"{hour:02d}:00" for hour in disabled_hours)
            raise ValueError(
                "Los siguientes horarios no están habilitados en SHours dentro del INI: "
                f"{formatted}. Habilítalos en la plantilla o elige otro horario."
            )
    if mode == "barra_generica":
        plan = build_generic_plan(schedule, template, audio_folder)
    else:
        plan = build_time_state_plan(schedule, template, audio_folder)
    return AnalysisResult(schedule, template, plan)


def generate(
    analysis: AnalysisResult,
    output_path: str | Path | None = None,
    create_backup: bool = True,
) -> GenerationResult:
    if not analysis.plan.can_generate:
        raise ValueError("La pauta tiene errores pendientes y no puede generarse.")

    target = Path(output_path) if output_path else analysis.template.source_path
    target = target.resolve()
    source = analysis.template.source_path.resolve()
    rendered = render_ini(
        analysis.template,
        analysis.plan.assignments,
        analysis.plan.enabled_hours_added,
        analysis.plan.managed_prefix,
        analysis.plan.display_group,
    )
    _validate_rendered(rendered, len(analysis.plan.assignments), analysis.plan.managed_prefix)

    target.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = None
    if create_backup and target == source and source.exists():
        backup_path = _backup_name(source)
        shutil.copy2(source, backup_path)

    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="ascii", newline="") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return GenerationResult(target, backup_path, len(analysis.plan.assignments))


def radioboss_is_running() -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    processes = result.stdout.casefold()
    return "radioboss.exe" in processes or "adscheduler.exe" in processes


def restore_backup(backup_path: str | Path, target_path: str | Path) -> Path:
    backup = Path(backup_path).resolve()
    target = Path(target_path).resolve()
    if not backup.is_file():
        raise ValueError("El respaldo seleccionado no existe.")
    read_ini(backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        safety_backup = _backup_name(target, label="antes_restaurar")
        shutil.copy2(target, safety_backup)
    shutil.copy2(backup, target)
    return target


def _backup_name(path: Path, label: str = "respaldo") -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = path.name
    lower = name.casefold()
    if lower.endswith(".ini.txt"):
        base = name[:-8]
        suffix = ".ini.txt"
    else:
        base = path.stem
        suffix = path.suffix
    candidate = path.with_name(f"{base}_{label}_{timestamp}{suffix}")
    counter = 2
    while candidate.exists():
        candidate = path.with_name(f"{base}_{label}_{timestamp}_{counter}{suffix}")
        counter += 1
    return candidate


def _validate_rendered(text: str, assignment_count: int, managed_prefix: str) -> None:
    if not text.startswith("object TAdsSchedulerIni"):
        raise ValueError("El INI generado perdió su cabecera de RadioBOSS.")
    if "  WorkFolder =" not in text or not text.rstrip().endswith("end"):
        raise ValueError("El INI generado está incompleto.")
    generated_marks = text.count(f"Value.DisplayName = '{managed_prefix}")
    if generated_marks == 0 or generated_marks > assignment_count:
        raise ValueError("La sección generada de Tiempo Estado no es válida.")
