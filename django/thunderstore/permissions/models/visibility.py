from django.db import models


class VisibilityFlagsQuerySet(models.QuerySet):
    def create_public(self):
        return self.create(
            public_list=True,
            public_detail=True,
            owner_list=True,
            owner_detail=True,
            moderator_list=True,
            moderator_detail=True,
            admin_list=True,
            admin_detail=True,
        )


class VisibilityFlags(models.Model):
    objects = VisibilityFlagsQuerySet.as_manager()
    id = models.BigAutoField(primary_key=True, editable=False)

    public_list = models.BooleanField(db_index=True)
    public_detail = models.BooleanField(db_index=True)
    owner_list = models.BooleanField(db_index=True)
    owner_detail = models.BooleanField(db_index=True)
    moderator_list = models.BooleanField(db_index=True)
    moderator_detail = models.BooleanField(db_index=True)
    admin_list = models.BooleanField(db_index=True)
    admin_detail = models.BooleanField(db_index=True)

    def __str__(self) -> str:
        flag_fields = (
            field.name
            for field in self._meta.get_fields()
            if isinstance(field, models.BooleanField) and getattr(self, field.name)
        )
        return ", ".join(flag_fields) or "None"

    def bitstring(self) -> str:
        fields = [
            self.public_list,
            self.public_detail,
            self.owner_list,
            self.owner_detail,
            self.moderator_list,
            self.moderator_detail,
            self.admin_list,
            self.admin_detail,
        ]
        return "".join("1" if field else "0" for field in fields)
