"""
Do not import/export these through __init__.py to avoid circular imports
in other serializer files.
"""
from rest_framework import serializers


class CyberstormPackageCategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()


class CyberstormPackageListingSectionSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()
    priority = serializers.IntegerField()
