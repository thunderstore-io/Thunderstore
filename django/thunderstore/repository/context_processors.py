def team(request):
    if not (hasattr(request, "user") and request.user.is_authenticated):
        return {}
    membership = request.user.teams.filter(team__is_active=True).first()
    if membership:
        return {"team": membership.team.name}
    return {}
