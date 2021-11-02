from rest_framework import serializers

from thunderstore.repository.models import Team
from thunderstore.repository.serializer_fields import Base64Field, ModelChoiceField
from thunderstore.repository.validation.icon import MAX_ICON_SIZE


class ReadmeValidatorParamsSerializer(serializers.Serializer):
    readme_data = Base64Field()


class ManifestV1ValidatorParamsSerializer(serializers.Serializer):
    namespace = ModelChoiceField(
        queryset=Team.objects.exclude(is_active=False),
        to_field="name",
    )
    manifest_data = Base64Field()


class IconValidatorParamsSerializer(serializers.Serializer):
    icon_data = Base64Field(max_size=MAX_ICON_SIZE)


class ValidatorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
