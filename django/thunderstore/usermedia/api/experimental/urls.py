from django.urls import path

from thunderstore.usermedia.api.experimental.views.upload import (
    UserMediaAbortUploadApiView,
    UserMediaFinishUploadApiView,
    UserMediaInitiateUploadApiView,
)

urls = [
    path(
        "usermedia/initiate-upload/",
        UserMediaInitiateUploadApiView.as_view(),
        name="usermedia.initiate-upload",
    ),
    path(
        "usermedia/<uuid:uuid>/finish-upload/",
        UserMediaFinishUploadApiView.as_view(),
        name="usermedia.finish-upload",
    ),
    path(
        "usermedia/<uuid:uuid>/abort-upload/",
        UserMediaAbortUploadApiView.as_view(),
        name="usermedia.abort-upload",
    ),
]
