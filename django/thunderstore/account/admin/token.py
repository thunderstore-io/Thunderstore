from django.contrib import admin
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import TokenProxy


class CustomTokenAdmin(TokenAdmin):
    raw_id_fields = ("user",)


admin.site.unregister(TokenProxy)
admin.site.register(TokenProxy, CustomTokenAdmin)
