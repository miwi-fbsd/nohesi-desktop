import json
import os
import requests

AUTH_FILE = "auth.json"

def load_auth():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            return json.load(f)
    return None

def save_auth(auth):
    with open(AUTH_FILE, "w") as f:
        json.dump(auth, f, indent=2)

def register_user(name, server_url):
    resp = requests.post(f"{server_url}/register", json={"name": name})
    resp.raise_for_status()
    data = resp.json()
    auth = {"name": name, "token": data["token"]}
    save_auth(auth)
    return auth

def post_status(auth, ip, server_url):
    headers = {
        "Authorization": f"Bearer {auth['token']}",
        "Content-Type": "application/json"
    }
    resp = requests.post(f"{server_url}/status", json={"ip": ip}, headers=headers)
    resp.raise_for_status()
    return resp.json()

def add_friend(auth, friend_name, server_url):
    headers = {
        "Authorization": f"Bearer {auth['token']}",
        "Content-Type": "application/json"
    }
    resp = requests.post(f"{server_url}/friends/request", json={"friend": friend_name}, headers=headers)
    resp.raise_for_status()
    return resp.json()

def get_requests(auth, server_url):
    headers = {
        "Authorization": f"Bearer {auth['token']}",
        "Content-Type": "application/json"
    }
    resp = requests.get(f"{server_url}/friends/requests", headers=headers)
    resp.raise_for_status()
    return resp.json()["incoming_requests"]

def accept_friend(auth, requester, server_url):
    headers = {
        "Authorization": f"Bearer {auth['token']}",
        "Content-Type": "application/json"
    }
    resp = requests.post(f"{server_url}/friends/accept", json={"friend": requester}, headers=headers)
    resp.raise_for_status()
    return resp.json()

def reject_friend(auth, requester, server_url):
    headers = {
        "Authorization": f"Bearer {auth['token']}",
        "Content-Type": "application/json"
    }
    resp = requests.post(f"{server_url}/friends/reject", json={"friend": requester}, headers=headers)
    resp.raise_for_status()
    return resp.json()

def get_online_friends(auth, server_url):
    headers = {
        "Authorization": f"Bearer {auth['token']}",
        "Content-Type": "application/json"
    }
    resp = requests.get(f"{server_url}/friends/online", headers=headers)
    resp.raise_for_status()
    return resp.json()["online_friends"]

def get_all_friends(auth, server_url):
    headers = {
        "Authorization": f"Bearer {auth['token']}",
        "Content-Type": "application/json"
    }
    resp = requests.get(f"{server_url}/friends/list", headers=headers)
    resp.raise_for_status()
    return resp.json()["friends"]

def remove_friend(auth, friend_name, server_url):
    headers = {
        "Authorization": f"Bearer {auth['token']}",
        "Content-Type": "application/json"
    }
    resp = requests.post(f"{server_url}/friends/remove", json={"friend": friend_name}, headers=headers)
    resp.raise_for_status()
    return resp.json()
