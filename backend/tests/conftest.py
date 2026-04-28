"""Shared fixtures for backend tests"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator

import pytest

from app.core.config_manager import ConfigurationManager, DEFAULT_CONFIG, DEFAULT_RULES


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for config/rules files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_manager(temp_data_dir: Path) -> ConfigurationManager:
    """Create a ConfigurationManager with a temporary data directory"""
    return ConfigurationManager(data_dir=str(temp_data_dir))


@pytest.fixture
def sample_rules() -> Dict[str, Any]:
    """Return a sample rules configuration"""
    import copy
    return copy.deepcopy(DEFAULT_RULES)


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Return a sample configuration"""
    import copy
    return copy.deepcopy(DEFAULT_CONFIG)
