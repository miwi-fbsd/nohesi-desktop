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
from PyQt5.QtGui import QColor

FAVORITES_FILE = "favorites.json"
SETTINGS_FILE = "settings.json"

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
        settings_menu = menubar.addMenu("Settings")

        theme_menu = settings_menu.addMenu("Theme")
        light_action = QAction("Light", self)
        dark_action = QAction("Dark", self)

        light_action.triggered.connect(lambda: self.set_theme("light"))
        dark_action.triggered.connect(lambda: self.set_theme("dark"))

        theme_menu.addAction(light_action)
        theme_menu.addAction(dark_action)

    def set_theme(self, theme):
        self.settings["theme"] = theme
        save_settings(self.settings)
        self.apply_theme()

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.tr = {}
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

        self.filter_layout.addWidget(self.region_filter)
        self.filter_layout.addWidget(self.density_filter)
        self.filter_layout.addWidget(self.type_filter)
        self.filter_layout.addWidget(self.map_filter)
        self.filter_layout.addWidget(self.sort_checkbox)
        self.filter_layout.addWidget(self.only_favs_checkbox)

        self.info_label = QLabel("🔄 Loading server data...")
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
        self.info_label.setText("🔄 Loading server data...")
        loader = ServerLoader()
        loader.signals.finished.connect(self.on_servers_loaded)
        self.threadpool.start(loader)

    def on_servers_loaded(self, servers):
        self.all_servers = servers
        self.info_label.setText(f"✅ {len(self.all_servers)} servers loaded")
        self.init_filters()
        self.apply_filters()

    def init_filters(self):
        for combo in [self.region_filter, self.density_filter, self.type_filter, self.map_filter]:
            combo.blockSignals(True)
            combo.clear()

        
        regions = sorted(set(s.get("region", "") for s in self.all_servers))
        densities = sorted(set(s.get("density", "") for s in self.all_servers))
        types = sorted(set(s.get("type", "") for s in self.all_servers))
        maps = sorted(set(s.get("map", "") for s in self.all_servers))

        for values, box, default_text in zip(
            [regions, densities, types, maps],
            [self.region_filter, self.density_filter, self.type_filter, self.map_filter],
            ["All Regions", "All Traffic", "All Types", "All Maps"]):
            unique_values = sorted(set(v for v in values if v and v != default_text))
            box.addItem(default_text)
            for v in unique_values:
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

        if region != "All Regions":
            filtered = [s for s in filtered if s.get("region") == region]
        if density != "All Traffic":
            filtered = [s for s in filtered if s.get("density") == density]
        if server_type != "All Types":
            filtered = [s for s in filtered if s.get("type") == server_type]
        if map_val != "All Maps":
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
            "★",
            "Name",
            "IP",
            "Region",
            "Map",
            "Players",
            "Traffic",
            "Type"
        ])

        for row, s in enumerate(data):
            ip = s.get("ip_address", "")
            fav_mark = "★" if ip in self.favorites else "☆"
            fav_item = QTableWidgetItem(fav_mark)
            fav_item.setTextAlignment(Qt.AlignCenter)
            fav_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
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
            QMessageBox.information(self, "Info", "Please select a server first.")

    def try_join_server_by_row(self, row):
        ip_port = self.table.item(row, 2).text()
        try:
            ip, port = ip_port.split(":")
            acmanager_url = f"acmanager://race/online/join?ip={ip}&httpPort={port}&password="
            os.startfile(acmanager_url)
        except Exception as e:
            QMessageBox.information(self, "Info", f"Failed to join server:\n{e}")

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

