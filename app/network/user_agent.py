"""User-Agent rotation manager: sequential round-robin and random selection
over a pool of user agent strings, with room to register additional agents
later (e.g. loaded from a file or remote source) without replacing the pool.
"""

import itertools
import random
from typing import Iterable, List, Optional

from app.config.constants import DEFAULT_USER_AGENTS


class UserAgentManager:
    def __init__(self, user_agents: Optional[Iterable[str]] = None) -> None:
        self._user_agents: List[str] = list(DEFAULT_USER_AGENTS) if user_agents is None else list(user_agents)
        if not self._user_agents:
            raise ValueError("UserAgentManager requires at least one user agent")
        self._cycle = itertools.cycle(self._user_agents)

    def next(self) -> str:
        """Sequential round-robin rotation."""
        return next(self._cycle)

    def random(self) -> str:
        """Uniform random selection."""
        return random.choice(self._user_agents)

    def register(self, user_agents: Iterable[str]) -> None:
        """Extend the pool with additional agents (future extensibility)."""
        new_agents = [ua for ua in user_agents if ua not in self._user_agents]
        if not new_agents:
            return
        self._user_agents.extend(new_agents)
        self._cycle = itertools.cycle(self._user_agents)

    @property
    def pool_size(self) -> int:
        return len(self._user_agents)
