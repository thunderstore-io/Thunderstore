from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination

# bigint max. Postgres compares anything larger as numeric and skips the id index.
MAX_CURSOR_ID = 2**63 - 1


class MarkdownHistoryPagination(CursorPagination):
    page_size = 10
    ordering = "-id"

    def decode_cursor(self, request):
        cursor = super().decode_cursor(request)
        if cursor is not None and cursor.position is not None:
            try:
                position = int(cursor.position)
            except ValueError:
                raise NotFound(self.invalid_cursor_message)
            if not 0 <= position <= MAX_CURSOR_ID:
                raise NotFound(self.invalid_cursor_message)
        return cursor
