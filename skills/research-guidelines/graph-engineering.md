---
name: graph-engineering
description: "Practical graph-engineering research brief: graph data models, an algorithms cheat-sheet for agent use, knowledge graphs for AI (entity resolution, embeddings, hybrid vector+graph retrieval, memory layers), query languages, tooling, pitfalls, and a when-to-reach-for-graphs decision checklist."
domain: data-engineering
mandatory: false
priority: 80
version: 1.0
sources:
  - "Cormen et al., Introduction to Algorithms (CLRS), 3rd ed. — BFS/DFS/Dijkstra/Bellman-Ford/Topological sort complexity bounds"
  - "Brandes, 'A Faster Algorithm for Betweenness Centrality', J. Math. Sociology 25(2), 2001"
  - "Grover & Leskovec, 'node2vec: Scalable Feature Learning for Networks', KDD 2016"
  - "Bordes et al., 'Translating Embeddings for Modeling Multi-relational Data' (TransE), NeurIPS 2013"
  - "Traag, Waltman & van Eck, 'From Louvain to Leiden', Scientific Reports 9, 2019"
  - "Blondel et al., 'Fast unfolding of communities in large networks', JSTAT 2008"
  - "Edge et al., 'From Local to Global: A Graph RAG Approach to Query-Focused Summarization', 2024"
  - "W3C RDF 1.1 Concepts / SPARQL 1.1 Query specs; Neo4j Cypher & GDS docs; Apache TinkerPop/Gremlin docs"
---

# Graph Engineering — Research Brief for Agent Use

Load this before designing or implementing anything graph-shaped: traversal queries,
knowledge graphs, memory layers, recommendation/relatedness features, or pathfinding.
Goal: pick the right model, algorithm, store, and query language the first time.

## 1. Fundamentals: graph data models

**Property graph (LPG).** Nodes and edges carry arbitrary key-value properties; edges
have a type/label; multiple typed edges between the same nodes are allowed. No schema
required. This is what Neo4j, Memgraph, ArangoDB, Kuzu, and most "graph databases" use.
Best for operational traversal workloads (shortest path, k-hop expansion, pattern match)
where query performance matters more than standards compliance.

**RDF / triple store.** Every fact is a `subject predicate object` triple; nodes and
predicates are global URIs; data is merged across sources by URI identity. Backed by
ontologies (RDFS/OWL) enabling inference (e.g., `parentOf` implies `ancestorOf`).
Queried with SPARQL. Best for open-world data integration, Linked Open Data, and any
use case needing reasoning/interop. Cost: verbose, slower for hot-path traversal.

**Knowledge graph (KG).** An application-layer concept, not a storage format: ontology
(schema) + instance data + usually a graph store plus, in AI stacks, an embedding index
and retrieval layer on top. A KG can live in an LPG, an RDF store, or even SQL with
recursive CTEs.

**Mapping between models.** Any RDF graph can be lossily mapped to an LPG (node per
subject/object, edge per predicate; literals become properties) and back (LPG -> RDF via
R2RML-style mapping, URIs generated from node IDs). If you may need inference or
cross-org data merging later, prefer RDF; otherwise prefer LPG — don't build a semantic
layer you don't have a concrete requirement for.

**Representations (when implementing yourself).**
- Adjacency list: `node -> list/set of (neighbor, edge_payload)`. Default choice;
  O(V+E) space, cheap traversal. Use this for agent-local graph code.
- Adjacency matrix: O(V^2) space, O(1) edge lookup, natural for linear algebra /
  PageRank via matrix ops. Only for small dense graphs.
- Edge list: `(u, v, payload)` rows. Best for storage, import/export, and SQL tables.
- Incidence matrix: edges as columns; niche (hypergraph-ish), rarely needed.

