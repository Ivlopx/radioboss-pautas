from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

from .models import Assignment, ExistingTrack, IniTemplate


ADTRACKS_RE = re.compile(r"(?m)^  AdTracks = <\r?$")
WORKFOLDER_RE = re.compile(r"(?m)^  WorkFolder =")
TOP_ITEM_RE = re.compile(r"(?m)^    item\r?$")


def date_to_delphi_serial(value: date) -> int:
    return (value - date(1899, 12, 30)).days


def delphi_serial_to_date(value: int) -> date:
    return date(1899, 12, 30) + timedelta(days=value)


def read_ini(path: str | Path) -> IniTemplate:
    source = Path(path)
    raw = source.read_bytes()
    encoding = "utf-8-sig"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1252"
        text = raw.decode(encoding)

    newline = "\r\n" if "\r\n" in text else "\n"
    adtracks = ADTRACKS_RE.search(text)
    workfolder = WORKFOLDER_RE.search(text)
    if adtracks is None or workfolder is None or adtracks.end() >= workfolder.start():
        raise ValueError("El archivo no tiene una sección AdTracks compatible.")

    line_end = text.find("\n", adtracks.end())
    if line_end < 0:
        raise ValueError("La cabecera AdTracks está incompleta.")
    tracks_start = line_end + 1
    prefix = text[:tracks_start]
    tracks_text = text[tracks_start:workfolder.start()]

    closing_matches = list(re.finditer(r"(?m)^    end>\r?\n?", tracks_text))
    if not closing_matches:
        raise ValueError("No se encontró el cierre de la lista AdTracks.")
    outer_close = closing_matches[-1]
    if tracks_text[outer_close.end():].strip():
        raise ValueError("Hay contenido inesperado después de AdTracks.")

    hours = _mask_values(text, "SHours", 24)
    minutes = _mask_values(text, "SMinutes", 60)
    if not minutes:
        raise ValueError("El INI no tiene minutos habilitados en SMinutes.")

    return IniTemplate(
        source_path=source,
        original_text=text,
        newline=newline,
        prefix_through_adtracks=prefix,
        existing_tracks_text=tracks_text,
        tail_from_workfolder=text[workfolder.start():],
        configured_hours=hours,
        configured_minutes=minutes,
        existing_tracks=_parse_existing_tracks(tracks_text),
    )


def _mask_values(text: str, field: str, expected_length: int) -> list[int]:
    match = re.search(rf"(?m)^  {re.escape(field)} = '([01]+)'\r?$", text)
    if not match or len(match.group(1)) != expected_length:
        raise ValueError(f"La máscara {field} no es válida.")
    return [index for index, value in enumerate(match.group(1)) if value == "1"]


def _parse_existing_tracks(text: str) -> list[ExistingTrack]:
    starts = [match.start() for match in TOP_ITEM_RE.finditer(text)]
    result: list[ExistingTrack] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        item = text[start:end]
        marks = tuple(
            (int(hour), int(minute), int(day))
            for hour, minute, day in re.findall(
                r"Hour = (\d+)\s+Minute = (\d+)\s+Day = (\d+)", item
            )
        )
        result.append(
            ExistingTrack(
                marks=marks,
                active=_bool_field(item, "Value.Active", True),
                has_start=_bool_field(item, "Value.IsStart", False),
                start_serial=_int_field(item, "Value.Start"),
                start_hour=_int_field(item, "Value.StartH") or 0,
                has_end=_bool_field(item, "Value.IsEnd", False),
                end_serial=_int_field(item, "Value.End2"),
                end_hour=_int_field(item, "Value.EndH") or 23,
            )
        )
    return result


def _bool_field(text: str, field: str, default: bool) -> bool:
    match = re.search(rf"(?m)^\s+{re.escape(field)} = (True|False)\r?$", text)
    return default if match is None else match.group(1) == "True"


def _int_field(text: str, field: str) -> int | None:
    match = re.search(rf"(?m)^\s+{re.escape(field)} = (-?\d+)\r?$", text)
    return None if match is None else int(match.group(1))


def track_is_valid(track: ExistingTrack, transmission_date: date, hour: int, minute: int) -> bool:
    if not track.active:
        return False
    moment = datetime.combine(transmission_date, time(hour, minute))
    if track.has_start and track.start_serial is not None:
        start = datetime.combine(delphi_serial_to_date(track.start_serial), time(track.start_hour, 0))
        if moment < start:
            return False
    if track.has_end and track.end_serial is not None:
        end = datetime.combine(delphi_serial_to_date(track.end_serial), time(track.end_hour, 59, 59))
        if moment > end:
            return False
    return True


