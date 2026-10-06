"""Catalog adapters. v0.1 uses bundled, versioned JSON snapshots (D-05)."""

from __future__ import annotations

import json
from pathlib import Path

from ..domain.catalog import CatalogSnapshot, CatalogUnavailable, CatalogVersionUnknown, build_snapshot

CATALOG_DIR = Path(__file__).with_name("catalogs")
DEFAULT_CATALOG_VERSION = "catalog-demo-v1"


class CatalogRepository:
    """In-memory store of validated snapshots. Invalid files fail at startup, never at request time."""

    def __init__(self, snapshots: dict[str, CatalogSnapshot], default_version: str = DEFAULT_CATALOG_VERSION,
                 available: bool = True):
        self._snapshots = snapshots
        self.default_version = default_version if default_version in snapshots else next(iter(sorted(snapshots)), "")
        self.available = available

    @classmethod
    def from_directory(cls, directory: Path = CATALOG_DIR) -> "CatalogRepository":
        snapshots = {}
        for path in sorted(directory.glob("*.json")):
            snapshot = build_snapshot(json.loads(path.read_text(encoding="utf-8")))
            snapshots[snapshot.catalog_version] = snapshot
        return cls(snapshots)

    @property
    def versions(self) -> list[str]:
        return sorted(self._snapshots)

    def get(self, version: str | None = None) -> CatalogSnapshot:
        if not self.available:
            raise CatalogUnavailable(version or self.default_version)
        version = version or self.default_version
        if version not in self._snapshots:
            raise CatalogVersionUnknown(version, self.versions)
        return self._snapshots[version]
