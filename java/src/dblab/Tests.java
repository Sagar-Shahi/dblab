package dblab;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Dependency-free test runner so the project builds with nothing but a JDK. */
public final class Tests {
    private static int run = 0;
    private static int failed = 0;

    private static void check(boolean condition, String name) {
        run++;
        if (!condition) {
            failed++;
            System.out.println("FAIL: " + name);
        }
    }

    private static List<String> keys(int n) {
        List<String> keys = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            keys.add("user:" + i);
        }
        return keys;
    }

    private static void ringTests() {
        List<String> keys = keys(5000);

        HashRing a = new HashRing(128);
        HashRing b = new HashRing(128);
        for (String n : List.of("n1", "n2", "n3")) {
            a.addNode(n);
        }
        for (String n : List.of("n3", "n1", "n2")) {
            b.addNode(n);
        }
        check(keys.stream().allMatch(k -> a.getNode(k).equals(b.getNode(k))), "ring is deterministic");

        HashRing ring = new HashRing(128);
        for (String n : List.of("n1", "n2", "n3", "n4")) {
            ring.addNode(n);
        }
        Map<String, String> before = new HashMap<>();
        Map<String, Integer> load = new HashMap<>();
        for (String k : keys) {
            before.put(k, ring.getNode(k));
            load.merge(ring.getNode(k), 1, Integer::sum);
        }
        check(load.values().stream().allMatch(c -> c > 0.6 * keys.size() / 4), "load is roughly balanced");

        ring.addNode("n5");
        int moved = 0;
        boolean onlyToNewNode = true;
        for (String k : keys) {
            String now = ring.getNode(k);
            if (!now.equals(before.get(k))) {
                moved++;
                onlyToNewNode &= now.equals("n5");
            }
        }
        check(moved < 0.30 * keys.size(), "adding a node moves under 30% of keys (moved " + moved + ")");
        check(onlyToNewNode, "keys only move to the new node");

        boolean distinct = true;
        for (String k : keys.subList(0, 200)) {
            distinct &= ring.getNodes(k, 3).stream().distinct().count() == 3;
        }
        check(distinct, "replica nodes are distinct");

        ring.removeNode("n5");
        boolean restored = keys.stream().allMatch(k -> ring.getNode(k).equals(before.get(k)));
        check(restored, "removing the node restores the old placement");

        boolean threw = false;
        try {
            new HashRing(8).getNode("x");
        } catch (IllegalStateException e) {
            threw = true;
        }
        check(threw, "empty ring throws");
    }

    private static void lruTests() {
        LruCache<String, Integer> cache = new LruCache<>(2);
        cache.put("a", 1);
        cache.put("b", 2);
        check(cache.get("a") == 1, "get returns stored value");
        cache.put("c", 3); // "b" is now least recently used
        check(!cache.containsKey("b"), "least recently used entry is evicted");
        check(cache.containsKey("a") && cache.containsKey("c"), "recent entries survive");
        check(cache.size() == 2, "size never exceeds capacity");
        check(cache.get("zzz") == null, "miss returns null");
        check(Math.abs(cache.hitRate() - 0.5) < 1e-9, "hit rate counts hits and misses");

        boolean threw = false;
        try {
            new LruCache<String, String>(0);
        } catch (IllegalArgumentException e) {
            threw = true;
        }
        check(threw, "zero capacity is rejected");
    }

    public static void main(String[] args) {
        ringTests();
        lruTests();
        System.out.println((run - failed) + "/" + run + " Java checks passed");
        if (failed > 0) {
            System.exit(1);
        }
    }
}
