from workloads.array_sum_workload import (
    NaiveArraySumWorkload,
    ChunkingArraySumWorkload,
    NoResultRaceArraySumWorkload,
    ChunkingNoResultRaceArraySumWorkload,
    NoCacheBlockRaceArraySumWorkload,
    ChunkingNoBlockRaceArraySumWorkload,
)

from components.boards import HWX86Board
from components.memories import HWDDR4
from components.processors import HWO3CPU
from components.cache_hierarchies import HWMESITwoLevelCacheHierarchy

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

    board = HWX86Board(
        clk_freq=CLK_FREQ,
        processor=HWO3CPU(cores),
        memory=HWDDR4(),
        cache_hierarchy=HWMESITwoLevelCacheHierarchy(xbar_latency=xbar),
    )

    board.set_workload(cls(N_ELEMENTS, cores))

    simulator = Simulator(board, full_system=False, on_exit_event=exit_event_handler)
    simulator.run()

def main():
    parser = argparse.ArgumentParser(description='Gem5 Running Utility')
    parser.add_argument('-n', '--name', type=str, help='Name of the test to run')
    parser.add_argument('-c', '--cores', type=int, help='Number of logical cores (threads)')
    parser.add_argument('-x', '--xbar', type=int, help='XBar latency', default=10, required=False)

    args = parser.parse_args()

    run(args.name, args.cores, args.xbar)

main()
