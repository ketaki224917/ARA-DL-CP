"""Initial package smoke checks."""

from ara import __version__


def test_package_version_is_available() -> None:
    """The package exposes a semantic version string."""
    assert __version__ == "0.1.0"

