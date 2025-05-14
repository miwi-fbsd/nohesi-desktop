# main.py (vollständiger, korrigierter Code)

import sys
import os
import json
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QLabel, QMainWindow, QPushButton, QMessageBox, QHBoxLayout, QCheckBox,
    QAction, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject

FAVORITES_FILE = "favorites.json"
SETTINGS_FILE = "settings.json"
LOCALES = {"de": "Deutsch", "en": "English"}


def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_favorites(favs):
    with open(FAVORITES_FILE, "w") as f:
        json.dump(list(favs), f)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"language": "en", "theme": "light"}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def load_locale(language_code):
    try:
        with open(f"locales/{language_code}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Fehler beim Laden der Sprachdatei: {e}")
        return {}

class ServerLoader(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()

    def run(self):
        all_servers = []
        page = 1
        while True:
            url = f"https://hub.nohesi.gg/servers?page={page}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                servers = data.get("data", {}).get("servers", [])
                if not servers:
                    break
                all_servers.extend(servers)
                if len(servers) < 10:
                    break
                page += 1
            except Exception as e:
                print(f"Fehler auf Seite {page}: {e}")
                break
        self.signals.finished.emit(all_servers)

class WorkerSignals(QObject):
    finished = pyqtSignal(list)


class SettingsDialog(QDialog):
    def __init__(self, parent, current_settings):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setModal(True)
        self.settings = current_settings.copy()

        layout = QFormLayout()

        self.language_combo = QComboBox()
        for code, name in LOCALES.items():
            self.language_combo.addItem(name, code)
        index = self.language_combo.findData(self.settings.get("language", "de"))
        self.language_combo.setCurrentIndex(index)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "light"))

        layout.addRow("Sprache:", self.language_combo)
        layout.addRow("Theme:", self.theme_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_settings(self):
        return {
            "language": self.language_combo.currentData(),
            "theme": self.theme_combo.currentText()
        }

class ServerBrowser(QMainWindow):
    def apply_theme(self):
        if self.settings.get("theme") == "dark":
            dark_stylesheet = """
                QWidget { background-color: #1e1e1e; color: #dddddd; }
                QComboBox, QLineEdit, QPushButton, QTableWidget, QCheckBox, QLabel {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555555;
                }
                QHeaderView::section {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
            """
            self.setStyleSheet(dark_stylesheet)
        else:
            self.setStyleSheet("")
    def init_menu(self):
        menubar = self.menuBar()
        einstellungen = menubar.addMenu(self.tr.get("settings", "Einstellungen"))
        action = QAction(self.tr.get("open_settings", "Einstellungen öffnen"), self)
        action.triggered.connect(self.open_settings_dialog)
        einstellungen.addAction(action)

    def open_settings_dialog(self):
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec_():
            self.settings = dialog.get_settings()
            save_settings(self.settings)
            self.tr = load_locale(self.settings.get("language", "de"))
            self.setWindowTitle(self.tr.get("title", "No Hesi Server Browser"))
            self.init_menu()
            self.init_filters()
            self.apply_filters()
            self.apply_theme()
            QMessageBox.information(self, self.tr.get("info", "Info"), self.tr.get("settings_saved", "Einstellungen gespeichert. Änderungen übernommen."))

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.tr = load_locale(self.settings.get("language", "de"))
        self.setWindowTitle(self.tr.get("title", "No Hesi Server Browser"))
        self.init_menu()
        self.resize(1000, 600)
        self.threadpool = QThreadPool()
        self.favorites = load_favorites()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.filter_layout = QHBoxLayout()

        self.region_filter = QComboBox()
        self.region_filter.currentTextChanged.connect(self.apply_filters)

        self.density_filter = QComboBox()
        self.density_filter.currentTextChanged.connect(self.apply_filters)

        self.type_filter = QComboBox()
        self.type_filter.currentTextChanged.connect(self.apply_filters)

        self.map_filter = QComboBox()
        self.map_filter.currentTextChanged.connect(self.apply_filters)

        self.sort_checkbox = QCheckBox(self.tr.get("most_played", "Sort by Most Played"))
        self.sort_checkbox.stateChanged.connect(self.apply_filters)

        self.only_favs_checkbox = QCheckBox(self.tr.get("favorites_only", "Only Favorites"))
        self.only_favs_checkbox.stateChanged.connect(self.apply_filters)

        self.filter_layout.addWidget(QLabel(self.tr.get("region", "Region") + ":"))
        self.filter_layout.addWidget(self.region_filter)
        self.filter_layout.addWidget(QLabel(self.tr.get("traffic", "Traffic") + ":"))
        self.filter_layout.addWidget(self.density_filter)
        self.filter_layout.addWidget(QLabel(self.tr.get("type", "Typ") + ":"))
        self.filter_layout.addWidget(self.type_filter)
        self.filter_layout.addWidget(QLabel(self.tr.get("map", "Map") + ":"))
        self.filter_layout.addWidget(self.map_filter)
        self.filter_layout.addWidget(self.sort_checkbox)
        self.filter_layout.addWidget(self.only_favs_checkbox)

        self.info_label = QLabel(self.tr.get("loading", "🔄 Loading server data..."))
        self.table = QTableWidget()
        self.table.cellDoubleClicked.connect(self.handle_click)

        self.join_button = QPushButton(self.tr.get("join_now", "Join Now"))
        self.join_button.clicked.connect(self.join_selected_server)

        self.layout.addWidget(self.info_label)
        self.layout.addLayout(self.filter_layout)
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.join_button)

        self.all_servers = []
        self.load_all_servers_async()
        self.apply_theme()

    def load_all_servers_async(self):
        self.info_label.setText(self.tr.get("loading", "🔄 Lade Serverdaten..."))
        loader = ServerLoader()
        loader.signals.finished.connect(self.on_servers_loaded)
        self.threadpool.start(loader)

    def on_servers_loaded(self, servers):
        self.all_servers = servers
        self.info_label.setText(self.tr.get("loaded", "✅ {count} Server geladen").replace("{count}", str(len(self.all_servers))))
        self.init_filters()
        self.apply_filters()

    def init_filters(self):
        for combo in [self.region_filter, self.density_filter, self.type_filter, self.map_filter]:
            combo.blockSignals(True)
            combo.clear()

        self.region_filter.addItem(self.tr.get("all_regions", "Alle Regionen"))
        self.density_filter.addItem(self.tr.get("all_densities", "Alle Dichten"))
        self.type_filter.addItem(self.tr.get("all_types", "Alle Typen"))
        self.map_filter.addItem(self.tr.get("all_maps", "Alle Maps"))

        regions = sorted(set(s.get("region", "") for s in self.all_servers))
        densities = sorted(set(s.get("density", "") for s in self.all_servers))
        types = sorted(set(s.get("type", "") for s in self.all_servers))
        maps = sorted(set(s.get("map", "") for s in self.all_servers))

        for val, (box, default_key) in zip(
            [regions, densities, types, maps],
            [
                (self.region_filter, "all_regions"),
                (self.density_filter, "all_densities"),
                (self.type_filter, "all_types"),
                (self.map_filter, "all_maps")
            ]):
            box.addItem(self.tr.get(default_key, val[0] if val else ""))
            for v in val:
                if v:
                    box.addItem(v)
            box.blockSignals(False)

    def apply_filters(self):
        region = self.region_filter.currentText()
        density = self.density_filter.currentText()
        server_type = self.type_filter.currentText()
        map_val = self.map_filter.currentText()
        sort_by_players = self.sort_checkbox.isChecked()
        only_favs = self.only_favs_checkbox.isChecked()

        filtered = self.all_servers

        if region != self.tr.get("all_regions", "Alle Regionen"):
            filtered = [s for s in filtered if s.get("region") == region]
        if density != self.tr.get("all_densities", "Alle Dichten"):
            filtered = [s for s in filtered if s.get("density") == density]
        if server_type != self.tr.get("all_types", "Alle Typen"):
            filtered = [s for s in filtered if s.get("type") == server_type]
        if map_val != self.tr.get("all_maps", "Alle Maps"):
            filtered = [s for s in filtered if s.get("map") == map_val]
        if only_favs:
            filtered = [s for s in filtered if s.get("ip_address") in self.favorites]
        if sort_by_players:
            filtered.sort(key=lambda x: x.get("clients", 0), reverse=True)

        self.populate_table(filtered)

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            self.tr.get("fav", "★"),
            self.tr.get("name", "Name"),
            self.tr.get("ip", "IP"),
            self.tr.get("region", "Region"),
            self.tr.get("map", "Map"),
            self.tr.get("players", "Spieler"),
            self.tr.get("density", "Density"),
            self.tr.get("type", "Typ")
        ])

        for row, s in enumerate(data):
            ip = s.get("ip_address", "")
            fav_mark = "★" if ip in self.favorites else "☆"
            fav_item = QTableWidgetItem(fav_mark)
            fav_item.setTextAlignment(Qt.AlignCenter)
            fav_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 0, fav_item)

            for col, key in enumerate(["name", "ip_address", "region", "map", "clients", "density", "type"], start=1):
                if key == "clients":
                    text = f"{s.get('clients', 0)}/{s.get('maxclients', 0)}"
                else:
                    text = self.tr.get(s.get(key, ""), s.get(key, ""))
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

    def handle_click(self, row, column):
        if column == 0:
            ip = self.table.item(row, 2).text()
            if ip in self.favorites:
                self.favorites.remove(ip)
            else:
                self.favorites.add(ip)
            save_favorites(self.favorites)
            self.apply_filters()
        else:
            self.try_join_server_by_row(row)

    def join_selected_server(self):
        row = self.table.currentRow()
        if row >= 0:
            self.try_join_server_by_row(row)
        else:
            QMessageBox.information(self, "Info", self.tr.get("no_selection", "Bitte zuerst einen Server auswählen."))

    def try_join_server_by_row(self, row):
        ip_port = self.table.item(row, 2).text()
        try:
            ip, port = ip_port.split(":")
            acmanager_url = f"acmanager://race/online/join?ip={ip}&httpPort={port}&password="
            os.startfile(acmanager_url)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Beitritt fehlgeschlagen:\n{e}")

if __name__ == "__main__":
    settings = load_settings()
    if settings.get("theme") == "dark":
        dark_stylesheet = """
            QWidget { background-color: #1e1e1e; color: #dddddd; }
            QComboBox, QLineEdit, QPushButton, QTableWidget, QCheckBox, QLabel {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #ffffff;
            }
        """
        app = QApplication(sys.argv)
        app.setStyleSheet(dark_stylesheet)
    else:
        app = QApplication(sys.argv)

    window = ServerBrowser()
    window.apply_theme()
    window.show()
    sys.exit(app.exec_())

