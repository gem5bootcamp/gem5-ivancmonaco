from components.three_level_cache import PrivateL1PrivateL2SharedL3CacheHierarchy
from components.l3_cache import L3Cache
from components.l4_cache import L4Cache

from m5.objects import (
    L2XBar,
)

class PrivateL1PrivateL2SharedL3SharedL4CacheHierarchy(PrivateL1PrivateL2SharedL3CacheHierarchy):
    def __init__(
        self,
        l1d_size,
        l1i_size,
        l2_size,
        l3_size,
        l4_size,
        l1d_assoc,
        l1i_assoc,
        l2_assoc,
        l3_assoc,
        l4_assoc,
    ):
        super().__init__(l1d_size, l1i_size, l2_size, l3_size, l1d_assoc, l1i_assoc, l2_assoc, l3_assoc)

        self._l4_size = l4_size
        self._l4_assoc = l4_assoc

    def _connect_shared_cache(self):
        self.l3_cache = L3Cache(self._l3_size, self._l3_assoc)
        self.l3_cache.replacement_policy = self._rp_policy()
        self.l3_cache.cpu_side = self.l3_bus.mem_side_ports

        self.l4_cache = L3Cache(
            size=self._l4_size,
            assoc=self._l4_assoc,
        )

        self.l4_bus = L2XBar()

        self.l3_cache.mem_side = self.l4_bus.cpu_side_ports
        self.l4_cache.cpu_side = self.l4_bus.mem_side_ports
        self.l4_cache.mem_side = self.membus.cpu_side_ports


