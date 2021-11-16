def team(request):
    if not (hasattr(request, "user") and request.user.is_authenticated):
        return {}
    name = request.user.username
    membership = request.user.teams.first()
    if membership:
        name = membership.team.name
    return {"team": name}
