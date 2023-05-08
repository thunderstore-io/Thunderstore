import base64
import io
import zipfile
import yaml

from celery import shared_task
from typing import Dict
from thunderstore.core.settings import CeleryQueues
from thunderstore.modpacks.models.legacyprofile import LegacyProfile, LegacyProfileMetaData

def parse_package_name_and_team(s: str):
    reversed_splitted = "".join(reversed(s)).split("-", maxsplit=1)
    name = "".join(reversed(reversed_splitted[0]))
    team = "".join(reversed(reversed_splitted[1]))
    return (name, team)


def generate_mod_metadata(mod: Dict, game: str):
    name, team = parse_package_name_and_team(mod["name"])
    version = ("%s.%s.%s" % (mod["version"]["major"], mod["version"]["minor"], mod["version"]["patch"]))
    return {
        "name": name,
        "team": team,
        "version": version,
        "enabled": mod["enabled"],
        "url": ("https://thunderstore.io/c/%s/p/%s/%s/v/%s" % (
            game,
            team,
            name,
            version
        ))
    }

# TODO: ERROR HANDLING MISSING
@shared_task(queue=CeleryQueues.Default)
def create_legacy_profile_metadata(
    profile: LegacyProfile,
) -> None:
    profile_meta_data = {}
    f = profile.file.file.open('r')
    with io.BytesIO(base64.b64decode(f.read())) as inmemoryfile:
        zip_ref = zipfile.ZipFile(inmemoryfile, 'r')
        zip_infos = zip_ref.infolist()
        for x in zip_infos:
            if x.filename == "export.r2x":
                yaml_dict = yaml.safe_load(zip_ref.open(x))
                profile_meta_data = {
                    "name": yaml_dict["profileName"],
                    "game": yaml_dict["profileGame"],
                    "game_display_name": yaml_dict["profileGameDisplayName"],
                    "code": str(profile.id),
                    "mods": [generate_mod_metadata(mod, yaml_dict["profileGame"]) for mod in yaml_dict["mods"]],
                }
    LegacyProfileMetaData.objects.create(profile=profile, profile_meta_data=profile_meta_data)