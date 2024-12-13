from .cores import LittleCore
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor

class LittleProcessor(BaseCPUProcessor):
    def __init__(self):
        super().__init__(cores=[
            LittleCore()
        ])
