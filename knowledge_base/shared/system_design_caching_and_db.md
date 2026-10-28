# System Design: Caching Strategies, Database Indexing, and Scalability

## Caching Topologies
Caching improves read latency and shields underlying persistent databases from high traffic volumes:
1. **Cache-Aside (Lazy Loading):** The application first queries the cache (e.g. Redis). If a cache miss occurs, the application queries the database, writes the result to the cache, and returns the response. This pattern is resilient to cache node failures.
2. **Write-Through:** The application writes data to the cache, and the cache synchronously writes to the database before acknowledging the write. Guarantees data consistency between cache and database at the expense of higher write latency.
3. **Write-Behind (Write-Back):** The application writes data directly to the cache, which asynchronously flushes batched updates to the database. Highly effective for write-heavy workloads, but risks data loss if the cache node crashes before flushing.

## Cache Eviction Policies
When cache memory reaches its threshold, eviction policies dictate which keys are purged:
- **LRU (Least Recently Used):** Evicts items that have not been read or written for the longest duration.
- **LFU (Least Frequently Used):** Evicts items with the lowest access count.
- **TTL (Time to Live):** Keys automatically expire after a predefined duration, preventing stale data retention.

## Database Indexing Fundamentals
Relational databases (such as PostgreSQL and SQLite) utilize B-Tree indexes by default:
- **B-Tree Indexes:** Balanced tree structures providing $O(\log N)$ search, insertion, and deletion complexity. Ideal for equality checks and range queries (`BETWEEN`, `<`, `>`).
- **Composite Indexes:** Indexes encompassing multiple columns. The order of columns in a composite index matters strictly according to the "leftmost prefix" rule: an index on `(tenant_id, status, created_at)` can accelerate queries on `tenant_id` or `(tenant_id, status)`, but not on `created_at` alone.
- **Index Overhead:** While indexes speed up reads, each additional index incurs write overhead (`INSERT`, `UPDATE`, `DELETE`) and storage consumption.

## Horizontal vs Vertical Scaling
- **Vertical Scaling:** Increasing CPU, RAM, and disk IOPS on a single machine. Simpler architecture but bounded by hardware limits and represents a single point of failure.
- **Horizontal Scaling:** Distributing requests across multiple stateless server nodes behind a load balancer, paired with database read replicas or sharding.

