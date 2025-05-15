import sys
import os
import json
import requests
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QLabel, QMainWindow, QPushButton, QMessageBox, QHBoxLayout, QCheckBox,
    QAction, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QColor

def get_appdata_dir():
    appdata = os.getenv("APPDATA")
    if appdata:
        path = os.path.join(appdata, "nohesi-desktop")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path
    raise RuntimeError("APPDATA not found")

APPDATA_DIR = get_appdata_dir()
SETTINGS_FILE = os.path.join(APPDATA_DIR, "settings.json")
FAVORITES_FILE = os.path.join(APPDATA_DIR, "favorites.json")
SERVERS_FILE = os.path.join(APPDATA_DIR, "servers.json")

def load_favorites():
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, "r") as f:
                data = json.load(f)
                # Akzeptiere Listen und Strings (falls versehentlich ein einzelner Favorit gespeichert wurde)
                if isinstance(data, list):
                    return set(data)
                elif isinstance(data, str):
                    return {data}
                else:
                    return set()
    except Exception as e:
        print(f"Fehler beim Laden der Favoriten: {e}")
    return set()

def save_favorites(favs):
    try:
        with open(FAVORITES_FILE, "w") as f:
            json.dump(list(favs), f)
    except Exception as e:
        print(f"Fehler beim Speichern der Favoriten: {e}")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"language": "en", "theme": "light"}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def load_servers_cache():
    if os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_servers_cache(servers):
    with open(SERVERS_FILE, "w", encoding="utf-8") as f:
        json.dump(servers, f, indent=2, ensure_ascii=False)

def load_locale(language_code):
    if language_code == "de":
        return {
            "title": "No Hesi Server Browser",
            "Settings": "Einstellungen",
            "Theme": "Design",
            "Light": "Hell",
            "Dark": "Dunkel",
            "most_played": "Nach Spielern sortieren",
            "favorites_only": "Nur Favoriten",
            "join_now": "Jetzt beitreten",
            "All Regions": "Alle Regionen",
            "All Traffic": "Alle Verkehrsdichten",
            "All Types": "Alle Typen",
            "All Maps": "Alle Karten",
            "Info": "Info",
            "Please select a server first.": "Bitte zuerst einen Server auswählen.",
            "Failed to join server:\n{e}": "Beitritt zum Server fehlgeschlagen:\n{e}",
            "Language": "Sprache",
            "Name": "Name",
            "IP": "IP",
            "Region": "Region",
            "Map": "Karte",
            "Players": "Spieler",
            "Traffic": "Verkehr",
            "Type": "Typ",
            "loading_servers": "Server werden aktualisiert ..."
        }
    elif language_code == "en":
        return {
            "title": "No Hesi Server Browser",
            "Settings": "Settings",
            "Theme": "Theme",
            "Light": "Light",
            "Dark": "Dark",
            "most_played": "Sort by Most Played",
            "favorites_only": "Only Favorites",
            "join_now": "Join Now",
            "All Regions": "All Regions",
            "All Traffic": "All Traffic",
            "All Types": "All Types",
            "All Maps": "All Maps",
            "Info": "Info",
            "Please select a server first.": "Please select a server first.",
            "Failed to join server:\n{e}": "Failed to join server:\n{e}",
            "Language": "Language",
            "Name": "Name",
            "IP": "IP",
            "Region": "Region",
            "Map": "Map",
            "Players": "Players",
            "Traffic": "Traffic",
            "Type": "Type",
            "loading_servers": "Updating server list ..."
        }
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
        save_servers_cache(all_servers)
        self.signals.finished.emit(all_servers)

