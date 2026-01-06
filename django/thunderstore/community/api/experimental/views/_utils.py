from urllib.parse import urlencode
from datetime import datetime, timezone
from collections import OrderedDict

from django.shortcuts import redirect
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class CustomCursorPagination(CursorPagination):
    ordering = "-datetime_created"
    results_name = "results"
    page_size = 100

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    (
                        "pagination",
                        OrderedDict(
                            [
                                ("next_link", self.get_next_link()),
                                ("previous_link", self.get_previous_link()),
                            ],
                        ),
                    ),
                    (self.results_name, data),
                ],
            ),
        )


class CustomCursorPaginationWithCount(CustomCursorPagination):
    count = 0
    full_queryset = None

    def paginate_queryset(self, queryset, request, view=None):
        self.full_queryset = queryset
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    (
                        "pagination",
                        OrderedDict(
                            [
                                ("next_link", self.get_next_link()),
                                ("previous_link", self.get_previous_link()),
                                ("count", self.full_queryset.count()),
                            ],
                        ),
                    ),
                    (self.results_name, data),
                ],
            ),
        )

class CustomListAPIView(ListAPIView):
    pagination_class = CustomCursorPagination
    paginator: CustomCursorPagination
    window_duration_in_seconds = 0
    default_query_params = ["window"]
    permitted_query_params = []

    def list(self, request, *args, **kwargs):

        if self.window_duration_in_seconds > 0:
            redirection = self.get_window_redirection()
            if redirection is not None:
                return redirection

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is None:
            raise ValueError("Pagination not set")

        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def get_window_redirection(self):
        requested_window = float(self.request.GET.get("window", f"{datetime.now(timezone.utc).timestamp()}"))
        is_valid_window = requested_window % self.window_duration_in_seconds

        if is_valid_window >= 1:
            # Redirect back to a valid window
            params = self.request.GET.copy()
            params["window"] = round(requested_window / self.window_duration_in_seconds) * self.window_duration_in_seconds
            sorted_params = sorted(params.items(), key=lambda x: x[0])
            query_string = urlencode(sorted_params)
            return redirect(f"{self.request.path}?{query_string}")

        query_items = {key: value for key, value in self.request.GET.items() if key in self.permitted_query_params}
        sorted_params = sorted(query_items.items(), key=lambda x: x[0])
        query_string = urlencode(sorted_params)
        expected_url = f"{self.request.path}?{query_string}"

        if self.request.get_full_path() != expected_url:
            return redirect(expected_url)
        return None

    def set_custom_query_params(self, query_params):
        self.permitted_query_params = self.default_query_params + query_params
