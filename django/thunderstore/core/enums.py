from django.db.models import TextChoices


class OptionalBoolChoice(TextChoices):
    NONE = "NONE"
    YES = "YES"
    NO = "NO"
