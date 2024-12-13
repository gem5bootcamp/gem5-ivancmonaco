# Design Space Exploration

## Author

Ivan Monaco (ivancmonaco@gmail.com)

## Introduction

For this experiment, we want to explore and different cache and memory configurations. In order to do that, we are going to run 36 different experiments, being the cross product of the following:

- 2 workloads: matrix-multiply and bfs
- 3 memory configurations: 1 , 2 and 4 channels.
- 2 processors: BigProcessor and LittleProcessor.
- 3 cache configurations: shared three level with default LRU RP and with Random RP, and a shared four level cache.

## Setup

Besides the moving parts, we are going to use the following fixed equipment:

- A SimpleBoard
- 3 GHz as frequency
- LPDDR5 5500 MHz 1x16 2GiB as memory (with 1 , 2 , or 4 channels as mentioned)
- Caches will have 32KiB as L1 (both), 256KiB for L2, 1024 KiB for L3, and (when applicable) 4096 KiB for L4.

## Results

![Matrix Multiply with Big Processor](http://design-space-exploration/results/Figure_1.png)
![Matrix Multiply with Little Processor](http://design-space-exploration/results/Figure_2.png)
![BFS with Big Processor](http://design-space-exploration/results/Figure_3.png)
![BFS with Little Processor](http://design-space-exploration/results/Figure_4.png)



