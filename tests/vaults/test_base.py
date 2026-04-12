from pathlib import Path
import pytest
from punkrecords.vaults.base import BaseVault


def test_base_vault_abstract():
    with pytest.raises(TypeError):
        BaseVault(Path("/tmp/test"))
