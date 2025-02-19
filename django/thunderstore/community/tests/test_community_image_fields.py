import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from thunderstore.community.factories import CommunityFactory

# Image fields currently in the Community model
IMAGE_FIELD_NAMES = (
    "icon",
    "background_image",
    "hero_image",
    "cover_image",
    "community_icon",
)


def _generate_test_image(width: int, height: int) -> SimpleUploadedFile:
    img = Image.new("RGB", (width, height), color="blue")
    img_io = io.BytesIO()
    img.save(img_io, format="JPEG")
    img_io.seek(0)

    uploaded_image = SimpleUploadedFile(
        "test.jpg", img_io.getvalue(), content_type="image/jpeg"
    )

    return uploaded_image


@pytest.mark.django_db
@pytest.mark.parametrize("image_field_name", IMAGE_FIELD_NAMES)
def test_update_community_default_image_dimensions(image_field_name) -> None:
    community = CommunityFactory()
    setattr(community, image_field_name, None)
    community.save()

    assert getattr(community, f"{image_field_name}_height") == 0
    assert getattr(community, f"{image_field_name}_width") == 0


@pytest.mark.django_db
@pytest.mark.parametrize("image_field_name", IMAGE_FIELD_NAMES)
def test_reset_to_community_default_image_dimensions(image_field_name) -> None:
    width = 200
    height = 100

    community = CommunityFactory()

    # Create new community with image
    setattr(community, image_field_name, _generate_test_image(width, height))
    community.save()

    # Assert image dimensions are set
    assert getattr(community, f"{image_field_name}_width") == width
    assert getattr(community, f"{image_field_name}_height") == height

    # Reset image field
    setattr(community, image_field_name, None)
    community.save()

    # Assert all image dimensions are reset to 0
    assert getattr(community, f"{image_field_name}_width") == 0
    assert getattr(community, f"{image_field_name}_height") == 0
