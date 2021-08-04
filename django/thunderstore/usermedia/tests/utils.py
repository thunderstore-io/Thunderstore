import json
import os
from typing import Any, List, Optional

import requests
from django.urls import reverse
from mypy_boto3_s3.type_defs import CompletedPartTypeDef
from rest_framework.test import APIClient

from thunderstore.core.types import UserType
from thunderstore.usermedia.s3_upload import UploadPartUrlTypeDef


def upload_usermedia(
    size: int,
    upload_urls: List[UploadPartUrlTypeDef],
    file: Optional[bytes] = None,
) -> List[CompletedPartTypeDef]:
    if file:
        upload_data = bytearray(file)
    else:
        upload_data = bytearray(os.urandom(size))

    finished_parts: List[CompletedPartTypeDef] = []
    for part_info in upload_urls:
        response = requests.put(
            url=part_info["url"],
            data=upload_data[part_info["offset"] :][: part_info["length"]],
        )
        response.raise_for_status()
        finished_parts.append(
            {
                "ETag": response.headers.get("ETag"),
                "PartNumber": part_info["part_number"],
            }
        )
    return finished_parts


def create_and_upload_usermedia(
    api_client: APIClient, user: UserType, settings: Any, upload: bytes
) -> str:
    _signing_url = settings.USERMEDIA_S3_SIGNING_ENDPOINT_URL
    settings.USERMEDIA_S3_SIGNING_ENDPOINT_URL = settings.USERMEDIA_S3_ENDPOINT_URL

    api_client.force_authenticate(user)
    response = api_client.post(
        reverse("api:experimental:usermedia.initiate-upload"),
        json.dumps(
            {
                "filename": "testfile.zip",
                "file_size_bytes": len(upload),
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 201
    upload_info = response.json()

    parts = upload_usermedia(
        size=upload_info["user_media"]["size"],
        upload_urls=upload_info["upload_urls"],
        file=upload,
    )

    response = api_client.post(
        reverse(
            "api:experimental:usermedia.finish-upload",
            kwargs=dict(uuid=upload_info["user_media"]["uuid"]),
        ),
        json.dumps({"parts": parts}),
        content_type="application/json",
    )
    assert response.status_code == 200
    upload_id = response.json()["uuid"]
    settings.USERMEDIA_S3_SIGNING_ENDPOINT_URL = _signing_url
    return upload_id
