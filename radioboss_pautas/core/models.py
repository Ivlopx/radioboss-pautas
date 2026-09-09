from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class ReplacementRule:
    old_key: str
    new_key: str
    effective_date: date
    source_note: str


@dataclass(frozen=True)
class ScheduleRecord:
    transmission_date: date
    sequence: int
    hour: int
    original_key: str
    key: str
    agency: str
    campaign: str
    version: str
    duration_seconds: int | None
    source_row: int


@dataclass
class ExcelSchedule:
    records: list[ScheduleRecord]
    notes: list[str]
    replacement_rules: list[ReplacementRule]
    warnings: list[str] = field(default_factory=list)
    source_kind: str = "tiempo_estado"


@dataclass(frozen=True)
class ExistingTrack:
    marks: tuple[tuple[int, int, int], ...]
    active: bool
    has_start: bool
    start_serial: int | None
    start_hour: int
    has_end: bool
    end_serial: int | None
    end_hour: int


@dataclass
class IniTemplate:
    source_path: Path
    original_text: str
    newline: str
    prefix_through_adtracks: str
    existing_tracks_text: str
    tail_from_workfolder: str
    configured_hours: list[int]
    configured_minutes: list[int]
    existing_tracks: list[ExistingTrack]


@dataclass(frozen=True)
class Assignment:
    transmission_date: date
    hour: int
    minute: int
    original_key: str
    key: str
    audio_path: Path
    source_row: int
    block_origin: str
    existing_ad_count: int


@dataclass
class Plan:
    assignments: list[Assignment]
    missing_keys: list[str]
    duplicate_audio_keys: dict[str, list[Path]]
    unmatched_audio_files: list[Path]
    warnings: list[str]
    enabled_hours_added: list[int]
    managed_prefix: str = "AUTO_TE_"
    display_group: str = "TIEMPO ESTADO"

    @property
    def can_generate(self) -> bool:
        return not self.missing_keys and not self.duplicate_audio_keys and bool(self.assignments)
