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
from PyQt5.QtGui import QColor, QIcon
import PyQt5.QtWidgets as QtWidgets
from friends_client import load_auth, register_user, get_all_friends, add_friend, remove_friend, get_requests, accept_friend, reject_friend, post_status

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
CARS_FILE = os.path.join(APPDATA_DIR, "cars.json")

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
            "loading_servers": "Server werden aktualisiert ...",
            "Link copied:\n{link}": "Link kopiert:\n{link}",
            "Failed to copy link:\n{e}": "Fehler beim Kopieren des Links:\n{e}",
            "Copy server link": "Server-Link kopieren",
            "friends": "Freunde",
            "add_friend": "Freund hinzufügen",
            "friend_added": "Freund hinzugefügt.",
            "remove_friend": "Freund entfernen",
            "friend_removed": "Freund entfernt.",
            "no_friend_selected": "Bitte zuerst einen Freund auswählen.",
            "show_requests": "Freundschaftsanfragen anzeigen",
            "friend_requests": "Freundschaftsanfragen",
            "pending_requests": "Offene Anfragen:",
            "accept_friend": "Annehmen",
            "reject_friend": "Ablehnen",
            "no_requests": "Keine offenen Freundschaftsanfragen."
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
            "loading_servers": "Updating server list ...",
            "Link copied:\n{link}": "Link copied:\n{link}",
            "Failed to copy link:\n{e}": "Failed to copy link:\n{e}",
            "Copy server link": "Copy server link",
            "friends": "Friends",
            "add_friend": "Add Friend",
            "friend_added": "Friend added.",
            "remove_friend": "Remove Friend",
            "friend_removed": "Friend removed.",
            "no_friend_selected": "Please select a friend first.",
            "show_requests": "Show Friend Requests",
            "friend_requests": "Friend Requests",
            "pending_requests": "Pending Requests:",
            "accept_friend": "Accept",
            "reject_friend": "Reject",
            "no_requests": "No pending friend requests."
        }
    return {}

def load_cars_json(filepath_or_url):
    """
    Lädt die Car-Liste aus einer lokalen Datei oder URL.
    Gibt eine Liste von Car-Modelnamen zurück.
    """
    try:
        if filepath_or_url.startswith("http"):
            resp = requests.get(filepath_or_url)
            if resp.status_code == 200 and resp.content:
                try:
                    data = resp.json()
                except Exception as e:
                    print(f"Fehler beim Parsen der Car-JSON: {e}")
                    return []
                # Speichere die Car-JSON lokal für Offline-Nutzung
                with open(CARS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                print(f"Fehler beim Laden der Car-Liste: HTTP {resp.status_code}")
                return []
        else:
            with open(filepath_or_url, "r", encoding="utf-8") as f:
                data = json.load(f)
        return [car["model"] for car in data.get("data", []) if car.get("available", True)]
    except Exception as e:
        print(f"Fehler beim Laden der Car-Liste: {e}")
        return []

def get_servers_for_car(car_model, tier=None):
    """
    Holt die Serverliste für ein bestimmtes Auto und Tier von der API.
    Wenn kein Tier angegeben ist, wird das niedrigste verfügbare Tier aus der Car-JSON verwendet.
    """
    try:
        # Lade die Car-Liste lokal
        if os.path.exists(CARS_FILE):
            with open(CARS_FILE, "r", encoding="utf-8") as f:
                cars_data = json.load(f)
            car_entry = next((c for c in cars_data.get("data", []) if c["model"] == car_model), None)
            if car_entry and car_entry.get("tier"):
                # Nimm das niedrigste Tier, falls nicht explizit gesetzt
                tier_keys = sorted(int(k) for k in car_entry["tier"].keys())
                tier = tier_keys[0] if tier is None else tier
            else:
                tier = 0
        else:
            tier = 0

        car_query = f"{car_model}|{tier}"
        url = f"https://hub.nohesi.gg/servers?car={car_query}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("servers", [])
    except Exception as e:
        print(f"Fehler beim Car-Server-API-Call: {e}")
        return []

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

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        layout = QVBoxLayout()
        label = QLabel(
            "<b>No Hesi Server Browser</b><br>"
            "Autor: miwitv<br><br>"
            "<a style='color:#9147ff;' href='https://twitch.tv/miwiland'>Twitch: twitch.tv/miwiland</a><br>"
            "<a style='color:#2dba4e;' href='https://github.com/miwi-fbsd/nohesi-desktop'>GitHub: https://github.com/miwi-fbsd/nohesi-desktop</a>"
        )
        label.setOpenExternalLinks(True)
        layout.addWidget(label)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)
        self.setLayout(layout)

