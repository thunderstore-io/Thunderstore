from django.urls import path

from thunderstore.repository.api.experimental.views import (
    PackageDetailApiView,
    PackageListApiView,
    PackageVersionChangelogApiView,
    PackageVersionDetailApiView,
    PackageVersionReadmeApiView,
    UploadPackageApiView,
)
from thunderstore.repository.api.experimental.views.package_index import (
    PackageIndexApiView,
)
from thunderstore.repository.api.experimental.views.submit import SubmitPackageApiView
from thunderstore.repository.api.experimental.views.submit_async import (
    CreateAsyncPackageSubmissionApiView,
    PollSubmissionStatusApiView,
)
from thunderstore.repository.api.experimental.views.validators import (
    IconValidatorApiView,
    ManifestV1ValidatorApiView,
    ReadmeValidatorApiView,
)
from thunderstore.repository.api.experimental.views.wiki import (
    PackageWikiApiView,
    PackageWikiListAPIView,
)
from thunderstore.social.api.experimental.views import CurrentUserExperimentalApiView
from thunderstore.social.api.experimental.views.current_user import (
    CurrentUserRatedPackagesExperimentalApiView,
)

urls = [
    path(
        "current-user/", CurrentUserExperimentalApiView.as_view(), name="current-user"
    ),
    path(
        "current-user/rated-packages/",
        CurrentUserRatedPackagesExperimentalApiView.as_view(),
        name="current-user.rated-packages",
    ),
    path("package-index/", PackageIndexApiView.as_view(), name="package-index"),
    path("package/", PackageListApiView.as_view(), name="package-list"),
    path("package/wikis/", PackageWikiListAPIView.as_view(), name="package-wiki-list"),
    path(
        "package/<str:namespace>/<str:name>/",
        PackageDetailApiView.as_view(),
        name="package-detail",
    ),
    path(
        "package/<str:namespace>/<str:name>/wiki/",
        PackageWikiApiView.as_view(),
        name="package-wiki",
    ),
    path(
        "package/<str:namespace>/<str:name>/<str:version>/",
        PackageVersionDetailApiView.as_view(),
        name="package-version-detail",
    ),
    path(
        "package/<str:namespace>/<str:name>/<str:version>/changelog/",
        PackageVersionChangelogApiView.as_view(),
        name="package-version-changelog",
    ),
    path(
        "package/<str:namespace>/<str:name>/<str:version>/readme/",
        PackageVersionReadmeApiView.as_view(),
        name="package-version-readme",
    ),
    path(
        "submission/submit/", SubmitPackageApiView.as_view(), name="submission.submit"
    ),
    path(
        "submission/submit-async/",
        CreateAsyncPackageSubmissionApiView.as_view(),
        name="submission.submit-async",
    ),
    path(
        "submission/poll-async/<str:submission_id>/",
        PollSubmissionStatusApiView.as_view(),
        name="submission.poll-async",
    ),
    path(
        "submission/upload/", UploadPackageApiView.as_view(), name="submission.upload"
    ),
    path(
        "submission/validate/readme/",
        ReadmeValidatorApiView.as_view(),
        name="submission.validate.readme",
    ),
    path(
        "submission/validate/manifest-v1/",
        ManifestV1ValidatorApiView.as_view(),
        name="submission.validate.manifest-v1",
    ),
    path(
        "submission/validate/icon/",
        IconValidatorApiView.as_view(),
        name="submission.validate.icon",
    ),
]
