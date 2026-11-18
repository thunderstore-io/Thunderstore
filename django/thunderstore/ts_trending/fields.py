import math

from rest_framework import serializers

from thunderstore.ts_trending.services.score import PackageScore


class ScoreField(serializers.Field):
    default_error_messages = {"invalid": "Expected a [package id, score] pair."}

    def to_internal_value(self, data) -> PackageScore:
        if not isinstance(data, (list, tuple)) or len(data) != 2:
            self.fail("invalid")
        package_id, score = data
        if type(package_id) is not int or type(score) not in (int, float):
            self.fail("invalid")
        try:
            score = float(score)
        except OverflowError:
            self.fail("invalid")
        if not math.isfinite(score):
            self.fail("invalid")
        return package_id, score
