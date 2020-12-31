def uploader_identity(request):
    if not request.user.is_authenticated:
        return {}
    name = request.user.username
    membership = request.user.uploader_identities.first()
    if membership:
        name = membership.identity.name
    return {"uploader_identity": name}
