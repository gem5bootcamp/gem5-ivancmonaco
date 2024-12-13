from workloads.array_sum_workload import (
    NaiveArraySumWorkload,
    ChunkingArraySumWorkload,
    NoResultRaceArraySumWorkload,
    ChunkingNoResultRaceArraySumWorkload,
    NoCacheBlockRaceArraySumWorkload,
    ChunkingNoBlockRaceArraySumWorkload,
)

from components.boards import HW5X86Board
from components.memories.secure_memory import SecureSimpleMemory
from components.processors import HW5O3CPU
from components.cache_hierarchies import HW5MESITwoLevelCacheHierarchy
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import PrivateL1PrivateL2CacheHierarchy

from gem5.simulate.simulator import Simulator

from workloads.roi_manager import exit_event_handler

import argparse

binaries = {
    "naive": NaiveArraySumWorkload,
    "chunking": ChunkingArraySumWorkload,
    "res-race-opt": NoResultRaceArraySumWorkload,
    "chunking-res-race-opt": ChunkingNoResultRaceArraySumWorkload,
    "block-race-opt": NoCacheBlockRaceArraySumWorkload,
    "all-opt": ChunkingNoBlockRaceArraySumWorkload
}

CLK_FREQ = "3GHz"
N_ELEMENTS = 32768

def run(name, cores, xbar=10):

    cls = binaries[name]

    board = HW5X86Board(
        clk_freq=CLK_FREQ,
        processor=HW5O3CPU(cores),
        memory=SecureSimpleMemory("2GiB"),
        cache_hierarchy=HW5MESITwoLevelCacheHierarchy(xbar_latency=xbar),
        # cache_hierarchy=PrivateL1PrivateL2CacheHierarchy("32KiB", "32KiB", "256KiB")
    )

    board.set_workload(cls(N_ELEMENTS, cores))

    simulator = Simulator(board, full_system=False, on_exit_event=exit_event_handler)
    simulator.run()

def main():
    parser = argparse.ArgumentParser(description='Gem5 Running Utility')
    parser.add_argument('-n', '--name', type=str, help="Name of the test to run", default="naive")
    parser.add_argument('-c', '--cores', type=int, help='Number of logical cores (threads)', default=1)
    parser.add_argument('-x', '--xbar', type=int, help='XBar latency', default=10, required=False)

    args = parser.parse_args()

    print(f"Running {args.name} with {args.cores} cores and {args.xbar} xbar latency")

    run(args.name, args.cores, args.xbar)

main()
