// Fixed-capacity least-recently-used cache (header-only, C++17).
//
// A doubly linked list orders entries by recency (front = newest) and a hash map points
// into the list, so get and put are both O(1). `splice` moves a node without copying it.
#pragma once

#include <cstddef>
#include <list>
#include <optional>
#include <stdexcept>
#include <unordered_map>
#include <utility>

namespace dblab {

template <class K, class V>
class LruCache {
public:
    explicit LruCache(std::size_t capacity) : capacity_(capacity) {
        if (capacity == 0) throw std::invalid_argument("capacity must be positive");
    }

    std::optional<V> get(const K& key) {
        auto it = index_.find(key);
        if (it == index_.end()) {
            ++misses_;
            return std::nullopt;
        }
        order_.splice(order_.begin(), order_, it->second);  // mark as most recently used
        ++hits_;
        return it->second->second;
    }

    void put(const K& key, V value) {
        auto it = index_.find(key);
        if (it != index_.end()) {
            it->second->second = std::move(value);
            order_.splice(order_.begin(), order_, it->second);
            return;
        }
        order_.emplace_front(key, std::move(value));
        index_[key] = order_.begin();
        if (order_.size() > capacity_) {
            index_.erase(order_.back().first);
            order_.pop_back();
        }
    }

    bool contains(const K& key) const { return index_.count(key) > 0; }  // does not change recency
    std::size_t size() const { return order_.size(); }

    double hit_rate() const {
        auto total = hits_ + misses_;
        return total == 0 ? 0.0 : static_cast<double>(hits_) / static_cast<double>(total);
    }

private:
    using Entry = std::pair<K, V>;
    std::size_t capacity_;
    std::list<Entry> order_;
    std::unordered_map<K, typename std::list<Entry>::iterator> index_;
    std::size_t hits_ = 0;
    std::size_t misses_ = 0;
};

}  // namespace dblab