def render_ini(
    template: IniTemplate,
    assignments: list[Assignment],
    enabled_hours_added: list[int],
    managed_prefix: str = "AUTO_TE_",
    display_group: str = "TIEMPO ESTADO",
) -> str:
    newline = template.newline
    prefix = template.prefix_through_adtracks
    if enabled_hours_added:
        enabled = set(template.configured_hours) | set(enabled_hours_added)
        mask = "".join("1" if hour in enabled else "0" for hour in range(24))
        prefix = re.sub(
            r"(?m)^(  SHours = ')[01]+('\r?)$",
            lambda match: f"{match.group(1)}{mask}{match.group(2)}",
            prefix,
        )

    existing = _unmanaged_existing_tracks(template.existing_tracks_text, newline, managed_prefix)
    items = _render_generated_items(assignments, newline, managed_prefix, display_group)
    if not items:
        raise ValueError("No hay asignaciones para escribir.")
    content = prefix + existing + items
    if not content.endswith(newline):
        content += newline
    content += template.tail_from_workfolder
    return content


def _unmanaged_existing_tracks(text: str, newline: str, managed_prefix: str) -> str:
    """Conserva pistas manuales y retira solamente las creadas por esta app."""
    starts = [match.start() for match in TOP_ITEM_RE.finditer(text)]
    if not starts:
        return ""
    prefix = text[: starts[0]]
    kept: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        item = text[start:end]
        accepted_prefixes = [managed_prefix]
        if managed_prefix == "AUTO_TE_":
            accepted_prefixes.append("TE_")
        prefix_pattern = "|".join(re.escape(prefix) for prefix in accepted_prefixes)
        managed = re.search(rf"(?m)^\s+Value\.DisplayName = '(?:{prefix_pattern})", item)
        if managed:
            continue
        item = re.sub(r"(?m)^    end>\r?\n?$", f"    end{newline}", item)
        kept.append(item)
    return prefix + "".join(kept)


def _render_generated_items(
    assignments: list[Assignment],
    newline: str,
    managed_prefix: str,
    display_group: str,
) -> str:
    grouped: dict[tuple[date, str, Path], list[Assignment]] = {}
    for assignment in assignments:
        grouped.setdefault(
            (assignment.transmission_date, assignment.key, assignment.audio_path), []
        ).append(assignment)

    chunks: list[str] = []
    ordered = sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], str(item[0][2])))
    for position, ((day, key, audio_path), group) in enumerate(ordered):
        lines = ["    item", "      Value.Marks = <"]
        for assignment in sorted(group, key=lambda value: (value.hour, value.minute, value.source_row)):
            lines.extend(
                [
                    "        item",
                    f"          Hour = {assignment.hour}",
                    f"          Minute = {assignment.minute}",
                    f"          Day = {day.isoweekday()}",
                    "        end",
                ]
            )
        lines[-1] += ">"
        serial = date_to_delphi_serial(day)
        display_name = f"{managed_prefix}{day:%Y-%m-%d}_{key}"
        lines.extend(
            [
                "      Value.Priority = 49",
                "      Value.PriorityUpdated = True",
                "      Value.Active = True",
                "      Value.IsStart = True",
                f"      Value.Start = {serial}",
                "      Value.StartH = 0",
                "      Value.IsEnd = True",
                f"      Value.End2 = {serial}",
                "      Value.EndH = 23",
                f"      Value.DisplayGroup = {_pascal_string(display_group)}",
                f"      Value.DisplayName = {_pascal_string(display_name)}",
                "      Value.AltTracks.Strings = (",
                f"        {_pascal_string(str(audio_path))})",
                "      Value.BgColor = clWindow",
                "    end>" if position == len(ordered) - 1 else "    end",
            ]
        )
        chunks.append(newline.join(lines) + newline)
    return "".join(chunks)


def _pascal_string(value: str) -> str:
    parts: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            parts.append("'" + "".join(current).replace("'", "''") + "'")
            current.clear()

    for char in value:
        code = ord(char)
        if 32 <= code <= 126:
            current.append(char)
        else:
            flush()
            parts.append(f"#{code}")
    flush()
    return "".join(parts) if parts else "''"