**When graphs beat relational models.** Variable-depth traversal ("friends of friends",
"all paths under 3 hops", "shortest route") is the decisive case: in SQL each extra hop
is another self-join, and beyond ~2-3 hops the queries become unreadable and slow
(recursive CTEs help but can't prune by path quality). Graphs also win on heterogeneous
or evolving schemas (add edge types without migrations) and on relationship-centric
analytics (centrality, communities, link prediction). **When relational wins:** flat
facts with 1-2 level joins, heavy group-by aggregation/BI, strict schema with strong
integrity constraints, high-volume OLTP on scalar data. If the query is "sum/group/join
over flat facts", that is SQL, not a graph problem.

## 2. Algorithms cheat-sheet

**Shortest path.**
- BFS — unweighted, O(V+E). First found path is the shortest in hops.
- Dijkstra — non-negative weights, O((V+E) log V) with binary heap. Default for weighted.
- A* — Dijkstra + admissible heuristic (e.g., straight-line distance); optimal only if
  the heuristic is admissible and consistent. Use for geospatial/latency-style search.
- 0-1 BFS (deque) — O(V+E) when weights are only 0/1.
- Bellman-Ford — handles negative weights, O(VE); Floyd-Warshall — all-pairs, O(V^3),
  fine only for small graphs.

**Centrality.** Degree (cheap local signal); betweenness (Brandes: O(VE) unweighted —
expensive, approximate by sampling on large graphs); closeness; eigenvector and
PageRank (recursive importance; PageRank via power iteration; good "importance" proxy
for ranking entities in a memory layer). Prefer PageRank over raw degree when edges are
meaningful relationships; prefer degree when you just need a fast filter.

**Community detection.** Louvain (modularity optimization, fast, de facto default,
non-overlapping, slightly non-deterministic); Leiden (fixes Louvain's disconnected-
community flaw, preferred); label propagation (O(E), very fast, stochastic — use for
coarse segmentation); connected components (exact, deterministic, for gross grouping).
For overlapping communities use COPRA/AGM-style methods — rarer, only if needed.

**Connectivity.** Union-find (DSU) with path compression + union by rank ≈ O(α(V))
amortized — the right tool for offline "are A and B connected" and Kruskal's MST.
Tarjan's SCC — O(V+E) for strongly connected components and articulation
points/bridges via DFS low-link values. Directed reachability: BFS/DFS from source.

**Topological sort & cycles.** Kahn's algorithm (indegree-based, O(V+E)) or DFS
finish-time ordering; only valid on DAGs. If Kahn outputs fewer than V nodes, a cycle
exists — this is also the cheapest directed cycle check. Undirected cycle detection:
union-find or DFS. Use for dependency resolution, scheduling, causal chains.

**Agent guidance.** For one-off exploration, NetworkX covers all of the above out of the
box (nx.shortest_path, nx.pagerank, nx.community.louvain_communities, nx.topological_sort).
Hand-implement only when the data is too big for NetworkX (> ~100k edges) or when you
need a custom pruning policy inside the traversal.

## 3. Knowledge graphs for AI

**Entity resolution.** Before a KG is useful, dedupe: normalize strings (case, unicode,
whitespace), block on cheap keys (prefix, token, year) to avoid O(n^2) comparisons,
then score candidate pairs with exact/fuzzy (Jaro-Winkler, token Jaccard) and embedding
cosine; merge on score threshold + review. Re-resolve periodically — entities drift.

**Embedding-based retrieval.** Two families:
- Structural embeddings: node2vec (biased random walks + skip-gram) captures
  neighborhood topology; TransE models relations as vector translations
  (h + r ≈ t) for link prediction. These encode *structure*, not semantics — two
  similar-meaning nodes far apart in the graph get unrelated vectors.
- GNNs (GCN/GAT): message passing over neighborhoods for node classification/link
  prediction; need labeled data and are heavier to train. Don't default to GNNs;
  node2vec/TransE are enough for most retrieval tasks.
- Text embeddings (sentence/document) cover semantics; graph embeddings cover
  structure. You usually want both — keep them in separate indexes, don't sum them
  blindly.

**Hybrid vector + graph retrieval (GraphRAG-style).** Pipeline that works well:
(1) embed query, retrieve top-k nodes by vector cosine; (2) expand each hit via graph
neighborhood — k-hop expansion, personalized PageRank (random walk biased toward the
query nodes), or precomputed community summaries; (3) merge, dedupe, rerank by a mix
of vector score, graph centrality, and recency; (4) feed the top-N subgraph or its
textual serialization to the LLM. Expansion depth 1-2 is usually the sweet spot —
depth 3+ explodes (see pitfalls).

**Memory layer (e.g., Ndlovu).** A graph store fits a persistent agent memory well:
- Nodes = entities and chunks (people, projects, docs, decisions, conversation chunks).
- Typed, timestamped edges = `mentions`, `depends_on`, `supersedes`, `follows`,
  `caused`. Time-stamped edges give you cheap "state of the world at time T" queries.
- Traversal answers "what relates to X and how" (associative recall); vector index
  answers "what is semantically similar to this"; PageRank on the whole graph gives an
  importance signal for eviction/pruning — evict low-importance, low-recency, and
  superseded nodes first. The graph is the index over memory, not a second copy of it:
  chunks live in the vector store, the graph points at them.

## 4. Query languages

- **Cypher** (Neo4j, Memgraph, Kuzu, Apache AGE): declarative pattern matching —
  `MATCH (a:Person)-[:KNOWS*1..3]->(b) RETURN DISTINCT b`; built-in `shortestPath`;
  variable-length patterns are the killer feature. Most approachable; default for LPG.
- **Gremlin** (Apache TinkerPop; JanusGraph, Neptune, Cosmos DB): imperative
  traversal DSL (`g.V().hasLabel('Person').repeat(out('KNOWS')).times(3)`). More
  verbose but works across many engines; pick only if portability matters.
- **SPARQL** (RDF): triple patterns, federated endpoints, inference via OWL/RDFS
  entailment. Use for open-data/W3C interop; not for hot traversal paths.
- **SQL recursive CTEs** — the no-new-infra option (Postgres, SQLite ≥3.8.3, DuckDB):
  ```sql
  WITH RECURSIVE reach(src, dst, depth) AS (
    SELECT u, v, 1 FROM edges WHERE u = 'start'
    UNION
    SELECT r.src, e.v, r.depth + 1 FROM reach r JOIN edges e ON r.dst = e.u
    WHERE r.depth < 5
  ) SELECT DISTINCT dst FROM reach;
  ```
  Works well ≤ ~5-10 hops at low fan-out. Gaps: no cycle protection (track visited
  paths in the recursive set or rely on the depth cap), no weighted shortest path
  (hand-roll Dijkstra), performance degrades with depth × fan-out.

**Choice rule.** Property graph + traversal-heavy → Cypher. RDF/integration → SPARQL.
Zero infra, small-medium graph → recursive CTE. Multi-engine portability → Gremlin.

## 5. Tooling

- **Neo4j** — most mature; Cypher, APOC, Graph Data Science library (PageRank,
  Louvain, node2vec out of the box). Some GDS/enterprise features licensed; Docker
  image makes it easy to try.
- **Memgraph** — in-memory, Cypher-compatible, fast for streaming workloads, open source.
- **ArangoDB** — multi-model (document + graph + key-value), AQL with native traversal;
  good when you also need document storage.
- **Kuzu** — embedded columnar property graph with Cypher, zero-server, local-first —
  strong fit for an agent memory layer on disk.
- **Apache AGE** — Cypher inside PostgreSQL: graph and relational data in one engine.
- **Local-first / lightest:** SQLite edge table + recursive CTE, with sqlite-vec for
  the vector index beside it — one file, no services, remarkably capable for graphs up
  to ~10^5-10^6 edges. DuckDB same idea with columnar speed.
- **In-memory analysis:** NetworkX (pure Python, fine < ~100k edges), igraph (C core,
  much faster, same breadth). Use these to prototype before committing to a store.

## 6. Common pitfalls and mitigations

- **N+1 traversal.** Fetching each node's properties/neighbors with a separate query
  per node turns O(V+E) work into O(V) round-trips. Mitigate: single Cypher/SPARQL
  query with pattern matching; batch-fetch neighbors; never loop queries inside a
  traversal loop.
- **Supernodes.** A node with extreme degree (a shared "Unknown"/"misc" entity, a hub
  user) makes every hop through it explode. Mitigate: relabel/split generic nodes,
  exclude them from traversals, cap per-hop expansion (`LIMIT` per step), keep hub
  edges in a separate index, or filter by edge type before traversing.
- **Fan-out explosion.** Traversals grow as fan-out^depth; depth 4-5 at fan-out 10 is
  10^5 nodes. Mitigate: hard k-hop caps, prune by score/type/recency at each step,
  bidirectional search (BFS from both endpoints, meet in the middle) for reachability
  and shortest paths, and a visited-set to kill cycles and diamond paths.
- **Index misses.** Lookups by unindexed property or node ID cause full scans per hop.
  Index node labels/IDs and edge types upfront (`CREATE INDEX ... FOR (n:Person) ON
  (n.name)`); check plans with PROFILE/EXPLAIN; in SQL, make sure the join column
  (edge endpoints) is indexed or every hop scans the whole edge table.
- **Global algorithms on huge graphs.** Betweenness, exact PageRank, Girvan-Newman are
  O(V·E)-ish and won't finish on large graphs. Mitigate: sample for approximation,
  cap k-hops, or use the store's parallel/distributed implementations (GDS, Spark).
- **Cycle traps.** Unbounded traversals on cyclic graphs loop forever. Always carry a
  visited set or depth cap; in recursive CTEs, track the path so you can exclude
  already-seen nodes.
- **Path enumeration vs existence.** Asking for *all* paths vs *a/shortest* path is
  the difference between tractable and intractable. Always prefer existence/
  shortest/`DISTINCT`-collapsed answers unless the task truly needs full enumeration.
- **Model mismatch.** Mixing RDF-style URIs into an LPG without a mapping layer, or
  storing timestamps as node properties instead of edge properties (breaks time-travel
  queries). Decide the model first (Section 1), then migrate data.
- **Memory blowup.** Adjacency matrices on large graphs; storing full paths instead of
  predecessors; keeping the whole graph in RAM when a store can page. Use adjacency
  lists, predecessor arrays, and on-disk stores.

## 7. When to reach for graphs — decision checklist

Ask in order; if the first three are mostly "yes", a graph approach is justified:

1. Is the core query multi-hop: path finding, k-hop neighborhood, reachability,
   "what relates to X and how"?
2. Is the data naturally entity-relationship shaped, with relationship depth that
   varies and is not known in advance (friends-of-friends, dependency chains,
   provenance)?
3. Do you need relationship-centric analytics: centrality, communities, link
   prediction, importance ranking over connections?
4. Is the schema heterogeneous or evolving (new node/edge types appear often)?
5. Would SQL need > 2 self-joins or a hand-rolled recursive traversal to answer it?

Then pick the weight class:
- Small-medium, local-first, single process → SQLite/edge table + recursive CTE
  (+ sqlite-vec), or Kuzu if you want Cypher; NetworkX/igraph for one-off analysis.
- Operational multi-hop service → LPG store (Neo4j/Memgraph/ArangoDB).
- Semantic web / cross-org merging / inference → RDF + SPARQL.
- AI retrieval over the graph → text embeddings + structural embeddings + hybrid
  expansion (Section 3), graph store as the index.

**Do NOT reach for graphs when:** the workload is flat aggregation/BI over tabular
facts, joins are 1-2 levels, schema is rigid and transactional integrity is the main
concern (SQL wins), or the "graph" is really just a lookup table with one edge type
(a hash map / relational index is faster and simpler).
