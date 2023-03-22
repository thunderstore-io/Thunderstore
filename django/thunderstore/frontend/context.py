from thunderstore.frontend.models import NavLink


def nav_links(request):
    return {
        # This is implicitly ordered based on the model's default ordering,
        # which follows the db index.
        "global_nav_links": NavLink.objects.filter(is_active=True)
    }
