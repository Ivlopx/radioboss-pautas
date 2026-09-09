from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from radioboss_pautas.service import (
    AnalysisResult,
    analyze,
    generate,
    radioboss_is_running,
    restore_backup,
)
from radioboss_pautas.core.ini import read_ini


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.analysis: AnalysisResult | None = None
        self.setWindowTitle("Generador de pauta para RadioBOSS")
        self.resize(1220, 860)
        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(3)
        title = QLabel("Generador de pautas para RadioBOSS")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Prepara, valida y distribuye pautas antes de incorporarlas a la programación."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        heading.addWidget(title)
        heading.addWidget(subtitle)
        badge = QLabel("RADIOBOSS")
        badge.setObjectName("productBadge")
        badge.setAlignment(Qt.AlignCenter)
        header.addLayout(heading, 1)
        header.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(header)

        steps = QLabel("1  Plantilla INI     2  Modalidad y archivos     3  Vista previa     4  Generar")
        steps.setObjectName("stepGuide")
        layout.addWidget(steps)

        template_group = QGroupBox("Paso 1 — Seleccionar INI plantilla")
        template_group.setProperty("card", True)
        template_form = QFormLayout(template_group)
        self.ini_edit = self._path_row(template_form, "INI de Ads Scheduler", "ini")
        self.ini_status = QLabel("Selecciona un INI válido para habilitar las secciones.")
        self.ini_status.setWordWrap(True)
        template_form.addRow("Estado", self.ini_status)
        self.ini_edit.textChanged.connect(self._load_ini_template)
        layout.addWidget(template_group)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("modeTabs")
        self.tabs.addTab(self._build_time_state_tab(), "Tiempo Estado")
        self.tabs.addTab(self._build_generic_tab(), "Barra genérica nacional")
        self.tabs.currentChanged.connect(self._invalidate)
        self.tabs.setEnabled(False)
        layout.addWidget(self.tabs)

        options = QHBoxLayout()
        self.backup_check = QCheckBox("Crear respaldo antes de reemplazar el INI")
        self.backup_check.setObjectName("backupOption")
        self.backup_check.setChecked(True)
        self.analyze_button = QPushButton("Analizar y previsualizar")
        self.analyze_button.setObjectName("primaryButton")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self._analyze)
        self.generate_button = QPushButton("Generar INI")
        self.generate_button.setObjectName("successButton")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._generate)
        self.restore_button = QPushButton("Restaurar respaldo")
        self.restore_button.setObjectName("secondaryButton")
        self.restore_button.setEnabled(False)
        self.restore_button.clicked.connect(self._restore)
        options.addWidget(self.backup_check)
        options.addStretch()
        options.addWidget(self.restore_button)
        options.addWidget(self.analyze_button)
        options.addWidget(self.generate_button)
        layout.addLayout(options)

        self.summary = QLabel("Aún no se ha analizado una pauta.")
        self.summary.setObjectName("summaryBar")
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("previewTable")
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Hora elegida", "Bloque", "Clave", "Audio", "Origen", "Fila Excel"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        warnings_group = QGroupBox("Validación y advertencias")
        warnings_group.setProperty("card", True)
        warnings_layout = QVBoxLayout(warnings_group)
        self.warnings = QPlainTextEdit()
        self.warnings.setReadOnly(True)
        self.warnings.setPlaceholderText("Aquí aparecerán notas, archivos faltantes o conflictos.")
        self.warnings.setMaximumHeight(140)
        warnings_layout.addWidget(self.warnings)
        layout.addWidget(warnings_group)

        self.setCentralWidget(root)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget#appRoot {
                background: #f4f7fb;
                color: #172033;
                font-family: "Segoe UI", "Inter", "Arial";
                font-size: 13px;
            }
            QLabel#pageTitle {
                color: #10233f;
                font-size: 26px;
                font-weight: 700;
            }
            QLabel#pageSubtitle {
                color: #64748b;
                font-size: 13px;
            }
            QLabel#productBadge {
                color: #0f766e;
                background: #dff7f2;
                border: 1px solid #a7e3d8;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#stepGuide {
                color: #475569;
                background: #e9eef6;
                border-radius: 8px;
                padding: 9px 14px;
                font-weight: 600;
            }
            QGroupBox[card="true"], QGroupBox {
                background: #ffffff;
                border: 1px solid #dce3ed;
                border-radius: 10px;
                margin-top: 12px;
                padding: 13px 12px 10px 12px;
                font-weight: 600;
                color: #26364d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #334155;
            }
            QTabWidget#modeTabs::pane {
                background: #ffffff;
                border: 1px solid #dce3ed;
                border-radius: 10px;
                top: -1px;
            }
            QTabBar::tab {
                background: #e9eef6;
                color: #536176;
                border: 1px solid #dce3ed;
                border-bottom: none;
                padding: 10px 20px;
                min-width: 150px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #0f766e;
                border-top: 3px solid #14b8a6;
                padding-top: 8px;
            }
            QTabBar::tab:disabled {
                color: #a8b1bf;
                background: #edf1f6;
            }
            QLineEdit, QComboBox, QPlainTextEdit {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 7px;
                padding: 7px 9px;
                selection-background-color: #99f6e4;
            }
            QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {
                border: 2px solid #14b8a6;
                padding: 6px 8px;
            }
            QComboBox::drop-down {
                border: none;
                width: 28px;
            }
            QPushButton {
                min-height: 34px;
                border-radius: 7px;
                padding: 0 16px;
                font-weight: 600;
            }
            QPushButton#secondaryButton, QGroupBox QPushButton {
                color: #334155;
                background: #ffffff;
                border: 1px solid #cbd5e1;
            }
            QPushButton#secondaryButton:hover, QGroupBox QPushButton:hover {
                background: #f1f5f9;
                border-color: #94a3b8;
            }
            QPushButton#primaryButton {
                color: #ffffff;
                background: #173b65;
                border: 1px solid #173b65;
            }
            QPushButton#primaryButton:hover { background: #214f83; }
            QPushButton#successButton {
                color: #ffffff;
                background: #0f766e;
                border: 1px solid #0f766e;
            }
            QPushButton#successButton:hover { background: #0d8a80; }
            QPushButton:disabled {
                color: #94a3b8;
                background: #e7ecf2;
                border: 1px solid #d8e0ea;
            }
            QLabel#summaryBar {
                color: #24334a;
                background: #e6f4f2;
                border: 1px solid #b7ded8;
                border-radius: 8px;
                padding: 10px 13px;
                font-weight: 600;
            }
            QTableWidget#previewTable {
                background: #ffffff;
                alternate-background-color: #f8fafc;
                border: 1px solid #dce3ed;
                border-radius: 8px;
                selection-background-color: #c8f1eb;
                selection-color: #172033;
            }
            QHeaderView::section {
                color: #ffffff;
                background: #173b65;
                border: none;
                border-right: 1px solid #31577f;
                padding: 9px 8px;
                font-weight: 600;
            }
            QCheckBox#backupOption { color: #334155; spacing: 8px; }
            """
        )

    def _build_time_state_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        description = QLabel(
            "Lee fecha, clave RDF y franja horaria de cada fila. Reutiliza bloques activos; "
            "si no hay ninguno, usa el primer minuto habilitado por el INI."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        inputs = QGroupBox("Archivos de Tiempo Estado")
        form = QFormLayout(inputs)
        self.te_excel_edit = self._path_row(form, "Excel de Tiempo Estado", "excel")
        self.te_audio_edit = self._path_row(form, "Carpeta Material Radio", "folder")
        layout.addWidget(inputs)
        return tab

    def _build_generic_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        description = QLabel(
            "Lee el calendario de lunes a lunes y las claves RDP. Los programas de 5 minutos "
            "usan dos horarios; los de 10 minutos usan uno. Siempre elige el bloque menos cargado."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        inputs = QGroupBox("Archivos de Barra genérica nacional")
        form = QFormLayout(inputs)
        self.bgn_excel_edit = self._path_row(form, "Excel de barra genérica", "excel")
        self.bgn_audio_edit = self._path_row(form, "Carpeta Material Radio", "folder")
        layout.addWidget(inputs)

        settings = QGroupBox("Configuración de transmisión")
        settings_form = QFormLayout(settings)
        self.duration_combo = QComboBox()
        self.duration_combo.addItem("Programas de 5 minutos", 5)
        self.duration_combo.addItem("Programas de 10 minutos", 10)
        self.duration_combo.currentIndexChanged.connect(self._update_generic_hours)
        self.hour1_combo = self._hour_combo()
        self.hour2_combo = self._hour_combo()
        settings_form.addRow("Tipo de estación", self.duration_combo)
        settings_form.addRow("Horario 1", self.hour1_combo)
        self.hour2_label = QLabel("Horario 2")
        settings_form.addRow(self.hour2_label, self.hour2_combo)
        layout.addWidget(settings)
        return tab

    def _hour_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem("Seleccionar…", None)
        combo.currentIndexChanged.connect(self._invalidate)
        return combo

    def _path_row(self, form: QFormLayout, label: str, kind: str) -> QLineEdit:
        row = QWidget()
        row_layout = QGridLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit()
        edit.textChanged.connect(self._invalidate)
        button = QPushButton("Seleccionar…")
        button.clicked.connect(lambda: self._choose_path(edit, kind))
        row_layout.addWidget(edit, 0, 0)
        row_layout.addWidget(button, 0, 1)
        form.addRow(label, row)
        return edit

    def _choose_path(self, edit: QLineEdit, kind: str) -> None:
        if kind == "folder":
            path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta Material Radio")
        elif kind == "excel":
            path, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar pauta", "", "Excel (*.xlsx *.xlsm)"
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar INI", "", "Ads Scheduler (*.ini *.ini.txt *.txt);;Todos (*)"
            )
        if path:
            edit.setText(path)

    def _update_generic_hours(self, *_args) -> None:
        is_five_minutes = self.duration_combo.currentData() == 5
        self.hour2_label.setVisible(is_five_minutes)
        self.hour2_combo.setVisible(is_five_minutes)
        self._invalidate()

    def _load_ini_template(self, path_text: str) -> None:
        self._invalidate()
        valid = False
        if path_text.strip():
            try:
                template = read_ini(path_text.strip())
                valid = True
                hours = ", ".join(f"{hour:02d}:00" for hour in template.configured_hours)
                minutes = ", ".join(f":{minute:02d}" for minute in template.configured_minutes)
                self.ini_status.setText(f"Plantilla válida. Horas: {hours}. Bloques: {minutes}.")
                self.ini_status.setStyleSheet("color: #176b36;")
                if hasattr(self, "hour1_combo"):
                    self._populate_hour_combos(template.configured_hours)
            except Exception as exc:
                self.ini_status.setText(f"INI no válido: {exc}")
                self.ini_status.setStyleSheet("color: #a12622;")
        else:
            self.ini_status.setText("Selecciona un INI válido para habilitar las secciones.")
            self.ini_status.setStyleSheet("")
        if hasattr(self, "tabs"):
            self.tabs.setEnabled(valid)
        if hasattr(self, "analyze_button"):
            self.analyze_button.setEnabled(valid)
            self.restore_button.setEnabled(valid)

    def _populate_hour_combos(self, hours: list[int]) -> None:
        for combo in (self.hour1_combo, self.hour2_combo):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Seleccionar…", None)
            for hour in hours:
                combo.addItem(f"{hour:02d}:00", hour)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

    def _current_paths(self) -> tuple[QLineEdit, QLineEdit, QLineEdit]:
        if self.tabs.currentIndex() == 0:
            return self.te_excel_edit, self.te_audio_edit, self.ini_edit
        return self.bgn_excel_edit, self.bgn_audio_edit, self.ini_edit

    def _invalidate(self, *_args) -> None:
        self.analysis = None
        if hasattr(self, "generate_button"):
            self.generate_button.setEnabled(False)

    def _analyze(self) -> None:
        excel_edit, audio_edit, ini_edit = self._current_paths()
        try:
            if self.tabs.currentIndex() == 0:
                self.analysis = analyze(
                    excel_edit.text().strip(),
                    audio_edit.text().strip(),
                    ini_edit.text().strip(),
                    mode="tiempo_estado",
                )
            else:
                hours = [self.hour1_combo.currentData()]
                if self.duration_combo.currentData() == 5:
                    hours.append(self.hour2_combo.currentData())
                if any(hour is None for hour in hours):
                    raise ValueError("Selecciona todos los horarios requeridos.")
                self.analysis = analyze(
                    excel_edit.text().strip(),
                    audio_edit.text().strip(),
                    ini_edit.text().strip(),
                    mode="barra_generica",
                    program_minutes=self.duration_combo.currentData(),
                    schedule_hours=hours,
                )
            self._show_analysis(self.analysis)
        except Exception as exc:
            self.analysis = None
            self.generate_button.setEnabled(False)
            QMessageBox.critical(self, "No se pudo analizar", str(exc))

    def _show_analysis(self, result: AnalysisResult) -> None:
        plan = result.plan
        dates = sorted({item.transmission_date for item in result.schedule.records})
        created = sum(1 for item in plan.assignments if item.block_origin == "Creado")
        self.summary.setText(
            f"{len(result.schedule.records)} transmisiones | "
            f"{dates[0].strftime('%d/%m/%Y')} a {dates[-1].strftime('%d/%m/%Y')} | "
            f"{len({item.key for item in result.schedule.records})} claves | "
            f"{created} asignaciones en bloques que estaban vacíos"
        )

        self.table.setRowCount(len(plan.assignments))
        for row, item in enumerate(plan.assignments):
            values = [
                item.transmission_date.strftime("%d/%m/%Y"),
                f"{item.hour:02d}:00–{item.hour:02d}:59",
                f"{item.hour:02d}:{item.minute:02d}",
                item.key if item.key == item.original_key else f"{item.original_key} → {item.key}",
                item.audio_path.name,
                item.block_origin,
                str(item.source_row),
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column in (0, 1, 2, 5, 6):
                    cell.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, cell)

        messages = list(plan.warnings)
        if plan.missing_keys:
            messages.insert(0, "Audios faltantes: " + ", ".join(plan.missing_keys))
        if plan.duplicate_audio_keys:
            for key, files in plan.duplicate_audio_keys.items():
                messages.insert(0, f"Clave duplicada {key}: " + "; ".join(path.name for path in files))
        self.warnings.setPlainText("\n".join(f"• {message}" for message in messages) or "Sin advertencias.")
        self.generate_button.setEnabled(plan.can_generate)

    def _generate(self) -> None:
        if self.analysis is None:
            return
        if radioboss_is_running():
            answer = QMessageBox.warning(
                self,
                "RadioBOSS está abierto",
                "Cierra RadioBOSS y Ads Scheduler antes de reemplazar el INI para evitar que "
                "el programa vuelva a guardar una versión anterior. ¿Deseas continuar de todos modos?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        _, _, ini_edit = self._current_paths()
        ini_path = Path(ini_edit.text().strip())
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar INI generado",
            str(ini_path),
            "Ads Scheduler (*.ini *.ini.txt *.txt);;Todos (*)",
        )
        if not target:
            return
        try:
            result = generate(self.analysis, target, self.backup_check.isChecked())
            backup_text = f"\nRespaldo: {result.backup_path}" if result.backup_path else ""
            QMessageBox.information(
                self,
                "INI generado",
                f"Se generaron {result.assignment_count} transmisiones.\nArchivo: {result.output_path}{backup_text}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo generar", str(exc))

    def _restore(self) -> None:
        backup, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar respaldo", "", "Ads Scheduler (*.ini *.ini.txt *.txt);;Todos (*)"
        )
        if not backup:
            return
        _, _, ini_edit = self._current_paths()
        target, _ = QFileDialog.getSaveFileName(
            self, "Restaurar como", ini_edit.text().strip(), "Ads Scheduler (*.ini *.ini.txt *.txt);;Todos (*)"
        )
        if not target:
            return
        try:
            restored = restore_backup(backup, target)
            QMessageBox.information(self, "Respaldo restaurado", f"Archivo restaurado: {restored}")
        except Exception as exc:
            QMessageBox.critical(self, "No se pudo restaurar", str(exc))


def main() -> int:
    application = QApplication(sys.argv)
    application.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
