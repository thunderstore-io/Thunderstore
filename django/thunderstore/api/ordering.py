from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter


class StrictOrderingFilter(OrderingFilter):
    """
    Acts just like the rest_framework.filters.OrderingFilter besides the
    following changes:
    - Returns a 400 if an invalid filter is used rather than simply ignoring it.
    - Always requires ordering_fields to be defined by the view rather than
      defaulting to all fields of the serializer.
    """

    ordering_fields = []

    def remove_invalid_fields(self, queryset, fields, view, request):
        """
        Overrides the base method so that rather than removing anything, this
        now validates the request parameters match the valid fields.
        """
        valid_fields = [
            item[0]
            for item in self.get_valid_fields(queryset, view, {"request": request})
        ]

        def term_valid(term):
            if term.startswith("-"):
                term = term[1:]
            return term in valid_fields

        for term in fields:
            if not term_valid(term):
                raise ValidationError(f"Unsupported result ordering: {term[:200]}")

        return fields
