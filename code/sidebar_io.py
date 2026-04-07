"""Dialogy a logika exportu/importu instancí (TSP/GPX) pro sidebar."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from geocode_cache import geocode_cache
from state_notify import CENTER_MAP
from tspmanager import tsp_manager


def _with_extension(path: str, ext: str) -> str:
    root, _ = os.path.splitext(path)
    return root + ext


@dataclass(frozen=True)
class ExportInteractiveResult:
    status: Literal["cancelled", "no_points", "success", "error"]
    used_tsp_fallback: bool = False
    saved_path: str | None = None


def export_instance_interactive(
    parent: QWidget,
    *,
    state,
    fmt: str,
) -> ExportInteractiveResult:
    route_points = state.get_route() or []
    suggested_ext = ".gpx" if fmt == "GPX" else ".tsp"
    suggested_name = f"instance{suggested_ext}"
    file_filter = "GPX soubory (*.gpx);;TSP soubory (*.tsp);;Všechny soubory (*)"

    filepath, _ = QFileDialog.getSaveFileName(
        parent,
        "Exportovat instanci",
        suggested_name,
        file_filter,
    )
    if not filepath:
        return ExportInteractiveResult(status="cancelled")

    try:
        points = state.get_points()
        if not points:
            return ExportInteractiveResult(status="no_points")

        selected_fmt = fmt
        target_filepath = filepath
        used_tsp_fallback = False

        if fmt == "GPX":
            if not route_points:
                reply = QMessageBox.question(
                    parent,
                    "Export GPX bez trasy",
                    (
                        "GPX může obsahovat waypointy i trasu.\n\n"
                        "Pro tuto instanci není vygenerovaná trasa.\n"
                        "Chceš exportovat waypoint-only GPX?\n\n"
                        "Ano = uložit .gpx s waypointy\n"
                        "Ne = fallback do .tsp (MODERN_GPS_DIPLOMA)\n"
                        "Zrušit / zavřít = nic neukládat"
                    ),
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                    | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    target_filepath = _with_extension(target_filepath, ".gpx")
                elif reply == QMessageBox.StandardButton.No:
                    selected_fmt = "TSP_GEO" if state.is_geo() else "TSP_EUC_2D"
                    used_tsp_fallback = True
                    target_filepath = _with_extension(target_filepath, ".tsp")
                else:
                    return ExportInteractiveResult(status="cancelled")
            else:
                target_filepath = _with_extension(target_filepath, ".gpx")
        else:
            target_filepath = _with_extension(target_filepath, ".tsp")

        tsp_manager.export_instance(
            target_filepath,
            points,
            selected_fmt,
            route_points=route_points,
        )
        geocode_cache.add_from_state(state)
        print(f"DEBUG: Uloženo do {target_filepath}")
        if used_tsp_fallback:
            QMessageBox.information(
                parent,
                "Export dokončen (fallback)",
                (
                    "GPX export bez vygenerované trasy byl uložen jako .tsp "
                    "s tagem MODERN_GPS_DIPLOMA."
                ),
            )
        return ExportInteractiveResult(
            status="success",
            used_tsp_fallback=used_tsp_fallback,
            saved_path=target_filepath,
        )

    except Exception as ex:
        print(f"ERROR EXPORT: {ex}")
        return ExportInteractiveResult(status="error")


@dataclass(frozen=True)
class ImportInteractiveResult:
    status: Literal[
        "cancelled",
        "empty",
        "success_with_route",
        "success_points_only",
        "error",
    ]


def import_instance_interactive(parent: QWidget, *, state) -> ImportInteractiveResult:
    filepath, _ = QFileDialog.getOpenFileName(
        parent,
        "Načíst instanci",
        "",
        "Podporované soubory (*.tsp *.gpx);;TSP soubory (*.tsp);;GPX soubory (*.gpx);;Všechny soubory (*)",
    )
    if not filepath:
        return ImportInteractiveResult(status="cancelled")

    try:
        payload = tsp_manager.load_instance(filepath)
        new_points = payload.get("points", [])
        route_points = payload.get("route_points", [])
        is_geo = bool(payload.get("is_geographic", True))

        if new_points:
            state.clear_all()
            state.apply_imported_instance(
                new_points,
                is_geographic=is_geo,
                route_points=route_points,
            )
            state.notify((CENTER_MAP, new_points[0]))
            if route_points:
                return ImportInteractiveResult(status="success_with_route")
            return ImportInteractiveResult(status="success_points_only")
        return ImportInteractiveResult(status="empty")

    except Exception as ex:
        print(f"ERROR IMPORT: {ex}")
        return ImportInteractiveResult(status="error")
