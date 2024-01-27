from django.db import models


class PackageInstaller(models.Model):
    identifier = models.SlugField(unique=True, db_index=True, editable=False)
    name = models.TextField()
    description = models.TextField()

    def __str__(self):
        return self.identifier


class PackageInstallerDeclaration(models.Model):
    """
    Used for the m2m relation between PackageVersion and PackageInstaller.
    A custom model is used in order to support potential extra data in the
    installer declarations in the future.
    """

    package_installer = models.ForeignKey(
        "repository.PackageInstaller",
        on_delete=models.PROTECT,
        related_name="installer_declarations",
    )
    package_version = models.ForeignKey(
        "repository.PackageVersion",
        on_delete=models.CASCADE,
        related_name="installer_declarations",
    )
