# Import needed libraries

import requests
import json
import httpx
import sqlite3
import License_cURL
import os
import glob
import inquirer
import uuid
import random

from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH
import base64


# Hola proxy

class Settings:
    def __init__(self, userCountry: str = None, randomProxy: bool = False) -> None:
        self.randomProxy = randomProxy
        self.userCountry = userCountry
        self.ccgi_url = "https://client.hola.org/client_cgi/"
        self.ext_ver = self.get_ext_ver()
        self.ext_browser = "chrome"
        self.user_uuid = uuid.uuid4().hex
        self.user_agent = "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"
        self.product = "cws"
        self.port_type_choice: str
        self.zoneAvailable = ["AR", "AT", "AU", "BE", "BG", "BR", "CA", "CH", "CL", "CO", "CZ", "DE", "DK", "ES", "FI",
                              "FR", "GR", "HK", "HR", "HU", "ID", "IE", "IL", "IN", "IS", "IT", "JP", "KR", "MX", "NL",
                              "NO", "NZ", "PL", "RO", "RU", "SE", "SG", "SK", "TR", "UK", "US", "GB"]

    def get_ext_ver(self) -> str:
        about = httpx.get("https://hola.org/access/my/settings#/about").text
        if 'window.pub_config.init({"ver":"' in about:
            version = about.split('window.pub_config.init({"ver":"')[1].split('"')[0]
            return version

        # last know working version
        return "1.199.485"


class Engine:
    def __init__(self, Settings) -> None:
        self.settings = Settings

    def get_proxy(self, tunnels, tls=False) -> str:
        login = f"user-uuid-{self.settings.user_uuid}"
        proxies = dict(tunnels)
        protocol = "https" if tls else "http"
        for k, v in proxies["ip_list"].items():
            return "%s://%s:%s@%s:%d" % (
                protocol,
                login,
                proxies["agent_key"],
                k if tls else v,
                proxies["port"][self.settings.port_type_choice],
            )

    def generate_session_key(self, timeout: float = 10.0) -> json:
        post_data = {"login": "1", "ver": self.settings.ext_ver}
        return httpx.post(
            f"{self.settings.ccgi_url}background_init?uuid={self.settings.user_uuid}",
            json=post_data,
            headers={"User-Agent": self.settings.user_agent},
            timeout=timeout,
        ).json()["key"]

    def zgettunnels(
            self, session_key: str, country: str, timeout: float = 10.0
    ) -> json:
        qs = {
            "country": country.lower(),
            "limit": 1,
            "ping_id": random.random(),
            "ext_ver": self.settings.ext_ver,
            "browser": self.settings.ext_browser,
            "uuid": self.settings.user_uuid,
            "session_key": session_key,
        }

        return httpx.post(
            f"{self.settings.ccgi_url}zgettunnels", params=qs, timeout=timeout
        ).json()


class Hola:
    def __init__(self, Settings) -> None:
        self.myipUri: str = "https://hola.org/myip.json"
        self.settings = Settings

    def get_country(self) -> str:

        if not self.settings.randomProxy and not self.settings.userCountry:
            self.settings.userCountry = httpx.get(self.myipUri).json()["country"]

        if (
                not self.settings.userCountry in self.settings.zoneAvailable
                or self.settings.randomProxy
        ):
            self.settings.userCountry = random.choice(self.settings.zoneAvailable)

        return self.settings.userCountry


def init_proxy(data):
    settings = Settings(
        data["zone"]
    )
    settings.port_type_choice = data[
        "port"
    ]

    hola = Hola(settings)
    engine = Engine(settings)

    userCountry = hola.get_country()
    session_key = engine.generate_session_key()
    #    time.sleep(10)
    tunnels = engine.zgettunnels(session_key, userCountry)

    return engine.get_proxy(tunnels)


# Get current working directory
main_directory = os.getcwd()

# Create database and table for local key caching if they don't exist
if not os.path.isfile(f"{main_directory}/database.db"):
    dbconnection = sqlite3.connect("database.db")
    dbcursor = dbconnection.cursor()
    dbcursor.execute('CREATE TABLE IF NOT EXISTS "DATABASE" ( "pssh" TEXT, "keys" TEXT, PRIMARY KEY("pssh") )')
    dbconnection.close()


# Define key cache function


def key_cache(pssh: str, db_keys: str):
    dbconnection = sqlite3.connect("database.db")
    dbcursor = dbconnection.cursor()
    dbcursor.execute("INSERT or REPLACE INTO database VALUES (?, ?)", (pssh, db_keys))
    dbconnection.commit()
    dbconnection.close()


# Making sure a .wvd file exists and using that as the CDM
try:
    cdm = glob.glob(f'{main_directory}/*.wvd')[0]
except:
    cdm = None
    print(f"Please place a WVD in {main_directory}")
    print(f"Use option 3 of TPD-Keys if you do not have your own.")


