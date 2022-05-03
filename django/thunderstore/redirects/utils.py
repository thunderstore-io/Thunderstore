import re
from collections import OrderedDict

from django.urls import reverse

from thunderstore.core.utils import make_full_url
from thunderstore.repository.mixins import CommunityMixin

OLD_URL_REGEXS = OrderedDict(
    {
        "bot_deprecate_mod": (
            "/api/v1/bot/deprecate-mod/$",
            "communities:community:api:bot.deprecate-mod",
        ),
        "current_user_info": (
            "/api/v1/current-user/info/$",
            "communities:community:api:current-user.info",
        ),
        "package_rate": (
            "/api/v1/package/([^/]*?)/rate/$",
            "communities:community:api:package-rate",
        ),
        "package_detail": (
            "/api/v1/package/([^/]*?)/$",
            "communities:community:api:package-detail",
        ),
        "package_list": ("/api/v1/package/$", "communities:community:api:package-list"),
        "packages_create_docs": (
            "/package/create/docs/$",
            "communities:community:packages.create.docs",
        ),
        "packages_create_old": (
            "/package/create/old/$",
            "communities:community:packages.create.old",
        ),
        "packages_create": (
            "/package/create/$",
            "communities:community:packages.create",
        ),
        "packages_list_by_dependency": (
            "/package/([^/]*?)/([^/]*?)/dependants/$",
            "communities:community:packages.list_by_dependency",
        ),
        "packages_version_detail": (
            "/package/([^/]*?)/([^/]*?)/([^/]*?)/$",
            "communities:community:packages.version.detail",
        ),
        "packages_detail": (
            "/package/([^/]*?)/([^/]*?)/$",
            "communities:community:packages.detail",
        ),
        "packages_list_by_owner": (
            "/package/([^/]*?)/$",
            "communities:community:packages.list_by_owner",
        ),
        "packages_list": ("/package/$", "communities:community:packages.list"),
    }
)


class RedirectNotFound(Exception):
    pass


class LegacyUrlHandler(CommunityMixin):
    def __init__(self, request):
        self.request = request
        self.reverse_name = None
        self.reverse_kwargs = {}

    def solve_view(self, path):
        result = None
        for view_name, (regex, reverse_name) in OLD_URL_REGEXS.items():
            result = re.search(regex, path)
            if result:
                self.handle_reverse_arguments(view_name, result)
                self.reverse_name = reverse_name
                break
        if not result:
            raise RedirectNotFound

    def get_redirected_full_url(self):
        self.solve_view(self.request.path)

        return make_full_url(
            self.request,
            reverse(self.reverse_name, kwargs=self.reverse_kwargs),
            transfer_query_string=True,
        )

    def noop(self, result=None):
        pass

    def handle_reverse_arguments(self, name, *args):
        self.reverse_kwargs.update(
            {"community_identifier": solve_community_identifier(self.request)}
        )
        getattr(self, "get_reverse_data_" + name, self.noop)(*args)

    def get_reverse_data_package_rate(self, result):
        self.reverse_kwargs.update({"uuid4": result.group(1)})

    def get_reverse_data_package_detail(self, result):
        self.reverse_kwargs.update({"uuid4": result.group(1)})

    def get_reverse_data_packages_list_by_dependency(self, result):
        self.reverse_kwargs.update({"owner": result.group(1)})
        self.reverse_kwargs.update({"name": result.group(2)})

    def get_reverse_data_packages_version_detail(self, result):
        self.reverse_kwargs.update({"owner": result.group(1)})
        self.reverse_kwargs.update({"name": result.group(2)})
        self.reverse_kwargs.update({"version": result.group(3)})

    def get_reverse_data_packages_detail(self, result):
        self.reverse_kwargs.update({"owner": result.group(1)})
        self.reverse_kwargs.update({"name": result.group(2)})

    def get_reverse_data_packages_list_by_owner(self, result):
        self.reverse_kwargs.update({"owner": result.group(1)})


def solve_community_identifier(request):
    # TODO: This is shitty
    if len(request.get_host().split(".")) == 3:
        return request.get_host().split(".")[0]
    else:
        return "riskofrain2"
