# Cache Coherence

## Author

Ivan Monaco (ivancmonaco@gmail.com)

## Introduction

We will take a very simple application, summing the values in an array, and see how if you are not careful how you parallelize the application, the performance will become quite poor.

Then, after seeing which algorithms perform well and poorly on real hardware, we will use gem5, a cycle-level simulator, with a detailed cache model to understand the performance.

## Results

### Hardware Results

Lets first load up and build tables for all our results.

All tests were ran in a x86 native 12-core processor running Ubuntu 22.x.y.
They were ran 100 times and the average was taken.

The following table shows which tests was run (Thread configuration + number of cores) and how long does it take to complete, in ascending order (lower is better).

| #  | Test                    | Cores | Average Time (ms) |
|----|-------------------------|-------|-------------------|
| 0  | Block race opt         | 4     | 0.220384          |
| 1  | All opt                | 4     | 0.226861          |
| 2  | Block race opt         | 2     | 0.229220          |
| 3  | All opt                | 2     | 0.244881          |
| 4  | Naive                  | 1     | 0.323143          |
| 5  | Res race opt           | 1     | 0.326467          |
| 6  | Block race opt         | 1     | 0.329142          |
| 7  | Chunking res race opt  | 1     | 0.332100          |
| 8  | Chunking               | 1     | 0.332399          |
| 9  | All opt                | 1     | 0.337583          |
| 10 | Block race opt         | 8     | 0.341541          |
| 11 | All opt                | 8     | 0.356096          |
| 12 | All opt                | 12    | 0.406281          |
| 13 | Block race opt         | 12    | 0.414171          |
| 14 | Chunking res race opt  | 2     | 0.580947          |
| 15 | Res race opt           | 2     | 0.587572          |
| 16 | Naive                  | 2     | 0.595884          |
| 17 | Chunking               | 2     | 0.610594          |
| 18 | Chunking               | 4     | 0.630850          |
| 19 | Chunking res race opt  | 4     | 0.633819          |
| 20 | Chunking res race opt  | 12    | 0.639322          |
| 21 | Naive                  | 4     | 0.645525          |
| 22 | Chunking               | 8     | 0.646897          |
| 23 | Naive                  | 8     | 0.648690          |
| 24 | Naive                  | 12    | 0.649543          |
| 25 | Res race opt           | 4     | 0.652155          |
| 26 | Chunking               | 12    | 0.655746          |
| 27 | Chunking res race opt  | 8     | 0.662393          |
| 28 | Res race opt           | 12    | 0.668676          |
| 29 | Res race opt           | 8     | 0.676898          |

Now, with this data we can try to answer the first 3 questions

#### Question 1

**For algorithm 1, does increasing the number of threads improve performance or hurt performance? **

Lets filter out only the first and sixth algorithm (Naive and All optimizations)

| Test    | Cores | Average Time (ms) |
|---------|-------|-------------------|
| All opt | 4     | 0.226861          |
| All opt | 2     | 0.244881          |
| Naive   | 1     | 0.323143          |
| All opt | 1     | 0.337583          |
| All opt | 8     | 0.356096          |
| All opt | 12    | 0.406281          |
| Naive   | 2     | 0.595884          |
| Naive   | 4     | 0.645525          |
| Naive   | 8     | 0.648690          |
| Naive   | 12    | 0.649543          |

Being the algorithm 1 , the 'Naive' implementation, we can see that the test with just 1 thread did pretty much better than the threaded implementation.

Naive algorithm took double the time to complete comparing runs with 1 and with 12 cores.
With this data we can assert that the thread count increase, actually hurt algorithm 1 performance.

#### Question 2

**(a) For algorithm 6, does increasing the number of threads improve performance or hurt performance? Use data to back up your answer.**

In the other hand, Algorithm 6 (all optimizations enabled), did much better when increasing the thread count, but up to 4, then the trend reverted, and behaved like the naive algorithm.

**(b) What is the speedup when you use 2, 4, 8, and 16 threads (only answer with up to the number of cores on your system).**

| Threads | Relative Performance |
|---------|----------------------|
| 1       | 100%                |
| 2       | 128%                |
| 4       | 133%                |
| 8       | 95%                 |
| 12      | 83%                 |


## Question 3

**(a) Using the data for all 6 algorithms, what is the most important optimization, chunking the array, using different result addresses, or putting padding between the result addresses?**

Assuming based on (2) that the ideal amount of threads for this experiment is 4, lets filter out the data and see how the implementations with 4 threads compare to each other

| Test                   | Cores | Average Time (ms) |
|------------------------|-------|-------------------|
| Block race opt         | 4     | 0.220384          |
| All opt                | 4     | 0.226861          |
| Chunking               | 4     | 0.630850          |
| Chunking res race opt  | 4     | 0.633819          |
| Naive                  | 4     | 0.645525          |
| Res race opt           | 4     | 0.652155          |


