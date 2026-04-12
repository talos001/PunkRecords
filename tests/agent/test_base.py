from abc import ABC
from typing import List, Dict, Optional
from pathlib import Path
import pytest
from punkrecords.agent.base import BaseAgent, IngestionResult, QueryResult


def test_base_agent_is_abstract():
    with pytest.raises(TypeError):
        BaseAgent()
