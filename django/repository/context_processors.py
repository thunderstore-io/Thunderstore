
def uploader_identity(request):
    name = request.user.username
    membership = request.user.author_identities.first()
    if membership:
        name = membership.identity.name
    return {
        "uploader_identity": name
    }
