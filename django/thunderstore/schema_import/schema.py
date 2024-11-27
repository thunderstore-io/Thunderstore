from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SchemaThunderstoreSection(BaseModel):
    name: str
    exclude_categories: List[str] = Field(default=[], alias="excludeCategories")
    require_categories: List[str] = Field(default=[], alias="requireCategories")


class SchemaThunderstoreCategory(BaseModel):
    label: str


class SchemaCommunity(BaseModel):
    display_name: str = Field(alias="displayName")
    categories: Dict[str, SchemaThunderstoreCategory]
    sections: Dict[str, SchemaThunderstoreSection]
    short_description: Optional[str] = Field(alias="shortDescription")
    discord_url: Optional[str] = Field(alias="discordUrl")
    wiki_url: Optional[str] = Field(alias="wikiUrl")
    autolist_package_ids: Optional[List[str]] = Field(alias="autolistPackageIds")


class SchemaGameMeta(BaseModel):
    displayName: str


class SchemaGame(BaseModel):
    meta: SchemaGameMeta
    thunderstore: Optional[SchemaCommunity]


class SchemaPackageInstaller(BaseModel):
    name: str
    description: str


class Schema(BaseModel):
    schema_version: str = Field(alias="schemaVersion")
    games: Dict[str, SchemaGame]
    communities: Dict[str, SchemaCommunity]
    package_installers: Optional[Dict[str, SchemaPackageInstaller]] = Field(
        None, alias="packageInstallers"
    )
