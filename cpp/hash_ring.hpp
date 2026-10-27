// Consistent hash ring with virtual nodes (header-only, C++17).
//
// A key belongs to the first node clockwise from the key's hash. When a node joins or
// leaves, only the keys in its arc move (about 1/n of them), unlike `hash(key) % n`.
#pragma once

#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace dblab {

// FNV-1a followed by a 64-bit finalizer (from MurmurHash3). Plain FNV-1a clusters badly
// for keys that differ only in their last characters, like "node#1", "node#2".
inline std::uint64_t hash64(const std::string& s) {
    std::uint64_t h = 1469598103934665603ULL;
    for (unsigned char c : s) {
        h ^= c;
        h *= 1099511628211ULL;
    }
    h ^= h >> 33;
    h *= 0xff51afd7ed558ccdULL;
    h ^= h >> 33;
    h *= 0xc4ceb9fe1a85ec53ULL;
    h ^= h >> 33;
    return h;
}

class HashRing {
public:
    explicit HashRing(int vnodes = 128) : vnodes_(vnodes) {
        if (vnodes < 1) throw std::invalid_argument("vnodes must be >= 1");
    }

    void add_node(const std::string& node) {
        if (!nodes_.insert(node).second) return;
        for (int i = 0; i < vnodes_; ++i) ring_[hash64(node + "#" + std::to_string(i))] = node;
    }

    void remove_node(const std::string& node) {
        if (nodes_.erase(node) == 0) throw std::invalid_argument("unknown node: " + node);
        for (auto it = ring_.begin(); it != ring_.end();) {
            it = (it->second == node) ? ring_.erase(it) : std::next(it);
        }
    }

    const std::set<std::string>& nodes() const { return nodes_; }

    const std::string& get_node(const std::string& key) const {
        if (ring_.empty()) throw std::logic_error("the ring has no nodes");
        auto it = ring_.lower_bound(hash64(key));
        return (it == ring_.end() ? ring_.begin() : it)->second;
    }

    // Up to `count` distinct nodes, walking clockwise from the key's position.
    std::vector<std::string> get_nodes(const std::string& key, std::size_t count) const {
        if (ring_.empty()) throw std::logic_error("the ring has no nodes");
        count = std::min(count, nodes_.size());
        std::vector<std::string> found;
        auto it = ring_.lower_bound(hash64(key));
        for (std::size_t step = 0; step < ring_.size() && found.size() < count; ++step) {
            if (it == ring_.end()) it = ring_.begin();
            if (std::find(found.begin(), found.end(), it->second) == found.end()) found.push_back(it->second);
            ++it;
        }
        return found;
    }

private:
    int vnodes_;
    std::map<std::uint64_t, std::string> ring_;
    std::set<std::string> nodes_;
};

}  // namespace dblab
