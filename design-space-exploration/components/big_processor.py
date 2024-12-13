from .cores import BigCore
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor

class BigProcessor(BaseCPUProcessor):
    def __init__(self):
        super().__init__(cores=[
            BigCore()
        ])