# Define key retrieval function
def retrieve_keys(proxy_used: str = None, headers: list = None,
                  json_data: json = None, device: str = cdm):
    pssh = input("PSSH: ")
    licence_url = input("License URL: ")
    if proxy_used is not None:
        proxy = init_proxy({"zone": proxy_used, "port": "peer"})
        proxies = {
            "http": proxy
        }
    else:
        proxies = None
    challenge_pssh = PSSH(pssh)
    try:
        device = Device.load(device)
    except:
        print(f"Please place a WVD in {main_directory}")
        exit()
    cdm = Cdm.from_device(device)
    session_id = cdm.open()
    challenge = cdm.get_license_challenge(session_id, challenge_pssh)
    license = requests.post(licence_url, data=challenge, proxies=proxies, headers=headers, json=json_data)
    license.raise_for_status()
    cdm.parse_license(session_id, license.content)
    db_keys = ''
    for key in cdm.get_keys(session_id):
        if key.type != 'SIGNING':
            db_keys += f'{key.kid.hex}:{key.key.hex()}\n'
            key_cache(pssh=pssh, db_keys=db_keys)
    return db_keys

# Define retrieve keys remotely function


def retrieve_keys_remotely(proxy_used: str = None):
    api_url = "https://api.cdrm-project.com"
    api_device = "CDM"
    pssh = input("PSSH: ")
    license_url = input("License URL: ")
    if proxy_used is not None:
        proxy = init_proxy({"zone": proxy_used, "port": "peer"})
        proxies = {
            "http": proxy
        }
    else:
        proxies = None
    x_headers = {
        "X-Secret-Key": "fvYBh0C3fRAxlvyJcynD1see3GmNbIiC"
    }
    open_session = requests.get(url=f"{api_url}/{api_device}/open", headers=x_headers)

    session_id = open_session.json()["data"]["session_id"]

    license_challenge_json_data = {
        "session_id": session_id,
        "init_data": pssh
    }

    licence_challenge = requests.post(url=f"{api_url}/{api_device}/get_license_challenge/AUTOMATIC", headers=x_headers,
                                      json=license_challenge_json_data)

    license_message = licence_challenge.json()["data"]["challenge_b64"]

    license = requests.post(
        headers=License_cURL.headers,
        proxies=proxies,
        url=license_url,
        data=base64.b64decode(license_message)
    )

    parse_license_json_data = {
        "session_id": session_id,
        "license_message": f"{base64.b64encode(license.content).decode()}"
    }

    requests.post(f"{api_url}/{api_device}/parse_license", json=parse_license_json_data,
                                  headers=x_headers)

    get_keys = requests.post(f"{api_url}/{api_device}/get_keys/ALL",
                             json={"session_id": session_id}, headers=x_headers)
    db_keys = ''
    for key in get_keys.json()["data"]["keys"]:
        if not key["type"] == "SIGNING":
            db_keys += f"{key['key_id']}:{key['key']}\n"
            key_cache(pssh=pssh, db_keys=db_keys)

    requests.get(f"{api_url}/{api_device}/close/{session_id}", headers=x_headers)

    return db_keys



# Defining service prompt function


def service_prompt():
    service_prompt = [
        inquirer.List('Service',
                      message="Please choose a service",
                      choices=['Generic', 'Generic with headers from Licence cURL', 'Remote'],
                      ),
    ]
    service_selected = inquirer.prompt(service_prompt)

    proxy_needed_prompt = [
        inquirer.List('Proxy',
                      message="Will you need a proxy?",
                      choices=['Yes', 'No'],
                      ),
    ]

    proxy_needed = inquirer.prompt(proxy_needed_prompt)
    if proxy_needed["Proxy"] == "Yes":
        allowed_countries = [
            "AR", "AT", "AU", "BE", "BG", "BR", "CA", "CH", "CL", "CO", "CZ", "DE", "DK", "ES", "FI",
            "FR", "GR", "HK", "HR", "HU", "ID", "IE", "IL", "IN", "IS", "IT", "JP", "KR", "MX", "NL",
            "NO", "NZ", "PL", "RO", "RU", "SE", "SG", "SK", "TR", "UK", "US", "GB"
        ]
        proxy_available = [
            inquirer.List('Proxys available',
                          message="Please choose a country",
                          choices=allowed_countries
                          ),
        ]
        selected_proxy = inquirer.prompt(proxy_available)
        return service_selected["Service"], selected_proxy["Proxys available"]
    else:
        selected_proxy = None
        return service_selected["Service"], selected_proxy


# Define variables for the service and proxy wanted


service_selected, selected_proxy = service_prompt()


if service_selected == "Generic":
    print(f"\n{retrieve_keys(proxy_used=selected_proxy)}")
elif service_selected == "Generic with headers from Licence cURL":
    print(f"\n{retrieve_keys(proxy_used=selected_proxy, headers=License_cURL.headers)}")
elif service_selected == "Remote":
    print(f"\n{retrieve_keys_remotely(proxy_used=selected_proxy)}")

