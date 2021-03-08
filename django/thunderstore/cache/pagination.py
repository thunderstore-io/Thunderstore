from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.utils.functional import cached_property

from thunderstore.cache.cache import cache_get_or_set_by_key


class CachedPaginator(Paginator):
    """
    A paginator that caches pages and doesn't need to re-evaluate queries
    as long as cache is available
    """

    def __init__(
        self,
        object_list: QuerySet,
        per_page: int,
        cache_key: str,
        cache_vary: str,
        cache_bust_condition: str,
        orphans=0,
        allow_empty_first_page=True,
    ):
        self.cache_key = cache_key
        self.cache_vary = cache_vary
        self.cache_bust_condition = cache_bust_condition
        super().__init__(
            object_list,
            per_page,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
        )

    def _get_page(self, *args, **kwargs):
        return CachedPage(
            *args,
            cache_key=self.cache_key,
            cache_vary=self.cache_vary,
            cache_bust_condition=self.cache_bust_condition,
            **kwargs,
        )

    @cached_property
    def count(self):
        return cache_get_or_set_by_key(
            self.cache_bust_condition,
            f"{self.cache_key}.count",
            self.cache_vary,
            lambda: super(CachedPaginator, self).count,
        )

    def _check_object_list_is_ordered(self):
        # TODO: Better way to override?
        pass


class CachedPage(Page):
    def __init__(
        self,
        object_list,
        number,
        paginator,
        cache_key: str,
        cache_vary: str,
        cache_bust_condition: str,
    ):
        self.cache_key = cache_key
        self.cache_vary = cache_vary
        self.cache_bust_condition = cache_bust_condition
        self._object_list = object_list
        self.number = number
        super().__init__(self.object_list, number, paginator)

    @cached_property
    def object_list(self):
        return cache_get_or_set_by_key(
            self.cache_bust_condition,
            f"{self.cache_key}.page.{self.number}",
            self.cache_vary,
            lambda: list(self._object_list),
        )