class FriendsDialog(QDialog):
    def __init__(self, parent, auth, server_url, tr):
        super().__init__(parent)
        self.setWindowTitle(tr.get("friends", "Friends"))
        self.auth = auth
        self.server_url = server_url
        self.tr = tr
        self.layout = QVBoxLayout()
        self.list_widget = QtWidgets.QListWidget()
        self.refresh_friends()
        self.layout.addWidget(self.list_widget)
        self.input = QtWidgets.QLineEdit()
        self.input.setPlaceholderText(tr.get("add_friend", "Add Friend"))
        self.layout.addWidget(self.input)
        add_btn = QPushButton(tr.get("add_friend", "Add Friend"))
        add_btn.clicked.connect(self.add_friend)
        self.layout.addWidget(add_btn)
        remove_btn = QPushButton(tr.get("remove_friend", "Remove Friend"))
        remove_btn.clicked.connect(self.remove_friend)
        self.layout.addWidget(remove_btn)
        # Button für Freundschaftsanfragen
        self.requests_btn = QPushButton(tr.get("show_requests", "Freundschaftsanfragen anzeigen"))
        self.requests_btn.clicked.connect(self.show_requests_dialog)
        self.layout.addWidget(self.requests_btn)
        self.setLayout(self.layout)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_friends)
        self.refresh_timer.start(10000)  # Refresh every 10 seconds

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(15000)  # Update status every 15 seconds

    def refresh_friends(self):
        self.list_widget.clear()
        try:
            friends = get_all_friends(self.auth, self.server_url)
            for f in friends:
                name = f["name"] if isinstance(f, dict) else f
                online = f.get("online", False) if isinstance(f, dict) else False
                item = name + (" (online)" if online else "")
                self.list_widget.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, self.tr.get("friends", "Friends"), str(e))

    def add_friend(self):
        name = self.input.text().strip()
        if not name:
            return
        try:
            add_friend(self.auth, name, self.server_url)
            QMessageBox.information(self, self.tr.get("friends", "Friends"), self.tr.get("friend_added", "Friend added."))
            self.refresh_friends()
            self.input.clear()
        except Exception as e:
            QMessageBox.warning(self, self.tr.get("friends", "Friends"), str(e))

    def remove_friend(self):
        selected = self.list_widget.currentItem()
        if not selected:
            QMessageBox.information(self, self.tr.get("friends", "Friends"), self.tr.get("no_friend_selected", "Please select a friend first."))
            return
        name = selected.text().split(" ")[0]
        try:
            remove_friend(self.auth, name, self.server_url)
            QMessageBox.information(self, self.tr.get("friends", "Friends"), self.tr.get("friend_removed", "Friend removed."))
            self.refresh_friends()
        except Exception as e:
            QMessageBox.warning(self, self.tr.get("friends", "Friends"), str(e))

    def show_requests_dialog(self):
        try:
            requests = get_requests(self.auth, self.server_url)
            if not requests:
                QMessageBox.information(self, self.tr.get("friends", "Friends"), self.tr.get("no_requests", "Keine offenen Freundschaftsanfragen."))
                return
            dlg = QDialog(self)
            dlg.setWindowTitle(self.tr.get("friend_requests", "Freundschaftsanfragen"))
            vbox = QVBoxLayout()
            label = QLabel(self.tr.get("pending_requests", "Offene Anfragen:"))
            vbox.addWidget(label)
            list_widget = QtWidgets.QListWidget()
            for r in requests:
                list_widget.addItem(r)
            vbox.addWidget(list_widget)
            btn_accept = QPushButton(self.tr.get("accept_friend", "Annehmen"))
            btn_reject = QPushButton(self.tr.get("reject_friend", "Ablehnen"))
            hbox = QHBoxLayout()
            hbox.addWidget(btn_accept)
            hbox.addWidget(btn_reject)
            vbox.addLayout(hbox)
            dlg.setLayout(vbox)
            def accept_selected():
                item = list_widget.currentItem()
                if not item:
                    return
                try:
                    accept_friend(self.auth, item.text(), self.server_url)
                    QMessageBox.information(self, self.tr.get("friends", "Friends"), self.tr.get("friend_added", "Friend added."))
                    list_widget.takeItem(list_widget.currentRow())
                    self.refresh_friends()
                except Exception as e:
                    QMessageBox.warning(self, self.tr.get("friends", "Friends"), str(e))
            def reject_selected():
                item = list_widget.currentItem()
                if not item:
                    return
                try:
                    reject_friend(self.auth, item.text(), self.server_url)
                    QMessageBox.information(self, self.tr.get("friends", "Friends"), self.tr.get("friend_removed", "Friend removed."))
                    list_widget.takeItem(list_widget.currentRow())
                    self.refresh_friends()
                except Exception as e:
                    QMessageBox.warning(self, self.tr.get("friends", "Friends"), str(e))
            btn_accept.clicked.connect(accept_selected)
            btn_reject.clicked.connect(reject_selected)
            dlg.exec_()
        except Exception as e:
            QMessageBox.warning(self, self.tr.get("friends", "Friends"), str(e))

    def update_status(self):
        try:
            # Replace "127.0.0.1" with the actual IP if available
            post_status(self.auth, "127.0.0.1", self.server_url)
        except Exception as e:
            print(f"Error updating status: {e}")

