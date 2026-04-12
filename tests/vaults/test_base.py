from pathlib import Path
import pytest
from src.vaults.base import BaseVault


def test_base_vault_abstract():
    """Test that BaseVault cannot be instantiated directly because it's abstract."""
    with pytest.raises(TypeError):
        BaseVault(Path("/tmp/test"))
