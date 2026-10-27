package dblab;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Fixed-capacity least-recently-used cache with hit/miss statistics.
 *
 * <p>A {@link LinkedHashMap} in access order keeps entries sorted from least to most recently
 * used, so {@code get} and {@code put} are both O(1) and eviction removes the eldest entry.
 * Not thread-safe.
 */
public final class LruCache<K, V> {
    private final int capacity;
    private final LinkedHashMap<K, V> map;
    private long hits;
    private long misses;

    public LruCache(int capacity) {
        if (capacity <= 0) {
            throw new IllegalArgumentException("capacity must be positive");
        }
        this.capacity = capacity;
        this.map = new LinkedHashMap<K, V>(16, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
                return size() > LruCache.this.capacity;
            }
        };
    }

    /** Returns the value or {@code null}; a hit marks the entry as most recently used. */
    public V get(K key) {
        V value = map.get(key);
        if (value == null) {
            misses++;
        } else {
            hits++;
        }
        return value;
    }

    public void put(K key, V value) {
        map.put(key, value);
    }

    public boolean containsKey(K key) {
        return map.containsKey(key); // does not change recency
    }

    public int size() {
        return map.size();
    }

    public double hitRate() {
        long total = hits + misses;
        return total == 0 ? 0.0 : (double) hits / total;
    }
}
