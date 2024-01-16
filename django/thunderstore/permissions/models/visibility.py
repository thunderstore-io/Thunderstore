from django.db import models


class VisibilityFlags(models.Model):
    id = models.BigAutoField(primary_key=True, editable=False)

    public_list = models.BooleanField(db_index=True)
    public_detail = models.BooleanField(db_index=True)
    owner_list = models.BooleanField(db_index=True)
    owner_detail = models.BooleanField(db_index=True)
    moderator_list = models.BooleanField(db_index=True)
    moderator_detail = models.BooleanField(db_index=True)
    admin_list = models.BooleanField(db_index=True)
    admin_detail = models.BooleanField(db_index=True)
