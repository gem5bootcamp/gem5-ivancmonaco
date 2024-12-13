from m5.objects import (
    Cache,
)

from m5.objects.ReplacementPolicies import RandomRP, TreePLRURP

class L3Cache(Cache):
    def __init__(self, size: str="64KiB", assoc:int = 8, *args, **kwargs):
        super().__init__(size=size, assoc=assoc, *args, **kwargs)
        self.tag_latency = 20
        self.data_latency = 20
        self.response_latency = 1
        self.mshrs = 20
        self.tgts_per_mshr = 12
        self.writeback_clean = False
        self.clusivity = "mostly_incl"

class L3RandomRPCache(L3Cache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.replacemente_policy = RandomRP()

class L3TreeRPCache(L3Cache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.replacemente_policy = TreePLRURP()

