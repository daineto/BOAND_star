"""Versioned, paper-independent campaign definitions."""
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Tuple

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_CAMPAIGN_SCHEMA = 1


@dataclass(frozen=True)
class Configuration:
    metric: str
    classical: str
    best: str
    worst: str
    size: str
    selector: str
    timeout: int = 600
    backend: str = "pyperplan"

    @property
    def name(self):
        name = "_".join(map(str, (self.metric, self.classical, self.best,
                                 self.worst, self.size, self.selector, self.timeout)))
        return name if self.backend == "pyperplan" else f"{name}_{self.backend}"

    @property
    def flags(self):
        flags = ("-m", self.metric, "-ch", self.classical, "-bh", self.best,
                 "-wh", self.worst, "-sh", self.size, "-s", self.selector)
        return flags if self.backend == "pyperplan" else (*flags, "--backend", self.backend)


@dataclass(frozen=True)
class Profile:
    configurations: Tuple[str, ...]
    domains: Optional[Tuple[str, ...]] = None
    instances: Optional[Tuple[Tuple[str, str], ...]] = None


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    version: str
    configurations: Mapping[str, Configuration]
    profiles: Mapping[str, Profile]
    instance_manifest: Path
    timeout_seconds: int = 600
    memory_kb: int = 8_000_000
    default_workers: int = 2
    archive_root: Optional[Path] = None
    analysis_module: Optional[str] = None
    schema_version: int = SUPPORTED_CAMPAIGN_SCHEMA

    def validate(self):
        if self.schema_version != SUPPORTED_CAMPAIGN_SCHEMA:
            raise ValueError(f"Unsupported campaign schema: {self.schema_version}")
        if min(self.timeout_seconds, self.memory_kb, self.default_workers) <= 0:
            raise ValueError("Campaign resource settings must be positive")
        names = [configuration.name for configuration in self.configurations.values()]
        if len(set(names)) != len(names):
            raise ValueError("Configuration identifiers must be unique")
        if any(c.timeout != self.timeout_seconds for c in self.configurations.values()):
            raise ValueError("The executor supports one timeout per campaign; split mixed limits into campaigns")
        for name, profile in self.profiles.items():
            if not profile.configurations or not set(profile.configurations) <= self.configurations.keys():
                raise ValueError(f"Invalid configurations in profile {name}")
        return self
