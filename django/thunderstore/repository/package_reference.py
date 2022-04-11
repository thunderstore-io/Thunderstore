from __future__ import annotations

from distutils.version import StrictVersion
from typing import Dict, Optional, Union

from django.db.models import QuerySet
from django.utils.functional import cached_property

from thunderstore.repository.models import Package, PackageVersion


class PackageReference:
    def __init__(
        self,
        namespace: str,
        name: str,
        version: Optional[Union[str, StrictVersion]] = None,
    ):
        """
        :param str namespace: The namespace of the referenced package
        :param str name: The name of the referenced package
        :param version: The version of the referenced package
        :type version: StrictVersion or str or None
        """
        self._namespace: str = namespace
        self._name: str = name
        if version is not None and not isinstance(version, StrictVersion):
            version = StrictVersion(version)
        self._version: Optional[StrictVersion] = version

    def __str__(self) -> str:
        if self.version:
            return f"{self.namespace}-{self.name}-{self.version_str}"
        else:
            return f"{self.namespace}-{self.name}"

    def __repr__(self) -> str:
        return f"<PackageReference: {str(self)}>"

    @property
    def namespace(self) -> str:
        return self._namespace

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> Optional[StrictVersion]:
        return self._version

    @property
    def version_str(self):
        if self.version is not None:
            return ".".join(str(x) for x in self.version.version)
        return ""

    def is_same_package(self, other: Union[str, PackageReference]) -> bool:
        """
        Check if another package reference belongs to the same package as this
        one

        :param other: The package to check against
        :type other: PackageReference or str
        :return: True if matching, False otherwise
        :rtype: bool
        """
        if isinstance(other, str):
            other = PackageReference.parse(other)
        return self.namespace == other.namespace and self.name == other.name

    def is_same_version(self, other: Union[str, PackageReference]) -> bool:
        """
        Check if another package reference is of the same package and version as
        this one

        :param other: The package to check against
        :type other: PackageReference or str
        :return: True if matching, False otherwise
        :rtype: bool
        """
        if isinstance(other, str):
            other = PackageReference.parse(other)
        if not self.is_same_package(other):
            return False
        try:
            return self.version == other.version
        except AttributeError:
            return False

    def __eq__(self, other):
        if isinstance(other, PackageReference):
            return self.is_same_version(other)
        return False

    def __gt__(self, other):
        if isinstance(other, PackageReference):
            if not self.is_same_package(other):
                raise TypeError("Unable to compare different packages")
            if not all((self.version, other.version)):
                raise TypeError("Unable to compare packages without version")
            return self.version > other.version
        raise TypeError("Unable to make comparison")

    def __lt__(self, other):
        if isinstance(other, PackageReference):
            if not self.is_same_package(other):
                raise TypeError("Unable to compare different packages")
            if not all((self.version, other.version)):
                raise TypeError("Unable to compare packages without version")
            return self.version < other.version
        raise TypeError("Unable to make comparison")

    def __hash__(self):
        return hash(str(self))

    @classmethod
    def parse(cls, unparsed: Union[PackageReference, str]) -> PackageReference:
        """
        - Packages references are in format {namespace}-{name}-{version}
        - Namespace may contain dashes, whereas name and version can not
        - Version might not be included

        This means we must parse the reference string backwards, as there is no
        good way to know when the namespace ends and the package name starts.

        :param str unparsed: The package reference string
        :return: A parsed PackageReferenced object
        :rtype: PackageReference
        :raises ValueError: If the reference string is in an invalid format
        """
        if isinstance(unparsed, PackageReference):
            return unparsed

        if unparsed is None:
            raise ValueError("Unable to parse NoneType")

        version_string = unparsed.split("-")[-1]
        version = None
        if version_string.count(".") > 0:
            if version_string.count(".") != 2:
                raise ValueError(f"Invalid package reference string: {unparsed}")
            if unparsed.count("-") < 2:
                raise ValueError(f"Invalid package reference string: {unparsed}")
            version = StrictVersion(version_string)
            unparsed = unparsed[: -(len(version_string) + 1)]

        name = unparsed.split("-")[-1]
        namespace = "-".join(unparsed.split("-")[:-1])

        if not (namespace and name):
            raise ValueError(f"Invalid package reference string: {unparsed}")

        return PackageReference(namespace=namespace, name=name, version=version)

    @cached_property
    def without_version(self) -> PackageReference:
        """
        Return this same package reference with version information removed

        :return: Versionless reference to the same package
        :rtype: PackageReference
        """
        if self.version:
            return PackageReference(namespace=self.namespace, name=self.name)
        return self

    def with_version(
        self, version: Optional[Union[str, StrictVersion]]
    ) -> PackageReference:
        """
        Return this same package reference with a different version

        :return: A reference to this package's specific version
        :rtype: PackageReference
        """
        return PackageReference(
            namespace=self.namespace, name=self.name, version=version
        )

    @property
    def queryset(self) -> QuerySet:
        """
        Get the queryset filtering for the model instance this reference is
        referring to.

        :return: A PackageVersion or Package queryset filtering for this package
        :rtype: QuerySet of PackageVersion or Package
        """
        if self.version:
            return PackageVersion.objects.filter(**self.get_filter_kwargs())
        else:
            return Package.objects.filter(**self.get_filter_kwargs())

    def get_filter_kwargs(self) -> Dict[str, str]:
        """
        Get kwargs that can be used on a QuerySet filter to filter for this
        package or package version

        :return: A dict of kwargs that can be passed into QuerySet.filter()
        :rtype: Dict[str, str]
        """
        if self.version:
            return dict(
                package__namespace__name=self.namespace,
                package__name=self.name,
                version_number=self.version_str,
            )
        else:
            return dict(
                namespace__name=self.namespace,
                name=self.name,
            )

    @cached_property
    def package_version(self) -> Optional[PackageVersion]:
        """
        Resolve and return the PackageVersion model instance for this reference

        :return: A PackageVersion model instance matching this reference
        :rtype: PackageVersion or None
        """
        if not self.version:
            raise TypeError(
                "Unable to resolve package version from a versionless reference"
            )
        return self.queryset.first()

    @cached_property
    def package(self) -> Optional[Package]:
        """
        Resolve and return the Package model instance for this reference

        :return: A Package model instance matching this reference
        :rtype: Package or None
        """
        return self.without_version.instance

    @cached_property
    def instance(self) -> Optional[Union[Package, PackageVersion]]:
        """
        Resolve and return the PackageVersion or Package model instance for
        this reference. PackageVersion will be returned if version information
        is available, otherwise a Package instance will be returned.

        :return: This reference's closest matching model instance
        :rtype: Package or PackageVersion or None
        """
        return self.queryset.first()

    @cached_property
    def exists(self) -> bool:
        """
        Check if the package this reference is pointing to exists in the db

        :return: True if the package exists, False otherwise
        :rtype: bool
        """
        return self.queryset.exists()
