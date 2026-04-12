from typing import TYPE_CHECKING

from .base import BaseVault

if TYPE_CHECKING:
    from .material_vault import MaterialVault
    from .index_vault import IndexVault

__all__ = ["BaseVault", "MaterialVault"]