class WorkerSignals(QObject):
    finished = pyqtSignal(list)

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
        menubar.setLayoutDirection(Qt.RightToLeft)
        settings_menu = menubar.addMenu(self.tr.get("Settings", "Settings"))

        language_menu = settings_menu.addMenu(self.tr.get("Language", "Language"))
        lang_en = QAction("English", self)
        lang_de = QAction("Deutsch", self)
        lang_en.triggered.connect(lambda: self.set_language("en"))
        lang_de.triggered.connect(lambda: self.set_language("de"))
        language_menu.addAction(lang_en)
        language_menu.addAction(lang_de)

        theme_menu = settings_menu.addMenu(self.tr.get("Theme", "Theme"))
        light_action = QAction(self.tr.get("Light", "Light"), self)
        dark_action = QAction(self.tr.get("Dark", "Dark"), self)
        light_action.triggered.connect(lambda: self.set_theme("light"))
        dark_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(light_action)
        theme_menu.addAction(dark_action)

    def set_theme(self, theme):
        self.settings["theme"] = theme
        save_settings(self.settings)
        self.apply_theme()

    def set_language(self, lang):
        self.settings["language"] = lang
        save_settings(self.settings)
        self.tr = load_locale(lang)
        self.update_ui_texts()

    def update_ui_texts(self):
        self.setWindowTitle(self.tr.get("title", "No Hesi Server Browser"))
        self.sort_checkbox.setText(self.tr.get("most_played", "Sort by Most Played"))
        self.only_favs_checkbox.setText(self.tr.get("favorites_only", "Only Favorites"))
        self.join_button.setText(self.tr.get("join_now", "Join Now"))
        self.table.setHorizontalHeaderLabels([
            "★", self.tr.get("Name", "Name"), self.tr.get("IP", "IP"),
            self.tr.get("Region", "Region"), self.tr.get("Map", "Map"),
            self.tr.get("Players", "Players"), self.tr.get("Traffic", "Traffic"),
            self.tr.get("Type", "Type")
        ])
        self.init_filters()
        self.menuBar().clear()
        self.init_menu()

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.tr = load_locale(self.settings.get("language", "en"))
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
        self.region_filter.currentTextChanged.connect(self.on_filter_change)

        self.density_filter = QComboBox()
        self.density_filter.currentTextChanged.connect(self.on_filter_change)

        self.type_filter = QComboBox()
        self.type_filter.currentTextChanged.connect(self.on_filter_change)

        self.map_filter = QComboBox()
        self.map_filter.currentTextChanged.connect(self.on_filter_change)

        self.sort_checkbox = QCheckBox(self.tr.get("most_played", "Sort by Most Played"))
        self.sort_checkbox.stateChanged.connect(self.apply_filters)

        self.only_favs_checkbox = QCheckBox(self.tr.get("favorites_only", "Only Favorites"))
        self.only_favs_checkbox.setChecked(True)
        self.only_favs_checkbox.stateChanged.connect(self.apply_filters)

        self.filter_layout.addWidget(self.region_filter)
        self.filter_layout.addWidget(self.density_filter)
        self.filter_layout.addWidget(self.type_filter)
        self.filter_layout.addWidget(self.map_filter)
        self.filter_layout.addWidget(self.sort_checkbox)
        self.filter_layout.addWidget(self.only_favs_checkbox)

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setVisible(False)

        self.table = QTableWidget()
        self.table.cellDoubleClicked.connect(self.handle_click)

        self.join_button = QPushButton(self.tr.get("join_now", "Join Now"))
        self.join_button.setFixedHeight(40)
        font = self.join_button.font()
        font.setPointSize(11)
        self.join_button.setFont(font)
        self.join_button.clicked.connect(self.join_selected_server)

        self.layout.addLayout(self.filter_layout)
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.join_button)
        self.layout.addWidget(self.info_label)  # Info-Label jetzt unter Join Now

        self.all_servers = load_servers_cache()
        self.init_filters()
        self.apply_filters()
        self.apply_theme()

        self.load_all_servers_async()

    def load_all_servers_async(self):
        loading_text = self.tr.get("loading_servers", "Server werden aktualisiert ...")
        self.info_label.setText(loading_text)
        self.info_label.setVisible(True)
        self._load_start_time = time.time()
        loader = ServerLoader()
        loader.signals.finished.connect(self.on_servers_loaded)
        self.threadpool.start(loader)

    def on_servers_loaded(self, servers):
        elapsed = time.time() - getattr(self, "_load_start_time", time.time())
        count = len(servers)
        if self.tr.get("language", "en") == "de":
            info = f"Server aktualisiert: {count} Server, Dauer: {elapsed:.2f} Sekunden"
        else:
            info = f"Servers updated: {count} servers, took {elapsed:.2f} seconds"
        self.all_servers = servers
        self.only_favs_checkbox.setChecked(False)
        self.info_label.setText(info)
        self.info_label.setVisible(True)
        QTimer.singleShot(3500, lambda: self.info_label.setVisible(False))
        self.init_filters()
        self.apply_filters()

    def init_filters(self):
        for combo, default_text, setting_key in zip(
            [self.region_filter, self.density_filter, self.type_filter, self.map_filter],
            [self.tr.get("All Regions", "All Regions"), self.tr.get("All Traffic", "All Traffic"),
             self.tr.get("All Types", "All Types"), self.tr.get("All Maps", "All Maps")],
            ["last_region", "last_density", "last_type", "last_map"]
        ):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(default_text)
            combo.blockSignals(False)

        regions = sorted(set(s.get("region", "") for s in self.all_servers))
        densities = sorted(set(s.get("density", "") for s in self.all_servers))
        types = sorted(set(s.get("type", "") for s in self.all_servers))
        maps = sorted(set(s.get("map", "") for s in self.all_servers))

        for values, box in zip(
            [regions, densities, types, maps],
            [self.region_filter, self.density_filter, self.type_filter, self.map_filter]
        ):
            unique_values = sorted(set(v for v in values if v))
            for v in unique_values:
                if v:
                    box.addItem(v)

        self.region_filter.setCurrentText(self.settings.get("last_region", self.tr.get("All Regions", "All Regions")))
        self.density_filter.setCurrentText(self.settings.get("last_density", self.tr.get("All Traffic", "All Traffic")))
        self.type_filter.setCurrentText(self.settings.get("last_type", self.tr.get("All Types", "All Types")))
        self.map_filter.setCurrentText(self.settings.get("last_map", self.tr.get("All Maps", "All Maps")))

    def on_filter_change(self):
        self.settings["last_region"] = self.region_filter.currentText()
        self.settings["last_density"] = self.density_filter.currentText()
        self.settings["last_type"] = self.type_filter.currentText()
        self.settings["last_map"] = self.map_filter.currentText()
        save_settings(self.settings)
        self.apply_filters()

    def apply_filters(self):
        region = self.region_filter.currentText()
        density = self.density_filter.currentText()
        server_type = self.type_filter.currentText()
        map_val = self.map_filter.currentText()
        sort_by_players = self.sort_checkbox.isChecked()
        only_favs = self.only_favs_checkbox.isChecked()

        filtered = self.all_servers

        if region != self.tr.get("All Regions", "All Regions"):
            filtered = [s for s in filtered if s.get("region") == region]
        if density != self.tr.get("All Traffic", "All Traffic"):
            filtered = [s for s in filtered if s.get("density") == density]
        if server_type != self.tr.get("All Types", "All Types"):
            filtered = [s for s in filtered if s.get("type") == server_type]
        if map_val != self.tr.get("All Maps", "All Maps"):
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
            "★", self.tr.get("Name", "Name"), self.tr.get("IP", "IP"),
            self.tr.get("Region", "Region"), self.tr.get("Map", "Map"),
            self.tr.get("Players", "Players"), self.tr.get("Traffic", "Traffic"),
            self.tr.get("Type", "Type")
        ])

        for row, s in enumerate(data):
            ip = s.get("ip_address", "")
            fav_mark = "★" if ip in self.favorites else "☆"
            fav_item = QTableWidgetItem(fav_mark)
            fav_item.setTextAlignment(Qt.AlignCenter)
            fav_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            if self.settings.get("theme") == "dark":
                fav_item.setBackground(QColor("#2b2b2b"))
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
            QMessageBox.information(self, self.tr.get("Info", "Info"),
                                     self.tr.get("Please select a server first.", "Please select a server first."))

    def try_join_server_by_row(self, row):
        ip_port = self.table.item(row, 2).text()
        try:
            ip, port = ip_port.split(":")
            acmanager_url = f"acmanager://race/online/join?ip={ip}&httpPort={port}&password="
            os.startfile(acmanager_url)
        except Exception as e:
            QMessageBox.information(self, self.tr.get("Info", "Info"),
                                     self.tr.get("Failed to join server:\n{e}", f"Failed to join server:\n{e}").format(e=e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ServerBrowser()
    window.apply_theme()
    window.show()
    sys.exit(app.exec_())
