"""
This module contains a three-level cache hierarchy with private L1 caches,
private L2 caches, and a shared L3 cache.
"""

from gem5.components.boards.abstract_board import AbstractBoard
from gem5.components.cachehierarchies.classic.abstract_classic_cache_hierarchy import (
    AbstractClassicCacheHierarchy,
)

from gem5.components.cachehierarchies.classic.caches.l1dcache import L1DCache
from gem5.components.cachehierarchies.classic.caches.l1icache import L1ICache
from gem5.components.cachehierarchies.classic.caches.l2cache import L2Cache
from gem5.components.cachehierarchies.classic.caches.mmu_cache import MMUCache
from components.l3_cache import L3RandomRPCache, L3TreeRPCache
from gem5.isas import ISA
from m5.objects.ReplacementPolicies import RandomRP, LRURP

from m5.objects import (
    BadAddr,
    Cache,
    L2XBar,
    SystemXBar,
    SubSystem,
)

from components.l3_cache import L3Cache

class PrivateL1PrivateL2SharedL3CacheHierarchy(AbstractClassicCacheHierarchy):

    def __init__(
        self,
        l1d_size,
        l1i_size,
        l2_size,
        l3_size,
        l1d_assoc,
        l1i_assoc,
        l2_assoc,
        l3_assoc,
        rp_policy=LRURP,
    ):
        AbstractClassicCacheHierarchy.__init__(self)

        # Save the sizes to use later. We have to use leading underscores
        # because the SimObject (SubSystem) does not have these attributes as
        # parameters.
        self._l1d_size = l1d_size
        self._l1i_size = l1i_size
        self._l2_size = l2_size
        self._l3_size = l3_size
        self._l1d_assoc = l1d_assoc
        self._l1i_assoc = l1i_assoc
        self._l2_assoc = l2_assoc
        self._l3_assoc = l3_assoc
        self._rp_policy = rp_policy

        ## FILL THIS IN

        self.membus = SystemXBar(width=64)

        # For FS mode
        self.membus.badaddr_responder = BadAddr()
        self.membus.default = self.membus.badaddr_responder.pio

    def get_mem_side_port(self):
        return self.membus.mem_side_ports

    def get_cpu_side_port(self):
        return self.membus.cpu_side_ports

    def incorporate_cache(self, board):
        board.connect_system_port(self.get_cpu_side_port())

        for _, port in board.get_memory().get_mem_ports():
            self.membus.mem_side_ports = port

        self.clusters = [
        self._create_core_cluster(
            core, board.get_processor().get_isa()
        )
            for core in board.get_processor().get_cores()
        ]

        self._connect_shared_cache()

        if board.has_coherent_io():
            self._setup_io_cache(board)

    ## FILL THIS IN

    def _connect_shared_cache(self):
        self.l3_cache = L3Cache(self._l3_size, self._l3_assoc)
        self.l3_cache.replacement_policy = self._rp_policy()

        self.l3_cache.cpu_side = self.l3_bus.mem_side_ports
        self.l3_cache.mem_side = self.membus.cpu_side_ports

    def _create_core_cluster(self, core, isa):
        """
        Create a core cluster with the given core.
        """
        cluster = SubSystem()

        ## FILL THIS IN
        # Create the L1 and L2 caches, l2xbar, and connect them to the core
        cluster.l1dcache = L1DCache(self._l1d_size, self._l1d_assoc)
        cluster.l1dcache.replacement_policy = self._rp_policy()

        cluster.l1icache = L1ICache(self._l1i_size, self._l1i_assoc)
        cluster.l1icache.replacement_policy = self._rp_policy()

        core.connect_dcache(cluster.l1dcache.cpu_side)
        core.connect_icache(cluster.l1icache.cpu_side)

        cluster.l2cache = L2Cache(self._l2_size, self._l2_assoc)
        cluster.l2cache.replacement_policy = self._rp_policy()
        cluster.l2_xbar = L2XBar()

        cluster.l1dcache.mem_side = cluster.l2_xbar.cpu_side_ports
        cluster.l1icache.mem_side = cluster.l2_xbar.cpu_side_ports
        cluster.l2cache.cpu_side = cluster.l2_xbar.mem_side_ports

        self._connect_l2_cache_with_l3_cache(cluster)

        cluster.iptw_cache = MMUCache(size="8KiB", writeback_clean=False)
        cluster.dptw_cache = MMUCache(size="8KiB", writeback_clean=False)
        core.connect_walker_ports(
            cluster.iptw_cache.cpu_side, cluster.dptw_cache.cpu_side
        )

        # Connect the caches to the L2 bus
        cluster.iptw_cache.mem_side = cluster.l2_xbar.cpu_side_ports
        cluster.dptw_cache.mem_side = cluster.l2_xbar.cpu_side_ports

        if isa == ISA.X86:
            int_req_port = self.membus.mem_side_ports
            int_resp_port = self.membus.cpu_side_ports
            core.connect_interrupt(int_req_port, int_resp_port)
        else:
            core.connect_interrupt()

        return cluster

    def _connect_l2_cache_with_l3_cache(self, cluster):
        self.l3_bus = L2XBar()
        cluster.l2cache.mem_side = self.l3_bus.cpu_side_ports

    def _setup_io_cache(self, board: AbstractBoard) -> None:
        """Create a cache for coherent I/O connections"""
        self.iocache = Cache(
            assoc=8,
            tag_latency=50,
            data_latency=50,
            response_latency=50,
            mshrs=20,
            size="1kB",
            tgts_per_mshr=12,
            addr_ranges=board.mem_ranges,
        )
        self.iocache.mem_side = self.membus.cpu_side_ports
        self.iocache.cpu_side = board.get_mem_side_coherent_io_port()

class PrivateL1PrivateL2SharedL3CacheHierarchyRandomRP(PrivateL1PrivateL2SharedL3CacheHierarchy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **{**kwargs, "rp_policy":RandomRP})

class PrivateL1PrivateL2SharedL3CacheHierarchyRandomRP(PrivateL1PrivateL2SharedL3CacheHierarchy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **{**kwargs, "rp_policy":RandomRP})

class PrivateL1PrivateL2PrivateL3CacheHierarchy(PrivateL1PrivateL2SharedL3CacheHierarchy):

    def _connect_shared_cache(self):
        pass

    def _connect_l2_cache_with_l3_cache(self, cluster):
        cluster.l3_cache = L3Cache(self._l3_size, self._l3_assoc)
        cluster.l3_cache.replacement_policy = self._rp_policy()
        cluster.l3_bus = L2XBar()
        cluster.l2cache.mem_side = cluster.l3_bus.cpu_side_ports
        cluster.l3_cache.cpu_side = cluster.l3_bus.mem_side_ports
        cluster.l3_cache.mem_side = self.membus.cpu_side_ports