We can see that up to the top of the table there is the block race optimization, which is in fact the fastest global algorithm with the 4 threads configuration.
This implementation, comparing it with the naive implementation using also 4 threads, is about 3 times faster.

**(b) Speculate how the hardware implementation is causing this result. What is it about the hardware that causes this optimization to be most important?**

The cache line width is responsible. In this case we are using blocks of 64B exclusively for each thread , in an independent form, reducing caches writes to memory.

### Gem5 Simulation Results

#### Question 4

**(a) What is the speedup of algorithm 1 and speedup of algorithm 6 on 16 cores as estimated by gem5?**

| Test    | Cores | Time Taken (s) |
|---------|-------|----------------|
| All opt | 16    | 0.000111       |
| Naive   | 1     | 0.000838       |
| All opt | 1     | 0.000839       |
| Naive   | 16    | 0.000917       |

We can clearly see that the difference is abismal for the sixth algorithm: 656% speedup!

For the naive algorithm it actually hurted its performance.

**(b) How does this compare to what you saw on the real system?**

This behavior matches what we saw in the real world.

The difference relies on the abismal difference on the x16 cores with the all optimizations enabled ( we saw an increase, but not that much!)

#### Question 5

**Which optimization (chunking the array, using different result addresses, or putting padding between the result addresses) has the biggest impact on the hit ratio?**

Lets load the data. We are going to use the L1D demand hit stat (greater is better) for the first core of each implementation ( we are using 16 cores for each experiment )

| Test                     | Cache Hit |
|--------------------------|-----------|
| All opt                  | 35942.0   |
| Chunking res race opt    | 35721.0   |
| Chunking                 | 31936.0   |
| Block race opt           | 29863.0   |
| Res race opt             | 27570.0   |
| Naive                    | 25823.0   |

The hit ratio is affected by all of them, as the all optimizations experiment had a better results than naive (we can even see that the all opt test rank the better, as each optimization contributed)

However, individually, the chunking combined with the address change wins the battle.

#### Question 6

**Which optimization (chunking the array, using different result addresses, or putting padding between the result addresses) has the biggest impact on the read sharing?**

This question is answered comparing all the algorithms with 16 cores as the thread configuration, and checking the sum of the read sharing stats of each core.

| Test                 | Read Sharing |
|------------------------|-------------:|
| Chunking               |       194.0  |
| Chunking res race opt  |       199.0  |
| All opt                |       223.0  |
| Block race             |     1193.0   |
| Naive                  |     1970.0   |
| Res race opt           |     1974.0   |

We can see that the biggest impact is made by the Chunking optimization.

#### Question 7

**Which optimization (chunking the array, using different result addresses, or putting padding between the result addresses) has the biggest impact on the write sharing?**

This question is answered comparing all the algorithms with 16 cores as the thread configuration, and checking the sum of the write sharing stats of each core.


| Test                 | Write Sharing |
|------------------------|--------------:|
| Block race            |         152.0 |
| All opt               |         186.0 |
| Chunking res race opt |       32735.0 |
| Res race opt          |       32774.0 |
| Chunking              |       32820.0 |
| Naive                 |       32864.0 |

We can see that the biggest impact is made by the Block race optimization (by far, and the only one that made something).


#### Question 8

**(a) Out of the three characteristics we have looked at, the L1 hit ratio, the read sharing, or the write sharing, which is most important for determining performance?**

Looking at the global table and seeing that the Block race optimization performed the best, and seeing the brutal difference in the write sharing table, I can conclude that the write sharing stat is the most important characteristic to look when determining performance. This makes sense, as every time a core write to a shared cache line, all the threads halt to let this cache coherence take place.

**(b) Using data from the gem5 simulations, now answer what hardware characteristic causes the most important optimization to be the most important.**

As we just said, a good cache coherence in your cache hierarchy is the best optimization to gain performance.


#### Question 9


**As you increase the cache-to-cache latency, how does it affect the importance of the different optimizations?**

We ran naive and all opt tests, with same number of cores, with x bar latency of 1, 10, and 25.

| Test     | X Bar Latency | Time Taken (s) |
|----------|---------------|----------------|
| All opt  | 1             | 0.000226       |
| All opt  | 10            | 0.000236       |
| All opt  | 25            | 0.000251       |
| Naive    | 1             | 0.000347       |
| Naive    | 10            | 0.000818       |
| Naive    | 25            | 0.000958       |

We can see that the X Bar latency has a huge impact on the performance, outweighting the importance of the optimizations.

If we reduce to a minimum of 1 this latency, the 2 algorithms are not that far from each other, even after all our optimization work!
