from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .ini import track_is_valid
from .models import Assignment, ExcelSchedule, IniTemplate, Plan


AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
KEY_AT_START_RE = re.compile(r"^(RD[FP]\d+)\b", re.IGNORECASE)


def index_audio_folder(path: str | Path) -> tuple[dict[str, list[Path]], list[Path]]:
    folder = Path(path)
    if not folder.is_dir():
        raise ValueError("La carpeta de audios no existe o no es accesible.")
    index: dict[str, list[Path]] = defaultdict(list)
    without_key: list[Path] = []
    for file_path in sorted(folder.rglob("*")):
        if not file_path.is_file() or file_path.suffix.casefold() not in AUDIO_EXTENSIONS:
            continue
        match = KEY_AT_START_RE.match(file_path.stem.strip())
        if match:
            index[match.group(1).upper()].append(file_path.resolve())
        else:
            without_key.append(file_path.resolve())
    return dict(index), without_key


def build_plan(
    schedule: ExcelSchedule,
    template: IniTemplate,
    audio_folder: str | Path,
    strategy: str = "active_only",
) -> Plan:
    if strategy not in {"active_only", "least_loaded"}:
        raise ValueError("La estrategia de distribución no es válida.")
    audio_index, unmatched = index_audio_folder(audio_folder)
    required_keys = sorted({record.key for record in schedule.records})
    missing = [key for key in required_keys if key not in audio_index]
    duplicates = {key: audio_index[key] for key in required_keys if len(audio_index.get(key, [])) > 1}
    warnings = list(schedule.warnings)
    if unmatched:
        warnings.append(f"{len(unmatched)} archivo(s) de audio no comienzan con una clave RDF y se omitieron.")
    if missing or duplicates:
        prefix, group = _managed_identity(schedule)
        return Plan([], missing, duplicates, unmatched, warnings, [], prefix, group)

    configured_minutes = template.configured_minutes
    configured_minute_set = set(configured_minutes)
    existing_count: Counter[tuple[date, int, int]] = Counter()

    schedule_slots = sorted({(record.transmission_date, record.hour) for record in schedule.records})
    for transmission_date, scheduled_hour in schedule_slots:
        weekday = transmission_date.isoweekday()
        for track in template.existing_tracks:
            for hour, minute, mark_day in track.marks:
                if (
                    hour == scheduled_hour
                    and mark_day == weekday
                    and minute in configured_minute_set
                    and track_is_valid(track, transmission_date, hour, minute)
                ):
                    existing_count[(transmission_date, hour, minute)] += 1

    generated_count: Counter[tuple[date, int, int]] = Counter()
    generated_active: set[tuple[date, int, int]] = set()
    assignments: list[Assignment] = []

    for record in sorted(schedule.records, key=lambda value: (value.transmission_date, value.sequence, value.source_row)):
        slot_prefix = (record.transmission_date, record.hour)
        if strategy == "least_loaded":
            active_minutes = list(configured_minutes)
        else:
            active_minutes = [
                minute
                for minute in configured_minutes
                if existing_count[(*slot_prefix, minute)] > 0 or (*slot_prefix, minute) in generated_active
            ]
        if active_minutes:
            minute = min(
                active_minutes,
                key=lambda value: (
                    existing_count[(*slot_prefix, value)] + generated_count[(*slot_prefix, value)],
                    configured_minutes.index(value),
                ),
            )
            chosen_key = (*slot_prefix, minute)
            origin = "Existente" if existing_count[chosen_key] else "Creado"
        else:
            minute = configured_minutes[0]
            origin = "Creado"

        key = (*slot_prefix, minute)
        assignment = Assignment(
            transmission_date=record.transmission_date,
            hour=record.hour,
            minute=minute,
            original_key=record.original_key,
            key=record.key,
            audio_path=audio_index[record.key][0],
            source_row=record.source_row,
            block_origin=origin,
            existing_ad_count=existing_count[key],
        )
        assignments.append(assignment)
        generated_count[key] += 1
        generated_active.add(key)

    added_hours = sorted({record.hour for record in schedule.records} - set(template.configured_hours))
    if added_hours:
        hours_text = ", ".join(f"{hour:02d}:00" for hour in added_hours)
        warnings.append(f"Se habilitarán en SHours las horas requeridas por el Excel: {hours_text}.")

    prefix, group = _managed_identity(schedule)
    return Plan(assignments, [], {}, unmatched, warnings, added_hours, prefix, group)


def _managed_identity(schedule: ExcelSchedule) -> tuple[str, str]:
    if schedule.source_kind == "barra_generica":
        return "AUTO_BGN_", "BARRA GENERICA NACIONAL"
    return "AUTO_TE_", "TIEMPO ESTADO"
