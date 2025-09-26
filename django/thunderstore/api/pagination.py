from rest_framework.pagination import PageNumberPagination


class PackageDependenciesPaginator(PageNumberPagination):
    page_size = 20
