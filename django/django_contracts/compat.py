"""
This module exists as an abstraction layer to make future refactoring easier
if this module is decoupled from the Thunderstore project.

The idea is that the dependencies imported from Thunderstore are all imported
through this module, meaning replacing them in the future will be easy.
"""
from thunderstore.core.mixins import TimestampMixin
