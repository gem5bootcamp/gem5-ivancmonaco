# Secure Memory Metadata Cache

## Author

Ivan Monaco (ivancmonaco@gmail.com)

## Introduction

We want to include an internal cache in the secure memory module, to be able to retrieve faster the metadata from every packet, avoiding to fetch them from memory every time.

## Implementation

We were not able to complete the whole experiment. We achieved the cache add next to the secure memory module, but we lack the return-early logic.

What we did was:

- First we modify the Packet class definition, to include an isHit attribute, which will be used to determine if the cache access was a hit or a miss.

    ```cpp
    class Packet : public Printable, public Extensible<Packet>
    {
        ...
        public:

        ...

        bool isHit = true;

        ...

    }
    ```

- Then we created a metadata cache extending the Cache class (which itself extends the BaseCache class).
    - In this new class we are going to override the handleTimingReqHit and handleTimingReqMiss virtual methods, to un/set the new isHit attribute of the Packet class.

    ```cpp
      class MetadataCache : public Cache
    {

        public:
        MetadataCache(const MetadataCacheParams& params);

        void handleTimingReqHit(PacketPtr pkt, CacheBlk *blk, Tick request_time) override;
        void handleTimingReqMiss(PacketPtr pkt, CacheBlk *blk, Tick forward_time, Tick request_time) override;
    };

    ```

    ```cpp

    void
    MetadataCache::handleTimingReqHit(PacketPtr pkt, CacheBlk *blk, Tick request_time)
    {
        pkt->isHit = true;
        Cache::handleTimingReqHit(pkt, blk, request_time);
    }

    void
    MetadataCache::handleTimingReqMiss(PacketPtr pkt, CacheBlk *blk, Tick forward_time, Tick request_time)
    {
        pkt->isHit = false;
        Cache::handleTimingReqMiss(pkt, blk, forward_time, request_time);
    }

    ```


- We were unable to include the secure memory algorithm in the Inspected Memory (the buffer one created during the bootcamp), so we just used the provided implementation in the repo from Samuel Thomas.
- In this implementation we added 2 ports, a request and a response one, and connect them to the new metadata cache. The default setting for the metadata cache was 4096 KiB with 8 ways, and a overall latency of 1.

    ```cpp
        class MetadataCacheRequestPort : public MemSidePort
        {
        public:
            MetadataCacheRequestPort(const std::string &name, SecureMemory *parent);

            void sendPacket(PacketPtr pkt) override;
            bool recvTimingResp(PacketPtr pkt) override;
            void recvReqRetry() override;

            std::deque<PacketPtr> pending_answers;

            EventFunctionWrapper answerEvent;
            void processAnswerEvent();
            void scheduleAnswerEvent(Tick when);
        };
    ```

    ```cpp
        class MetadataCacheResponsePort : public CpuSidePort
        {
        private:
            std::deque<PacketPtr> not_in_cache_pkts;

        public:
            MetadataCacheResponsePort(const std::string &name, SecureMemory *parent)
                : CpuSidePort(name, parent) {};

        bool recvTimingReq(PacketPtr pkt) override;

        void recvRespRetry() override;

        void answer();

        };
    ```

    ```python

    class SecureMemorySystem(AbstractMemorySystem):

        ...

        self.metadata_cache = MetadataCache(size="16 KiB", assoc=8)
        self.secure_memory = SecureMemory()

        self.secure_memory.metadata_cache_request_port = self.metadata_cache.cpu_side
        self.metadata_cache.mem_side = self.secure_memory.metadata_cache_response_port

        self.secure_memory.mem_side = self.module.port

    ```

- Next, we changed the every memory request port for the metadata request port.
- The flow changed like this:
    - Save the original packet
    - Create a new packet and forward it to the cache
    - Wait for the response
    - If the response is a hit, we call handleResponse with the original packet
    - If the response is a miss, we forward the original packet to the memory port, as in the original implementation.

    ```cpp
        void
        SecureMemory::MetadataCacheRequestPort::sendPacket(PacketPtr pkt)
        {

            pending_answers.push_back(pkt);

            PacketPtr cache_pkt = pkt->isRead() ? Packet::createRead(pkt->req) : Packet::createWrite(pkt->req);
            cache_pkt->allocate();

            if (!sendTimingReq(cache_pkt);) {
                blocked_packets.push_back(cache_pkt);
            }
        }

        bool
        SecureMemory::MetadataCacheRequestPort::recvTimingResp(PacketPtr pkt)
        {
            assert(!pending_answers.empty());

            PacketPtr mem_pkt = pending_answers.front();
            pending_answers.pop_front();

            if(pkt->isHit){
                parent->handleResponse(pkt);
            } else {
                parent->mem_port.sendPacket(mem_pkt);
            }

            return true;
        }
    ```

- If the cache does not have the packet, it will forward it to the MetadataCacheResponsePort, where we are going to just responde that with the same packet.

    ```cpp
        bool
        SecureMemory::MetadataCacheResponsePort::recvTimingReq(PacketPtr pkt)
        {
            if(!pkt->needsResponse()){
                return true;
            }
            pkt->makeTimingResponse();
            not_in_cache_pkts.push_back(pkt);
            parent->scheduleNotInCacheEvent(parent->nextCycle());
            return true;
        }

        void
        SecureMemory::scheduleNotInCacheEvent(Tick when)
        {
            if (!notInCacheEvent.scheduled()) {
                schedule(notInCacheEvent, when);
            }
        }

        void SecureMemory::processNotInCacheEvent()
        {
            metadata_cache_response_port.answer();
        }


        void SecureMemory::MetadataCacheResponsePort::answer()
        {
            if(not_in_cache_pkts.empty()){
                return;
            }

            PacketPtr pkt = not_in_cache_pkts.front();

            if(sendTimingResp(pkt)){
                not_in_cache_pkts.pop_front();
            }

            parent->scheduleNotInCacheEvent(parent->nextCycle());
        }
    ```

## Limitations

As I said before, we were not able to complete the whole experiment. We were unable to implement the return-early logic, so we are not able to avoid the memory access in case of a cache hit.
Moreover, we were unable to test the fully implementation, because after we succesfully validated several packages we were prompted with a Sequencer assertion error, which we were unable to solve:

```bash
    src/mem/ruby/system/Sequencer.cc:256: panic: Possible Deadlock detected. Aborting!
    version: 0 request.paddr: 0x1fada0 m_readRequestTable: 1 current time: 333000000 issue_time: 828837 difference: 332171163
 ```

## Results

To be able to showcase something, we are going to present two results, one with the original memory, and one with the vanilla secure memory.

**We forecast that our cache implementation would be a middle ground between the two.**

For the experiments we ran the NaiveArraySumWorkload from the 2nd homework.

Our test machine is:

- CPU: HW5O3CPU
    - A single core, out of order CPU
    - 3 GHz clock
- A Ruby MESI Two Level cache hierarchy with a XBar latency of 10
- For the memory we are going to run 2 GiB, 1 GiB/S latency and 150 ns of latency.
    - First with a simple memory
    - Then with the secure memory


#### Simulation Seconds

| Simple Memory | Secure Memory | Difference %   |
|---------------|---------------|----------------|
|  0.000872     |  0.001157     |  ~35 %         |


#### Simulated instructions

| Simple Memory | Secure Memory | Difference %   |
|---------------|---------------|----------------|
|  1449464      |  1449464      |  0 %           |
