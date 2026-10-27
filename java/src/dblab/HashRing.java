package dblab;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Consistent hash ring with virtual nodes.
 *
 * <p>A key belongs to the first node clockwise from the key's hash. When a node joins or
 * leaves, only the keys in its arc move, roughly {@code 1/n} of them, instead of nearly
 * all of them as with {@code hash(key) % n}.
 *
 * <p>Not thread-safe: wrap calls in a lock or use a copy-on-write swap for concurrent use.
 */
public final class HashRing {
    private final TreeMap<Long, String> ring = new TreeMap<>();
    private final Set<String> nodes = new TreeSet<>();
    private final int vnodes;

    public HashRing(int vnodes) {
        if (vnodes < 1) {
            throw new IllegalArgumentException("vnodes must be >= 1");
        }
        this.vnodes = vnodes;
    }

    public void addNode(String node) {
        if (!nodes.add(node)) {
            return;
        }
        for (int i = 0; i < vnodes; i++) {
            ring.put(hash(node + "#" + i), node);
        }
    }

    public void removeNode(String node) {
        if (!nodes.remove(node)) {
            throw new IllegalArgumentException("unknown node: " + node);
        }
        ring.values().removeIf(node::equals);
    }

    public Set<String> nodes() {
        return java.util.Collections.unmodifiableSet(nodes);
    }

    public String getNode(String key) {
        return getNodes(key, 1).get(0);
    }

    /** Up to {@code count} distinct nodes, walking clockwise from the key's position. */
    public List<String> getNodes(String key, int count) {
        if (ring.isEmpty()) {
            throw new IllegalStateException("the ring has no nodes");
        }
        int wanted = Math.min(count, nodes.size());
        List<String> found = new ArrayList<>(wanted);
        long h = hash(key);
        for (Map<Long, String> part : List.of(ring.tailMap(h, true), ring.headMap(h, false))) {
            for (String node : part.values()) {
                if (!found.contains(node)) {
                    found.add(node);
                    if (found.size() == wanted) {
                        return found;
                    }
                }
            }
        }
        return found;
    }

    static long hash(String s) {
        try {
            byte[] digest = MessageDigest.getInstance("MD5").digest(s.getBytes(StandardCharsets.UTF_8));
            long h = 0;
            for (int i = 0; i < 8; i++) {
                h = (h << 8) | (digest[i] & 0xffL);
            }
            return h;
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e); // MD5 is required by the JDK spec
        }
    }
}
