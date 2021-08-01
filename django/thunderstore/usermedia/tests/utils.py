import os
from typing import List

import requests
from mypy_boto3_s3.type_defs import CompletedPartTypeDef

from thunderstore.usermedia.s3_upload import UploadPartUrlTypeDef


def upload_usermedia(
    size: int, upload_urls: List[UploadPartUrlTypeDef]
) -> List[CompletedPartTypeDef]:
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
