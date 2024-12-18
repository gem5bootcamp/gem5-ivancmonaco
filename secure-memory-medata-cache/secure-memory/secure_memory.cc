/*
 * Copyright (c) 2012, 2014, 2017-2019, 2021 Arm Limited
 * All rights reserved
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 2002-2005 The Regents of The University of Michigan
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * Tutorial author: Samuel Thomas, Brown University
 */

#include "bootcamp/secure-memory/secure_memory.hh"

#include "debug/SecureMemoryDebugFlag.hh"

namespace gem5 {

void debugPacket(std::string func, PacketPtr pkt) {
    std::string pkt_read = pkt->isRead() ? "read" : "write";
    std::string pkt_data = pkt->hasData() ? "with data" : "without data";
    std::string pkt_addr = std::to_string(pkt->getAddr());
    std::string pkt_req = pkt->isRequest() ? "request" : "response";

    DPRINTF(SecureMemoryDebugFlag, "%s: Received %s %s %s for addr %s\n", func, pkt_read, pkt_req, pkt_data, pkt_addr);
}

Tick
SecureMemory::align(Tick when)
{
    return clockEdge((Cycles) std::ceil((when - curTick()) / clockPeriod()));
}

SecureMemory::SecureMemory(const SecureMemoryParams& params)
    :   ClockedObject(params),
        cpu_port(params.name + ".cpu_side", this),
        mem_port(params.name + ".mem_side", this),
        metadata_cache_request_port(params.name + ".metadata_cache_request_port", this),
        metadata_cache_response_port(params.name + ".metadata_cache_response_port", this),
        notInCacheEvent([this](){ processNotInCacheEvent(); }, name() + ".notInCacheEvent"),
        stats(*this)
{
}
Port&
SecureMemory::getPort(const std::string &if_name, PortID idx)
{
    if (if_name == "mem_side") {
        return mem_port;
    } else if (if_name == "cpu_side") {
        return cpu_port;
    } else if (if_name == "metadata_cache_request_port") {
        return metadata_cache_request_port;
    } else if (if_name == "metadata_cache_response_port") {
        return metadata_cache_response_port;
    }
    return ClockedObject::getPort(if_name, idx);
}
void
SecureMemory::startup()
{
    // setup address range for secure memory metadata
    AddrRangeList ranges = mem_port.getAddrRanges();
    assert(ranges.size() == 1);
    uint64_t start = ranges.front().start();
    uint64_t end = ranges.front().end();
    uint64_t hmac_bytes = ((end - start) / BLOCK_SIZE) * HMAC_SIZE;
    uint64_t counter_bytes = ((end - start) / PAGE_SIZE) * BLOCK_SIZE;
    // initialize integrity_levels
    uint64_t tree_offset = end + hmac_bytes;
    integrity_levels.push_front(start); // where does data start?
    integrity_levels.push_front(tree_offset); // where does tree start?
    uint64_t bytes_on_level = counter_bytes;
    do {
        integrity_levels.push_front(tree_offset + bytes_on_level); // level starting address
        tree_offset += bytes_on_level;
        bytes_on_level /= ARITY;
    } while (bytes_on_level > 1);
    integrity_levels.push_front(end); // hmac start
    integrity_levels.shrink_to_fit();
    data_level = integrity_levels.size() - 1;
    counter_level = data_level - 1;
}
uint64_t
SecureMemory::getHmacAddr(uint64_t child_addr)
{
    AddrRangeList ranges = mem_port.getAddrRanges();
    assert(ranges.size() == 1);
    uint64_t start = ranges.front().start();
    uint64_t end = ranges.front().end();
    if (!(child_addr >= start && child_addr < end)) {
        // this is a check for something that isn't metadata
        return (uint64_t) -1;
    }
    // raw location, not word aligned
    uint64_t hmac_addr = integrity_levels[hmac_level] + ((child_addr / BLOCK_SIZE) * HMAC_SIZE);
    // word aligned
    return hmac_addr - (hmac_addr % BLOCK_SIZE);
}
uint64_t
SecureMemory::getParentAddr(uint64_t child_addr)
{
    AddrRangeList ranges = mem_port.getAddrRanges();
    assert(ranges.size() == 1);
    uint64_t start = ranges.front().start();
    uint64_t end = ranges.front().end();
    if (child_addr >= start && child_addr < end) {
        // child is data, get the counter
        return integrity_levels[counter_level] + ((child_addr / PAGE_SIZE) * BLOCK_SIZE);
    }
    for (int i = counter_level; i > root_level; i--) {
        if (child_addr >= integrity_levels[i] && child_addr < integrity_levels[i - 1]) {
            // we belong to this level
            uint64_t index_in_level = (child_addr - integrity_levels[i]) / BLOCK_SIZE;
            return integrity_levels[i - 1] + ((index_in_level / ARITY) * BLOCK_SIZE);
        }
    }
    assert(child_addr == integrity_levels[root_level]);
    // assert(false); // we shouldn't ever get here
    return (uint64_t) -1;
}
bool
SecureMemory::handleRequest(PacketPtr pkt)
{
    debugPacket("SecureMemory::handleRequest", pkt);
    std::vector<uint64_t> metadata_addrs;
    uint64_t child_addr = pkt->getAddr();
    uint64_t hmac_addr = getHmacAddr(child_addr);
    metadata_addrs.push_back(hmac_addr);

    do {
        metadata_addrs.push_back(getParentAddr(child_addr));
        child_addr = metadata_addrs.back();
    } while (child_addr != integrity_levels[root_level]);

    pending_tree_authentication.insert(pkt->getAddr());
    pending_hmac.insert(pkt->getAddr());
    if (pkt->isWrite() && pkt->hasData()) {
        pending_untrusted_packets.insert(pkt);
    } else if (pkt->isRead()) {
        mem_port.sendPacket(pkt); // mem_port
    }

    for (uint64_t addr: metadata_addrs) {
        RequestPtr req = std::make_shared<Request>(addr, BLOCK_SIZE, 0, 0);
        PacketPtr metadata_pkt = Packet::createRead(req);
        metadata_pkt->allocate();
        if (addr != hmac_addr) {
            // note: we can't save the packet itself because it may be deleted
            // by the memory device :-)
            pending_tree_authentication.insert(addr);
        }
        metadata_cache_request_port.sendPacket(metadata_pkt); // mem_port
    }
    stats.requests_processed++;
    return true;
}
void
SecureMemory::verifyChildren(PacketPtr parent)
{
    debugPacket("SecureMemory::verifyChildren::1", parent);
    if (parent->getAddr() < integrity_levels[hmac_level]) {
        bool awaiting_hmac = false;
        debugPacket("SecureMemory::verifyChildren::2", parent);
        for (uint64_t addr: pending_hmac) {
            if (addr == parent->getAddr()) {
                awaiting_hmac = true;
            }
        }
        debugPacket("SecureMemory::verifyChildren::3", parent);
        if (!awaiting_hmac) {
            // we are authenticated!
            pending_tree_authentication.erase(parent->getAddr());
            debugPacket("SecureMemory::verifyChildren::4::authenticated", parent);
            if (parent->isWrite()) {
                // also send writes for all of the metadata
                mem_port.sendPacket(parent); // mem_port
            } else {
                cpu_port.sendPacket(parent);
            }
        }
        return;
    }
    std::vector<PacketPtr> to_call_verify;

    // verify all packets that have returned and are waiting
    for (auto it = pending_untrusted_packets.begin();
              it != pending_untrusted_packets.end(); ) {
        if (getParentAddr((*it)->getAddr()) == parent->getAddr()) {

            // someone was untrusted and waiting for us
            to_call_verify.push_back(*it);
            it = pending_untrusted_packets.erase(it);
        } else {
            ++it;
        }
    }
    // all done, free/remove node
    delete parent;
    for (PacketPtr pkt: to_call_verify) {
        verifyChildren(pkt);
    }
}
bool
SecureMemory::handleResponse(PacketPtr pkt)
{
    debugPacket("SecureMemory::handleResponse", pkt);
    if (pkt->isWrite() && pkt->getAddr() < integrity_levels[hmac_level]) {
        debugPacket("SecureMemory::handleResponse::1", pkt);
        // we are in metadata
        cpu_port.sendPacket(pkt);
        return true;
    }

    if (pkt->getAddr() >= integrity_levels[hmac_level] && pkt->getAddr() < integrity_levels[counter_level]) {
        debugPacket("SecureMemory::handleResponse::2", pkt);
        // authenticate the data
        for (auto it = pending_hmac.begin();
                  it != pending_hmac.end(); ) {
            if (getHmacAddr(*it) == pkt->getAddr()) {
                it = pending_hmac.erase(it);
                // using simple memory, so we can assume hmac
                // will always be verified first and not worry
                // about the case where cipher happens before verification
            } else {
                ++it;
            }
        }
        delete pkt;
        return true;
    }

    // we are no longer in memory
    pending_tree_authentication.erase(pkt->getAddr());
    if (pkt->getAddr() == integrity_levels[root_level]) {
        DPRINTF(SecureMemoryDebugFlag, "SecureMemory::handleResponse: root level: %d for pkt addr: %d\n", root_level, pkt->getAddr());
        // value is trusted, authenticate children
        verifyChildren(pkt);
        stats.responses_processed++;
    } else {
        debugPacket("SecureMemory::handleResponse::3", pkt);
        // move from pending address to pending metadata stored
        // in on-chip buffer for authentication
        pending_untrusted_packets.insert(pkt);
    }
    return true;
}
bool
SecureMemory::CpuSidePort::recvTimingReq(PacketPtr pkt)
{
    debugPacket("CpuSidePort::recvTimingReq", pkt);
    if (blocked || !parent->handleRequest(pkt)) {
        need_retry = true;
        return false;
    }
    return true;
}
void
SecureMemory::CpuSidePort::sendPacket(PacketPtr pkt)
{
    blocked_packets.push_back(pkt);
    PacketPtr to_send = blocked_packets.front();
    debugPacket("CpuSidePort::sendPacket", to_send);
    if (sendTimingResp(to_send)) {
        blocked_packets.pop_front();
        if (blocked) {
            blocked = false;
        }
        if (need_retry) {
            sendRetryReq();
            need_retry = false;
        }
    }
}

bool
SecureMemory::MemSidePort::recvTimingResp(PacketPtr pkt)
{
    debugPacket("MemSidePort::recvTimingResp", pkt);
    return parent->handleResponse(pkt);
}

void
SecureMemory::MetadataCacheResponsePort::recvRespRetry()
{
    debugPacket("MetadataCacheResponsePort::recvRespRetry", not_in_cache_pkts.front());
}

void
SecureMemory::MemSidePort::recvReqRetry()
{
    debugPacket("MemSidePort::recvReqRetry", blocked_packets.front());
    assert(!blocked_packets.empty());
    // the while is important here to receive a retry
    while (!blocked_packets.empty() &&
           sendTimingReq(blocked_packets.front())) {
        blocked_packets.pop_front();
    }
}

void
SecureMemory::MetadataCacheRequestPort::recvReqRetry()
{
    debugPacket("MetadataCacheRequestPort::recvReqRetry", blocked_packets.front());
    assert(!blocked_packets.empty());
    // the while is important here to receive a retry
    while (!blocked_packets.empty() &&
           sendTimingReq(blocked_packets.front())) {
        blocked_packets.pop_front();
    }
}

void
SecureMemory::MemSidePort::sendPacket(PacketPtr pkt)
{
    debugPacket("MemSidePort::sendPacket", pkt);
    if (!sendTimingReq(pkt)) {
        blocked_packets.push_back(pkt);
    }
}

SecureMemory::SecureMemoryStats::SecureMemoryStats(SecureMemory &m)
    : statistics::Group(&m), m(m),
      ADD_STAT(requests_processed, statistics::units::Count::get(),
               "number of requests from the processor side that we've handled"),
      ADD_STAT(responses_processed, statistics::units::Count::get(),
               "number of memory responses that we've handled")
{
}
void
SecureMemory::SecureMemoryStats::regStats()
{
    statistics::Group::regStats();
}

void
SecureMemory::MetadataCacheRequestPort::sendPacket(PacketPtr pkt)
{
    debugPacket("MetadataCacheRequestPort::sendPacket", pkt);
    bool success = sendTimingReq(pkt);
    if (!success) {
        blocked_packets.push_back(pkt);
    }
}

bool
SecureMemory::MetadataCacheRequestPort::recvTimingResp(PacketPtr pkt)
{
    debugPacket("MetadataCacheRequestPort::recvTimingResp", pkt);

    RequestPtr req = std::make_shared<Request>(pkt->getAddr(), BLOCK_SIZE, 0, 0);
    PacketPtr mem_pkt = Packet::createRead(req);
    mem_pkt->allocate();
    parent->mem_port.sendPacket(mem_pkt);
    return true;
}

bool
SecureMemory::MetadataCacheResponsePort::recvTimingReq(PacketPtr pkt)
{
    debugPacket("MetadataCacheResponsePort::recvTimingReq", pkt);
    pkt->makeTimingResponse();
    not_in_cache_pkts.push_back(pkt);
    parent->scheduleNotInCacheEvent(parent->nextCycle());
    return true;
}

void SecureMemory::MetadataCacheResponsePort::answer()
{
    if(not_in_cache_pkts.empty()){
        return;
    }

    PacketPtr pkt = not_in_cache_pkts.front();

    if(sendTimingResp(pkt)){
        debugPacket("MetadataCacheResponsePort::answer", pkt);
        not_in_cache_pkts.pop_front();
    }

    parent->scheduleNotInCacheEvent(parent->nextCycle());
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

} // namespace gem5

