import argparse
from gem5.utils.multisim import multisim

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import PrivateL1CacheHierarchy as DefaultCache
from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import PrivateL1CacheHierarchy
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import PrivateL1PrivateL2CacheHierarchy
from gem5.components.cachehierarchies.classic.private_l1_shared_l2_cache_hierarchy import PrivateL1SharedL2CacheHierarchy
from components.four_level_cache import PrivateL1PrivateL2SharedL3SharedL4CacheHierarchy
from gem5.components.memory.single_channel import SingleChannelDDR4_2400 as DefaultMemory
from gem5.components.memory.dram_interfaces.lpddr5 import LPDDR5_5500_1x16_8B_BL32, LPDDR5_5500_1x16_BG_BL16
from components.three_level_cache import PrivateL1PrivateL2SharedL3CacheHierarchy, PrivateL1PrivateL2SharedL3CacheHierarchyRandomRP, PrivateL1PrivateL2PrivateL3CacheHierarchy
from gem5.components.memory.memory import ChanneledMemory
from gem5.components.memory.dram_interfaces.ddr4 import DDR4_2400_8x8, DDR4_2400_16x4, DDR4_2400_4x16

from components.little_processor import LittleProcessor
from components.big_processor import BigProcessor

from gem5.resources.workload import obtain_resource

from gem5.simulate.simulator import Simulator

import m5
from gem5.simulate.exit_event import ExitEvent

def handle_workbegin():
    while True:
        m5.stats.reset()
        yield False


def handle_workend():
    while True:
        m5.stats.dump()
        yield True


exit_event_handler = {
    ExitEvent.WORKBEGIN: handle_workbegin(),
    ExitEvent.WORKEND: handle_workend(),
}

caches = {
    "three_level": lambda: PrivateL1PrivateL2SharedL3CacheHierarchy("32KiB", "32KiB", "256KiB", "1024KiB", l1d_assoc=4, l1i_assoc=4, l2_assoc=8, l3_assoc=8),
    "three_level_random": lambda: PrivateL1PrivateL2SharedL3CacheHierarchyRandomRP("32KiB", "32KiB", "256KiB", "1024KiB", l1d_assoc=4, l1i_assoc=4, l2_assoc=8, l3_assoc=8),
    "four_level": lambda: PrivateL1PrivateL2SharedL3SharedL4CacheHierarchy("32KiB", "32KiB", "256KiB", "1024KiB", "4096KiB", l1d_assoc=4, l1i_assoc=4, l2_assoc=8, l3_assoc=8, l4_assoc=16),
    # "three_level_private": lambda: PrivateL1PrivateL2PrivateL3CacheHierarchy("32KiB", "32KiB", "256KiB", "1024KiB", l1d_assoc=4, l1i_assoc=4, l2_assoc=8, l3_assoc=8),
}

memories = {
    "1": lambda: ChanneledMemory(LPDDR5_5500_1x16_8B_BL32, 1, 64, "2GiB"),
    "2": lambda: ChanneledMemory(LPDDR5_5500_1x16_8B_BL32, 2, 64, "2GiB"),
    "4": lambda: ChanneledMemory(LPDDR5_5500_1x16_8B_BL32, 4, 64, "2GiB"),
}

workload_id = 1
workloads_ids = [workload_id]
workloads = [workload for workload in obtain_resource("riscv-getting-started-benchmark-suite")]
workloads = [workload for i,workload in enumerate(workloads) if i in workloads_ids]
workloads = {workload.get_id(): workload for workload in workloads}

processors = {
    "big": lambda: BigProcessor(),
    "little": lambda: LittleProcessor(),
}


def test_case(processor, cache, memory, workload):
    board = SimpleBoard(
        processor=processors[processor](),
        cache_hierarchy=caches[cache](),
        memory=memories[memory](),
        clk_freq="3GHz",
    )

    board.set_workload(workload=workloads[workload])

    return Simulator(board, full_system=False, on_exit_event=exit_event_handler, id=f"{workload}-{processor}-{memory}-{cache}")

# multisim.set_num_processes(3)
# workloads_keys = list(workloads.keys())
# workload_id = 8

# for workload in workloads.keys():
#     for processor in processors.keys():
#         for memory in memories.keys():
#             for cache in caches.keys():
#                 multisim.add_simulator(test_case(processor, cache, memory, workload))

# print(workloads_keys)
# print(workloads_keys[workload_id])
test_case("big", "four_level", "2", list(workloads.keys())[0]).run()
