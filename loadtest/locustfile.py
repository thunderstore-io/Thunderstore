from random import choice, random

from locust import HttpUser, task


BOOLS = ["deprecated", "nsfw"]
ORDERING = ["last-updated", "most-downloaded", "newest", "top-rated"]
QUERIES = ["character", "ror2", "unity"]
SECTIONS = ["mods", "modpacks"]


class AnonymousUser(HttpUser):
    @task
    def index(self):
        url = f"/?ordering={choice(ORDERING)}"
        url += f"&section={choice(SECTIONS)}" if random() < 0.5 else ""
        url += f"&q={choice(QUERIES)}" if random() < 0.5 else ""
        url += f"&{choice(BOOLS)}=on" if random() < 0.5 else ""
        self.client.get(url)

    @task
    def api(self):
        url = f"/api/v1/package/"
        self.client.get(url)
