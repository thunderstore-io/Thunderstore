from typing import List, Literal, Optional

from django.conf import settings
from pydantic import BaseModel


class DiscordEmbedThumbnail(BaseModel):
    url: str
    width: int
    height: int


class DiscordEmbedProvider(BaseModel):
    name: str
    url: str


class DiscordEmbedAuthor(BaseModel):
    name: str


class DiscordEmbedField(BaseModel):
    name: str
    value: str


DEFAULT_PROVIDER = DiscordEmbedProvider(
    name=settings.SITE_NAME, url=f"{settings.PROTOCOL}{settings.PRIMARY_HOST}/"
)


class DiscordEmbed(BaseModel):
    title: str
    type: Literal["rich"] = "rich"
    description: Optional[str]
    url: Optional[str]
    timestamp: str
    color: Optional[int]
    thumbnail: Optional[DiscordEmbedThumbnail]
    provider: DiscordEmbedProvider = DEFAULT_PROVIDER
    author: Optional[DiscordEmbedAuthor]
    fields: Optional[List[DiscordEmbedField]]


class DiscordPayload(BaseModel):
    embeds: List[DiscordEmbed]
