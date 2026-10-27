// Dependency-free tests: `make test` builds and runs this file.
#include <cmath>
#include <iostream>
#include <map>
#include <string>
#include <vector>

#include "hash_ring.hpp"
#include "lru_cache.hpp"

static int g_run = 0;
static int g_failed = 0;

#define CHECK(cond, name)                                  \
    do {                                                   \
        ++g_run;                                           \
        if (!(cond)) {                                     \
            ++g_failed;                                    \
            std::cout << "FAIL: " << (name) << std::endl;  \
        }                                                  \
    } while (0)

static std::vector<std::string> make_keys(int n) {
    std::vector<std::string> keys;
    for (int i = 0; i < n; ++i) keys.push_back("user:" + std::to_string(i));
    return keys;
}

static void ring_tests() {
    const auto keys = make_keys(5000);

    dblab::HashRing a, b;
    for (auto n : {"n1", "n2", "n3"}) a.add_node(n);
    for (auto n : {"n3", "n1", "n2"}) b.add_node(n);
    bool same = true;
    for (const auto& k : keys) same = same && a.get_node(k) == b.get_node(k);
    CHECK(same, "ring is deterministic");

    dblab::HashRing ring;
    for (auto n : {"n1", "n2", "n3", "n4"}) ring.add_node(n);
    std::map<std::string, std::string> before;
    std::map<std::string, int> load;
    for (const auto& k : keys) {
        before[k] = ring.get_node(k);
        ++load[before[k]];
    }
    bool balanced = true;
    for (const auto& kv : load) balanced = balanced && kv.second > 0.6 * keys.size() / 4;
    CHECK(balanced, "load is roughly balanced");

    ring.add_node("n5");
    int moved = 0;
    bool only_to_new = true;
    for (const auto& k : keys) {
        if (ring.get_node(k) != before[k]) {
            ++moved;
            only_to_new = only_to_new && ring.get_node(k) == "n5";
        }
    }
    CHECK(moved < 0.30 * keys.size(), "adding a node moves under 30% of keys");
    CHECK(only_to_new, "keys only move to the new node");

    bool distinct = true;
    for (int i = 0; i < 200; ++i) {
        auto owners = ring.get_nodes(keys[i], 3);
        distinct = distinct && owners.size() == 3 && owners[0] != owners[1] && owners[1] != owners[2] &&
                   owners[0] != owners[2];
    }
    CHECK(distinct, "replica nodes are distinct");

    ring.remove_node("n5");
    bool restored = true;
    for (const auto& k : keys) restored = restored && ring.get_node(k) == before[k];
    CHECK(restored, "removing the node restores the old placement");

    bool threw = false;
    try {
        dblab::HashRing().get_node("x");
    } catch (const std::logic_error&) {
        threw = true;
    }
    CHECK(threw, "empty ring throws");
}

static void lru_tests() {
    dblab::LruCache<std::string, int> cache(2);
    cache.put("a", 1);
    cache.put("b", 2);
    CHECK(cache.get("a").value_or(-1) == 1, "get returns stored value");
    cache.put("c", 3);  // "b" is now least recently used
    CHECK(!cache.contains("b"), "least recently used entry is evicted");
    CHECK(cache.contains("a") && cache.contains("c"), "recent entries survive");
    CHECK(cache.size() == 2, "size never exceeds capacity");
    CHECK(!cache.get("zzz").has_value(), "miss returns nullopt");
    CHECK(std::fabs(cache.hit_rate() - 0.5) < 1e-9, "hit rate counts hits and misses");
    cache.put("a", 10);
    CHECK(cache.get("a").value_or(-1) == 10, "put overwrites an existing key");

    bool threw = false;
    try {
        dblab::LruCache<int, int> bad(0);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    CHECK(threw, "zero capacity is rejected");
}

int main() {
    ring_tests();
    lru_tests();
    std::cout << (g_run - g_failed) << "/" << g_run << " C++ checks passed" << std::endl;
    return g_failed == 0 ? 0 : 1;
}
