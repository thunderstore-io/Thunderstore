from rest_framework import serializers


class PackageValidationResponseSerializer(serializers.Serializer):
    validation_errors = serializers.ListField(child=serializers.CharField())
