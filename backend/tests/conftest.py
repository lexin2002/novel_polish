"""Pytest configuration and fixtures"""

import pytest


def pytest_configure(config):
    """Configure pytest-asyncio to use auto mode"""
    config.option.asyncio_mode = "auto"