class UsernameDialog(QDialog):
    def __init__(self, tr, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr.get("add_friend", "Benutzername wählen"))
        self.layout = QVBoxLayout()
        self.label = QLabel(tr.get("add_friend", "Bitte gib deinen Benutzernamen ein:"))
        self.layout.addWidget(self.label)
        self.input = QtWidgets.QLineEdit()
        self.layout.addWidget(self.input)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        self.setLayout(self.layout)
    def get_username(self):
        return self.input.text().strip()

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

        # About-Menüpunkt jetzt im Settings-Menü
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        settings_menu.addAction(about_action)

        # Freunde-Menüeintrag direkt ohne Untermenü
        friends_action = QAction(self.tr.get("friends", "Friends"), self)
        friends_action.triggered.connect(self.show_friends_dialog)
        menubar.addAction(friends_action)

    def show_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec_()

    def show_friends_dialog(self):
        if not self.auth:
            QMessageBox.warning(self, self.tr.get("friends", "Friends"), "Bitte zuerst einloggen/registrieren!")
            return
        dlg = FriendsDialog(self, self.auth, self.server_url, self.tr)
        dlg.exec_()

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
            self.tr.get("Type", "Type"), "Tier", "VIP"
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
        self.server_url = "http://192.168.1.100:8000"  # Passe ggf. an
        self.auth = load_auth()
        if not self.auth:
            # Username abfragen
            dlg = UsernameDialog(self.tr, self)
            if dlg.exec_() == QDialog.Accepted:
                username = dlg.get_username()
                if username:
                    try:
                        self.auth = register_user(username, self.server_url)
                        QMessageBox.information(self, "Info", f"Registrierung erfolgreich! Willkommen, {username}.")
                    except Exception as e:
                        QMessageBox.critical(self, "Fehler", f"Registrierung fehlgeschlagen: {e}")
                        sys.exit(1)
                else:
                    QMessageBox.critical(self, "Fehler", "Kein Benutzername eingegeben.")
                    sys.exit(1)
            else:
                sys.exit(0)

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

        self.car_filter = QComboBox()
        self.car_filter.addItem("All Cars")
        self.car_filter.currentTextChanged.connect(self.on_filter_change)

        self.sort_checkbox = QCheckBox(self.tr.get("most_played", "Sort by Most Played"))
        self.sort_checkbox.stateChanged.connect(self.apply_filters)

        self.only_favs_checkbox = QCheckBox(self.tr.get("favorites_only", "Only Favorites"))
        self.only_favs_checkbox.setChecked(True)
        self.only_favs_checkbox.stateChanged.connect(self.apply_filters)

        self.filter_layout.addWidget(self.region_filter)
        self.filter_layout.addWidget(self.density_filter)
        self.filter_layout.addWidget(self.type_filter)
        self.filter_layout.addWidget(self.map_filter)
        self.filter_layout.addWidget(self.car_filter)  # Car-Filter hinzufügen
        self.filter_layout.addWidget(self.sort_checkbox)
        self.filter_layout.addWidget(self.only_favs_checkbox)

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setVisible(False)

        self.table = QTableWidget()
        self.table.cellDoubleClicked.connect(self.handle_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_context_menu)

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
        self.cars_list = load_cars_json("https://hub.nohesi.gg/servers/cars")
        for car in sorted(self.cars_list):
            self.car_filter.addItem(car)
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

        # Car-Filter aktualisieren
        current_car = self.car_filter.currentText()
        self.car_filter.blockSignals(True)
        self.car_filter.clear()
        self.car_filter.addItem("All Cars")
        for car in sorted(self.cars_list):
            self.car_filter.addItem(car)
        self.car_filter.setCurrentText(current_car if current_car in self.cars_list else "All Cars")
        self.car_filter.blockSignals(False)

        # Favoriten-Checkbox initialisieren:
        if self.favorites:
            self.only_favs_checkbox.setChecked(True)
        else:
            # Wenn keine Favoriten, dann letzte Einstellung oder Default
            last_checked = self.settings.get("only_favs_checked", False)
            self.only_favs_checkbox.setChecked(last_checked)

    def on_filter_change(self):
        self.settings["last_region"] = self.region_filter.currentText()
        self.settings["last_density"] = self.density_filter.currentText()
        self.settings["last_type"] = self.type_filter.currentText()
        self.settings["last_map"] = self.map_filter.currentText()
        # Speichere auch den Zustand der Favoriten-Checkbox
        self.settings["only_favs_checked"] = self.only_favs_checkbox.isChecked()
        save_settings(self.settings)
        self.apply_filters()

    def apply_filters(self):
        region = self.region_filter.currentText()
        density = self.density_filter.currentText()
        server_type = self.type_filter.currentText()
        map_val = self.map_filter.currentText()
        car_model = self.car_filter.currentText()
        sort_by_players = self.sort_checkbox.isChecked()

        # Favoriten-Logik: Nur wenn Favoriten vorhanden sind, Checkbox aktiv lassen
        if self.favorites:
            only_favs = self.only_favs_checkbox.isChecked()
        else:
            only_favs = False
            self.only_favs_checkbox.setChecked(False)

        # Car-Filter: Hole Server direkt von der API, wenn ein Auto gewählt ist
        if car_model != "All Cars":
            print(f"[DEBUG] apply_filters: car_model={car_model}")  # Debug-Ausgabe
            filtered = get_servers_for_car(car_model, tier=None)  # tier=None, damit das niedrigste Tier gewählt wird
        else:
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
        # Neue Spalte für VIP-Slots einfügen (insgesamt 10 Spalten)
        self.table.setRowCount(len(data))
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "★", self.tr.get("Name", "Name"), self.tr.get("IP", "IP"),
            self.tr.get("Region", "Region"), self.tr.get("Map", "Map"),
            self.tr.get("Players", "Players"), self.tr.get("Traffic", "Traffic"),
            self.tr.get("Type", "Type"), "Tier", "VIP"
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

            # Standardspalten
            for col, key in enumerate(["name", "ip_address", "region", "map", "clients", "density", "type"], start=1):
                if key == "clients":
                    text = f"{s.get('clients', 0)}/{s.get('maxclients', 0)}"
                else:
                    text = self.tr.get(s.get(key, ""), s.get(key, ""))
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, col, item)

            # Tier-Spalte (Spalte 8)
            tier_value = ""
            if "type" in s and isinstance(s["type"], str) and s["type"].lower().startswith("tier"):
                tier_value = s["type"].replace("Tier", "")
            elif "tier3_cars" in s:
                tier_value = "3"
            else:
                tier_value = ""
            tier_item = QTableWidgetItem(str(tier_value))
            tier_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 8, tier_item)

            # VIP-Slots-Spalte (Spalte 9)
            vip = s.get("vip_slots", 0)
            max_vip = s.get("max_vip_slots", 0)
            vip_text = f"{vip}/{max_vip}" if max_vip else str(vip)
            vip_item = QTableWidgetItem(vip_text)
            vip_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 9, vip_item)

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

    def show_table_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        menu = QtWidgets.QMenu(self)
        copy_action = menu.addAction(self.tr.get("Copy server link", "Copy server link"))
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == copy_action:
            self.copy_selected_server_link(row=index.row())

    def copy_selected_server_link(self, row=None):
        if row is None:
            row = self.table.currentRow()
        if row < 0:
            return
        ip_port = self.table.item(row, 2).text()
        try:
            ip, port = ip_port.split(":")
            link = f"https://acstuff.club/s/q:race/online/join?ip={ip}&httpPort={port}"
            clipboard = QApplication.clipboard()
            clipboard.setText(link)
        except Exception:
            pass

if __name__ == "__main__":
    # Icon-Pfad absolut auflösen (für PyInstaller: sys._MEIPASS prüfen)
    if hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    icon_path = os.path.join(base_dir, "nohesi.ico")

    app = QApplication(sys.argv)
    # Setze das Icon für das QApplication-Objekt (Taskbar-Icon)
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = ServerBrowser()
    # Setze das Icon für das Fenster (Window-Icon)
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    # Stelle sicher, dass das Fenster als Hauptfenster erkannt wird (Taskbar-Icon)
    window.setWindowFlags(window.windowFlags() & ~Qt.WindowStaysOnTopHint)
    window.apply_theme()
    window.show()
    sys.exit(app.exec_())
`