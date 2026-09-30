# Vector Database Research

## Contents

1. [When to Use a Vector Database](#1-when-to-use-a-vector-database)
2. [Case Study: A 100-Page User Guide](#2-case-study-a-100-page-user-guide)
3. [How a Vector Database Works](#3-how-a-vector-database-works)
4. [MCP Tools for Inserting and Retrieving Data](#4-mcp-tools-for-inserting-and-retrieving-data)
5. [Where the Embedding Model Runs](#5-where-the-embedding-model-runs)
6. [HNSW Index Explained](#6-hnsw-index-explained)
7. [Vector Database Comparison](#7-vector-database-comparison)
8. [Language Support: Python, TypeScript and C#](#8-language-support-python-typescript-and-c)
9. [Vector Databases on Amazon AWS](#9-vector-databases-on-amazon-aws)
10. [Tokens vs Context Window](#10-tokens-vs-context-window)

---

## 1. When to Use a Vector Database

Use a vector database when you need to search by **meaning (semantic similarity)** instead of exact values.

### 1.1 Good fit

- **Fuzzy or natural-language queries.** The user describes what they want and doesn't know the exact keyword.
- **Unstructured data.** Documents, emails, support tickets, code, images or audio that you turn into embeddings.
- **RAG (Retrieval-Augmented Generation).** An LLM needs relevant context pulled from a large corpus that won't fit in its context window.
- **Recommendations or "more like this".** Finding similar products, articles or users.
- **Scale.** Enough vectors (roughly hundreds of thousands or more) that a brute-force similarity scan in memory gets slow.

### 1.2 Not a good fit

- **Exact lookups** such as `get_user_by_email` or finding an order by ID. A dict or SQL index is simpler, faster and exact.
- **Small datasets.** With 10 members, or even a few thousand rows, embeddings plus numpy cosine similarity in memory is enough.
- **Structured filtering or aggregation** such as "users created last month" or "total sales by region". Use SQL for these.

The current member MCP server is a clear case where a vector DB would be over-engineering.

### 1.3 Example: a support knowledge-base assistant

A company has 50,000 help articles, past tickets and product manuals. A user asks:

> "My invoice shows a charge twice after I upgraded my plan"

A keyword search might miss the right article, titled "Duplicate billing during subscription changes", because the words don't match.

With a vector DB:

1. **Ingest (offline):** split each document into chunks, turn each chunk into an embedding vector with an embedding model, and store the vector with metadata (source, product, date) in the vector DB.
2. **Query:** turn the user's question into an embedding, then ask the DB for the top 5 nearest chunks, optionally filtered by metadata such as `product = "billing"`.
3. **Generate:** pass those chunks to the LLM as context. It answers from the actual docs and cites them.

### 1.4 How it could fit this project

Add an MCP tool such as `search_knowledge_base(query)` that performs step 2. The console agent's LLM would then decide when to call it, just as it already decides between `get_user_by_name` and `get_all_users`.

If you already run Postgres, start with **pgvector**. Move to a dedicated vector DB such as Qdrant or Pinecone only when scale or performance requires it.

---

## 2. Case Study: A 100-Page User Guide

**Question:** a user guide of about 100 pages must answer user help questions. Should it use a vector DB, or pass the whole guide to the LLM?

**Answer:** for a 100-page guide you usually don't need a vector DB. Start by passing the whole guide to the LLM, and switch to a vector DB only if a specific limit forces it.

### 2.1 Why the whole guide works

- **It fits.** 100 pages is roughly 50k-75k tokens (about 500 words per page, about 1.3 tokens per word). `openai/gpt-oss-120b` has a context window of about 131k tokens, so it fits with room to spare.
- **Answers tend to be better.** The model sees everything, including cross-references like "see Section 4.2" and steps spread across chapters. Retrieval can miss the right chunk, and then the answer is wrong or incomplete.
- **There's no pipeline to maintain.** You skip chunking, embeddings, index updates and relevance tuning. When the guide changes, you just reload the file.
- **Prompt caching cuts cost and latency.** Put the guide at the start of the system prompt so every request shares the same prefix. Many providers then charge a fraction of the price for the cached part. Check whether your OpenRouter provider supports caching for that model.

### 2.2 When to switch to a vector DB (RAG)

| Situation | Full guide | Vector DB |
|---|---|---|
| Size of the docs | Up to a few hundred pages | Thousands of pages or many documents |
| Query volume | Low to moderate | High, where about 60k tokens per query adds up |
| Latency | A few seconds is fine | Fast responses needed |
| Model | Large context window | Small or local model with a small context |
| Growth | The guide stays about the same | New manuals keep getting added |

Other signs you've outgrown the full-guide approach:

- Answers get worse because the model loses details buried in the middle of a long context.
- You need to cite exact page or section sources at scale.
- You want to restrict answers by metadata, such as product version or user role.

### 2.3 Suggested path

1. **Now:** load the guide as text or markdown at startup and put it in the system prompt. Add an instruction like "Answer only from the guide; say so if the answer isn't there."
2. **Measure:** track tokens per request, cost and answer quality on 20-30 real questions.
3. **Only if needed:** chunk the guide and store it in pgvector or Chroma, then expose it as an MCP tool like `search_user_guide(query)` for the agent to call.

### 2.4 Middle option: section lookup

If the guide has clear sections, expose a `get_section(title)` MCP tool with a table of contents in the prompt. The LLM picks the section and you send only that part. You get most of the savings without embeddings.

---

## 3. How a Vector Database Works

### 3.1 Embeddings: text turned into numbers

An **embedding model** converts text into a fixed-length list of numbers (a vector), for example 384 or 1536 numbers. Texts with similar meaning get vectors that point in similar directions.

```
"How do I reset my password?"        -> [0.12, -0.44, 0.91, ...]
"Steps to recover login credentials" -> [0.10, -0.40, 0.88, ...]   <- close
"Invoice payment due dates"          -> [-0.71, 0.33, 0.05, ...]   <- far
```

### 3.2 Storage

Each record in the vector DB holds four things:

| Field | Example |
|---|---|
| id | `guide-p12-c3` |
| vector | `[0.10, -0.40, 0.88, ...]` |
| original text | "To reset your password, open Settings..." |
| metadata | `{"page": 12, "section": "Account"}` |

### 3.3 Search: nearest neighbours

1. The question is embedded with the **same** embedding model.
2. The DB finds the stored vectors closest to it, usually by **cosine similarity**.
3. It returns the top-k matches with their text and metadata.

Comparing against every vector would be slow at scale. Vector DBs instead use an **ANN (Approximate Nearest Neighbour) index**, most commonly **HNSW** (see [section 6](#6-hnsw-index-explained)). That keeps search in milliseconds even with millions of vectors.

### 3.4 Overall flow

```
INGEST (once, or whenever the guide changes)
  user_guide.md -> split into chunks -> embed each chunk -> store in vector DB

QUERY (every question)
  User -> Agent -> LLM decides to call tool
                     |
                     v
          MCP tool search_user_guide(query)
                     -> embed query -> vector DB top-5 chunks
                     <- return chunks as text
                     |
                     v
          LLM writes the answer from those chunks -> Console
```

The MCP server owns the vector DB. The LLM never touches the DB directly; it only calls the tools.

---

## 4. MCP Tools for Inserting and Retrieving Data

### 4.1 Example tools with Chroma

This uses **Chroma** (`uv add chromadb`). It runs embedded in the Python process and includes a default embedding model, so it needs no extra service or API key.

```python
# src/member_mcp/guide_tools.py
import chromadb
from fastmcp import FastMCP

mcp = FastMCP("user-guide")

client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(
    "user_guide", metadata={"hnsw:space": "cosine"}
)


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    step = size - overlap
    return [text[i : i + size] for i in range(0, len(text), step)]


@mcp.tool
def add_document(doc_id: str, text: str, section: str = "") -> str:
    """Split a document into chunks and store them in the vector DB."""
    chunks = chunk_text(text)
    collection.upsert(
        ids=[f"{doc_id}-{i}" for i in range(len(chunks))],
        documents=chunks,  # Chroma embeds these automatically
        metadatas=[{"doc_id": doc_id, "section": section, "chunk": i} for i in range(len(chunks))],
    )
    return f"Stored {len(chunks)} chunks for {doc_id}"


@mcp.tool
def search_user_guide(query: str, top_k: int = 5) -> list[dict]:
    """Find the user guide passages most relevant to the question."""
    result = collection.query(query_texts=[query], n_results=top_k)
    return [
        {"text": doc, "section": meta["section"], "distance": round(dist, 3)}
        for doc, meta, dist in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]
```

### 4.2 What each tool does

- **Insert:** `upsert` sends each chunk through the embedding model and stores the vector, text and metadata. Upserting with the same id overwrites the old chunk, so re-ingesting an updated guide is safe.
- **Retrieve:** `query` embeds the question, runs the HNSW nearest-neighbour search and returns the closest chunks. A smaller distance means more relevant.

### 4.3 Loading a large guide

Don't have the LLM push 100 pages through `add_document`. That would mean sending the whole guide as tool-call arguments, which is slow and costly. Use a one-off script that calls the same code directly:

```python
# scripts/ingest_guide.py
from pathlib import Path
from member_mcp.guide_tools import collection, chunk_text

text = Path("docs/user_guide.md").read_text(encoding="utf-8")
chunks = chunk_text(text)
collection.upsert(
    ids=[f"guide-{i}" for i in range(len(chunks))],
    documents=chunks,
    metadatas=[{"section": "", "chunk": i} for i in range(len(chunks))],
)
print(f"Ingested {len(chunks)} chunks")
```

Keep the `add_document` tool for small additions made during a conversation, like "remember this FAQ answer". Use `search_user_guide` for every question.

### 4.4 At query time

1. The user asks: "How do I change my notification settings?"
2. The LLM sees the `search_user_guide` tool description and calls it with that query.
3. The MCP server returns the 5 closest chunks, for example the passages from the Notifications chapter.
4. The agent sends those chunks back to the LLM, which writes the answer and can cite the section.

### 4.5 Practical tips

- **Chunking matters most.** Split on headings or paragraphs rather than fixed character counts when you can, and keep some overlap so steps aren't cut in half.
- **Use the same embedding model for ingest and query.** If you change the model, re-ingest everything.
- **Hybrid search** (vector plus keyword/BM25) helps with exact terms like error codes and product names.
- **Swapping databases:** pgvector, Qdrant and Pinecone follow the same pattern (upsert vectors with metadata, query top-k). Only the client code changes.

---

## 5. Where the Embedding Model Runs

The embedding model runs **inside the MCP server process**. In the Chroma example it is hidden inside the `chromadb` library.

### 5.1 Chroma's default embedding function

When you call:

```python
collection.upsert(documents=chunks, ...)        # insert
collection.query(query_texts=[query], ...)      # search
```

Chroma embeds the text using its **default embedding function**:

- **Model:** `all-MiniLM-L6-v2`, a small open-source model that produces 384-number vectors.
- **Runtime:** ONNX Runtime on your CPU, locally, with no API key.
- **Download:** fetched once on first use (about 80 MB) and cached under `~/.cache/chroma/onnx_models/`.
- **Process:** the same Python process as the FastMCP server, because `PersistentClient` runs Chroma embedded.

```
MCP server process (FastMCP)
 +- search_user_guide(query)
      +- chromadb
           +- embedding model (all-MiniLM-L6-v2, ONNX, CPU)  <- here
           +- HNSW index + storage (./chroma_data)
```

### 5.2 Embedding model vs LLM

These are two separate models with different jobs:

| | Embedding model | LLM (`openai/gpt-oss-120b`) |
|---|---|---|
| Job | Text to vector | Understand the question, pick tools, write the answer |
| Where it runs | Locally, in the MCP server | Remotely, via OpenRouter |
| Size | Small (about 80 MB) | Very large |
| Called by | The MCP tool, on every insert and search | The agent, on every turn |

The LLM never sees vectors. It only sees the text chunks the tool returns.

### 5.3 Choosing the embedding model explicitly

It is better to set the model explicitly so it's visible and fixed.

#### Option A: pass an embedding function to Chroma

```python
from chromadb.utils import embedding_functions

ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = client.get_or_create_collection("user_guide", embedding_function=ef)
```

Chroma still calls the model automatically on `upsert` and `query`. This needs `uv add sentence-transformers`, which also pulls in PyTorch, a much larger install than the default ONNX setup.

#### Option B: embed the text yourself and store raw vectors

This is how it works with most other vector DBs, such as pgvector and Qdrant, which store and search vectors but don't create them.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

# insert
vectors = model.encode(chunks).tolist()
collection.upsert(ids=ids, embeddings=vectors, documents=chunks, metadatas=metas)

# search
query_vector = model.encode(query).tolist()
result = collection.query(query_embeddings=[query_vector], n_results=5)
```

### 5.4 Hosted embedding models

Instead of a local model, you can call an embedding API, such as OpenAI `text-embedding-3-small`, Voyage or Cohere. The tool code has the same shape: send the text, get a vector back, store or query it. It only adds a network call and a cost per request.

Whichever model you pick, use the **same model for insert and search**. Vectors from different models aren't comparable, so if you change the model you have to re-ingest the whole guide.

---

## 6. HNSW Index Explained

**HNSW (Hierarchical Navigable Small World)** is the index most vector databases use to find the nearest vectors quickly without comparing the query against every stored vector.

### 6.1 The problem it solves

Brute-force search compares the query vector with every stored vector:

- 1,000 chunks: instant.
- 10 million chunks: 10 million distance calculations per query, which is too slow.

HNSW cuts this to a few hundred comparisons. The trade-off is that results are **approximate**: it finds the true nearest neighbours most of the time (often 95-99%+), not with a guarantee.

### 6.2 The idea: a graph with layers

#### Navigable Small World graph

Each vector is a node connected to a handful of its nearest neighbours. To search, you start at some node and repeatedly move to whichever neighbour is closer to the query. You stop when no neighbour is closer. This is called greedy search.

#### Hierarchical layers

Greedy search on a single huge graph takes many small steps, so HNSW stacks several layers:

```
Layer 2:  A ----------------------- F            (few nodes, long jumps)
          |                         |
Layer 1:  A ------ C ------ E ----- F ---- H     (more nodes)
          |        |        |       |      |
Layer 0:  A - B -  C - D -  E - ... F - G - H - I - J ...   (all nodes, short links)
```

- Every vector is in layer 0.
- Each higher layer holds a random, smaller subset of them.
- The top layers act like **motorways** and layer 0 like **local streets**.

### 6.3 How a search works

1. Start at the entry point in the top layer.
2. Move greedily to the neighbour closest to the query until you can't get any closer.
3. Drop down one layer from that node and repeat.
4. In layer 0, keep a shortlist of the best candidates and return the top-k.

Each layer narrows the search area, so the cost grows roughly **logarithmically** with the number of vectors.

### 6.4 How inserting works

When you `upsert` a chunk:

1. A random top layer is chosen for the new node. Most nodes only live in layer 0, and fewer and fewer go higher.
2. The index searches down to find the new node's nearest neighbours in each of its layers.
3. The node is linked to up to **M** of those neighbours in each layer.

### 6.5 Tuning parameters

| Parameter | Meaning | Higher value means |
|---|---|---|
| `M` | Links per node | Better recall, more memory |
| `ef_construction` | Candidate list size when building the index | Better graph quality, slower inserts |
| `ef_search` (`ef`) | Candidate list size when searching | Better recall, slower queries |

In Chroma you can set these on the collection:

```python
collection = client.get_or_create_collection(
    "user_guide",
    metadata={
        "hnsw:space": "cosine",
        "hnsw:M": 16,
        "hnsw:construction_ef": 100,
        "hnsw:search_ef": 50,
    },
)
```

This uses the long-standing `hnsw:*` metadata keys. Recent Chroma releases also accept a `configuration` argument for the same settings, so check the docs for the version you install.

### 6.6 Does it matter for a 100-page guide?

Not really. A 100-page guide gives a few hundred chunks, and brute force over those takes microseconds. HNSW only starts to matter at hundreds of thousands of vectors or more. The defaults are fine for this use case.

---

## 7. Vector Database Comparison

Capacities and performance below are **rough, practical ranges**; real numbers depend heavily on vector size, hardware, index settings and filters. Benchmark with your own data before committing.

### 7.1 Comparison table

| Database | Type | Open source (license) | Practical capacity | Performance | Best use cases |
|---|---|---|---|---|---|
| **Chroma** | Dedicated vector DB, embedded or server | Yes (Apache 2.0); managed Chroma Cloud also available | Up to low millions of vectors on one node | Fast at small to medium scale | Prototypes, local RAG, apps like this MCP server |
| **pgvector** | Postgres extension | Yes (PostgreSQL license) | Up to tens of millions, more with tuning or partitioning | Good; HNSW and IVFFlat indexes; slower than dedicated DBs at very large scale | Teams already on Postgres; combining SQL filters, joins and vectors |
| **Qdrant** | Dedicated vector DB (Rust) | Yes (Apache 2.0); managed cloud also available | Up to billions with sharding | Very fast; strong filtered search; quantization reduces memory | Production RAG, search with heavy metadata filtering |
| **Weaviate** | Dedicated vector DB (Go) | Yes (BSD-3); managed cloud also available | Up to billions with sharding | Fast; built-in hybrid search (vector plus BM25 keyword search) | Hybrid search, built-in embedding modules, multi-tenant SaaS |
| **Milvus** (managed version: **Zilliz Cloud**) | Distributed vector DB | Milvus yes (Apache 2.0); Zilliz Cloud is managed | Billions and up, built for massive scale | Very high throughput; many index types, GPU support | Large enterprise workloads, image and video search |
| **Pinecone** | Fully managed serverless service | No (proprietary SaaS) | Billions, scaling handled for you | Fast, low operations effort; costs grow with usage | Teams wanting zero infrastructure work |
| **FAISS** (Meta) | Library, not a database | Yes (MIT) | Billions, in memory or on GPU | Extremely fast raw search | Research, batch jobs, a custom engine; no persistence, API or metadata filtering built in |
| **LanceDB** | Embedded DB on files (Lance format) | Yes (Apache 2.0); managed cloud also available | Large; data lives on disk or object storage such as S3 | Good; low memory use | Local or serverless apps, multimodal data, data-lake setups |
| **Elasticsearch / OpenSearch** | Search engines with vector support | OpenSearch yes (Apache 2.0); Elasticsearch offers AGPL alongside Elastic License / SSPL | Billions, distributed | Good; best-in-class keyword search, vector search added on | Organizations already running Elasticsearch or OpenSearch; hybrid enterprise search |
| **Redis** (vector search) | In-memory data store | Mixed: Redis 8 offers AGPL alongside RSALv2 / SSPL | Limited by RAM | Very low latency | Real-time recommendations, semantic caching of LLM responses |
| **MongoDB Atlas Vector Search** | Document DB with vector search | Mostly managed / proprietary (Atlas) | Large, via sharding | Good | Apps already storing their data in MongoDB |
| **Cloud-provider services** (Azure AI Search, Vertex AI Vector Search, AWS OpenSearch / S3 Vectors) | Managed cloud services | No | Large | Good; integrated with their cloud | Teams committed to one cloud provider |
| **sqlite-vec** | SQLite extension | Yes (MIT / Apache 2.0) | Thousands to low millions | Fine at small scale | On-device, edge and desktop apps; tiny footprint |

### 7.2 How to choose

```
Already use Postgres?                 -> pgvector
Prototype or small app, local?        -> Chroma (or sqlite-vec / LanceDB)
Production, self-hosted, filtering?   -> Qdrant or Weaviate
Billions of vectors, big team?        -> Milvus / Zilliz
No infrastructure, pay per use?       -> Pinecone
Already use Elasticsearch/OpenSearch? -> their built-in vector search
Just need fast math, no DB?           -> FAISS
```

### 7.3 Rough scale guide

| Number of vectors | What works |
|---|---|
| Under 100K (a 100-page guide is a few hundred chunks) | Anything, including plain numpy. Pick whatever is simplest. |
| 100K to 10M | pgvector, Chroma, Qdrant, Weaviate, LanceDB |
| 10M to 1B | Qdrant, Weaviate, Milvus, Pinecone, Elasticsearch / OpenSearch |
| Over 1B | Milvus / Zilliz, Pinecone, Vespa, custom FAISS setups |

### 7.4 Recommendation for this project

- **Chroma** runs embedded with no extra service, so it's the easiest fit for the FastMCP server.
- **pgvector** makes sense if Postgres is later added for member data.
- **Qdrant** is the natural next step for a dedicated production vector DB. It runs with one `docker run` command and has a good Python client.

Licenses and managed offerings change often (Elasticsearch and Redis have both changed licenses recently). Check the current license before you commit, especially for commercial use.

---

## 8. Language Support: Python, TypeScript and C#

All the main vector DBs have official Python support. TypeScript support is almost as common. C# is the one that varies most.

### 8.1 Legend

- **Official:** maintained by the vendor or project.
- **Community:** third-party library.
- **Via driver:** you use the standard database driver for that language.

### 8.2 Language support table

| Database | Python | TypeScript / JavaScript | C# / .NET |
|---|---|---|---|
| **Chroma** | Official (`chromadb`) | Official (`chromadb` on npm) | Community (e.g. `ChromaDB.Client`); also a Semantic Kernel connector |
| **pgvector** | Official helper (`pgvector-python`) + psycopg / SQLAlchemy | Official helper (`pgvector-node`) + `pg` / Prisma / Drizzle | Official helper (`pgvector-dotnet`) + Npgsql / EF Core |
| **Qdrant** | Official (`qdrant-client`) | Official (`@qdrant/js-client-rest`) | Official (`Qdrant.Client`) |
| **Weaviate** | Official (`weaviate-client`) | Official (`weaviate-client` on npm) | Official C# client is recent (verify it's mature enough); community clients also exist |
| **Milvus / Zilliz** | Official (`pymilvus`) | Official (`@zilliz/milvus2-sdk-node`) | Official (`Milvus.Client`) |
| **Pinecone** | Official (`pinecone`) | Official (`@pinecone-database/pinecone`) | Official (`Pinecone.Client`) |
| **FAISS** | Official (Python bindings over C++) | Community only (e.g. `faiss-node`) | Community only |
| **LanceDB** | Official (`lancedb`) | Official (`@lancedb/lancedb`) | None official |
| **Elasticsearch** | Official (`elasticsearch`) | Official (`@elastic/elasticsearch`) | Official (`Elastic.Clients.Elasticsearch`) |
| **OpenSearch** | Official (`opensearch-py`) | Official (`@opensearch-project/opensearch`) | Official (`OpenSearch.Client`) |
| **Redis** | Official (`redis-py`, plus `redisvl` for vector search) | Official (`redis` / node-redis) | Official (`NRedisStack` on top of `StackExchange.Redis`) |
| **MongoDB Atlas** | Official (`pymongo`) | Official (`mongodb`) | Official (`MongoDB.Driver`) |
| **Azure AI Search** | Official (`azure-search-documents`) | Official (`@azure/search-documents`) | Official (`Azure.Search.Documents`), the strongest .NET option |
| **Vertex AI Vector Search** | Official (`google-cloud-aiplatform`) | Official (Node SDK) | Official (`Google.Cloud.AIPlatform.V1`) |
| **sqlite-vec** | Official (`sqlite-vec` on pip) | Official (`sqlite-vec` on npm) | Via driver: load the extension through `Microsoft.Data.Sqlite` |

### 8.3 Summary

- **Python:** all of them. Python is the default language for vector DB and RAG work.
- **TypeScript:** nearly all officially. FAISS is the exception, with community bindings only.
- **C# with official clients:** Qdrant, Milvus, Pinecone, pgvector (via Npgsql), Elasticsearch, OpenSearch, Redis, MongoDB, Azure AI Search and Vertex AI.
- **C# is weak or community-only for:** Chroma, LanceDB and FAISS. Weaviate's official C# client is recent.

### 8.4 Other ways to connect

#### REST / gRPC APIs

Qdrant, Weaviate, Milvus, Pinecone, Chroma (server mode) and Elasticsearch all expose HTTP APIs, so any language can call them without an SDK.

#### Framework connectors

These give one interface over many databases:

| Language | Frameworks |
|---|---|
| Python | LangChain, LlamaIndex |
| TypeScript | LangChain.js, LlamaIndex.TS |
| C# | Microsoft Semantic Kernel / `Microsoft.Extensions.VectorData`, with connectors for Qdrant, Azure AI Search, Redis, Pinecone, Weaviate, Postgres, MongoDB, SQLite and others |

### 8.5 If you need all three languages

**Qdrant** and **pgvector** are the safest choices. Both have official, well-maintained Python, TypeScript and C# support, and both can be self-hosted for free. Choose **Azure AI Search** if you're a .NET shop on Azure.

SDKs change often, so check each project's docs for current package names before you choose.

---

## 9. Vector Databases on Amazon AWS

AWS has several vector options. The main one is the vector engine in **Amazon OpenSearch Service**, and there is also a newer, cheaper storage option called **Amazon S3 Vectors**.

### 9.1 AWS vector services

| Service | What it is | Capacity / performance | Best for |
|---|---|---|---|
| **Amazon OpenSearch Service** (managed or **Serverless** vector engine) | Managed OpenSearch with k-NN vector search (HNSW, IVF), plus keyword and hybrid search | Billions of vectors; low-latency queries; Serverless scales automatically | General-purpose production RAG and semantic search, especially hybrid search |
| **Amazon S3 Vectors** | Vector storage and query built into S3 ("vector buckets"), launched in 2025 | Very large scale at low storage cost; slower queries than in-memory engines | Large archives, cost-sensitive RAG, rarely queried data |
| **Aurora PostgreSQL / RDS for PostgreSQL with pgvector** | Managed Postgres with the pgvector extension | Up to tens of millions of vectors, typically | Apps that already use Postgres; combining SQL and vectors |
| **Amazon MemoryDB** (vector search) | In-memory, Redis/Valkey-compatible, durable | Very low latency; limited by RAM | Real-time recommendations, semantic caching |
| **Amazon ElastiCache for Valkey** (vector search) | In-memory cache with vector search | Very low latency; limited by RAM | Caching LLM responses, fast lookups |
| **Amazon DocumentDB** (vector search) | MongoDB-compatible document DB with vector indexes | Moderate | Apps already on DocumentDB |
| **Amazon Neptune Analytics** | Graph database with vector search | Moderate | Combining knowledge graphs with semantic search (GraphRAG) |

### 9.2 Fully managed RAG: Amazon Bedrock Knowledge Bases

This is the easiest end-to-end option. You point it at documents in S3, such as a 100-page user guide, and Bedrock does the rest:

1. Splits the documents into chunks.
2. Embeds them, for example with **Amazon Titan Text Embeddings** or **Cohere Embed**.
3. Stores the vectors in a vector store you choose: OpenSearch Serverless, S3 Vectors, Aurora pgvector, Neptune Analytics, or third-party options like Pinecone, MongoDB Atlas and Redis.
4. Answers queries through its API, either retrieval only or retrieval plus answer generation.

An MCP tool like `search_user_guide(query)` could simply call the Bedrock Knowledge Base retrieve API instead of Chroma.

### 9.3 Third-party databases on AWS

Pinecone, Zilliz (Milvus), Qdrant Cloud, Weaviate Cloud and MongoDB Atlas can all run in AWS regions, many through the AWS Marketplace.

### 9.4 SDK support

| Language | Libraries |
|---|---|
| Python | `boto3`, `opensearch-py`, `psycopg` + `pgvector` |
| TypeScript | AWS SDK for JavaScript v3, `@opensearch-project/opensearch` |
| C# | AWS SDK for .NET, `OpenSearch.Client`, Npgsql + `pgvector-dotnet` |

### 9.5 Recommendation

| Need | Choose |
|---|---|
| Least effort, managed RAG | Bedrock Knowledge Bases, with S3 Vectors or OpenSearch Serverless as the store |
| Production search with hybrid keyword and vector search | OpenSearch Service |
| Already on Postgres | Aurora PostgreSQL + pgvector |
| Lowest cost at large scale | S3 Vectors |

AWS features and pricing change often, so check the current AWS docs, especially for S3 Vectors because it's new.

---

## 10. Tokens vs Context Window

Tokens are the **units** an LLM reads and writes. The context window is the **maximum number of tokens** the model can handle in one request.

### 10.1 Tokens

A token is a chunk of text, usually a word, part of a word or a punctuation mark. The model never sees characters or words directly, only tokens.

```
"Unbelievable results!"  ->  ["Un", "believ", "able", " results", "!"]  = 5 tokens
```

Rough rules for English:

- 1 token is about 4 characters, or about 0.75 words.
- 100 words is about 130 tokens.
- One page is about 500-700 tokens.

Exact counts depend on the model's **tokenizer**, so the same text can give slightly different counts on different models. Code, non-English text and numbers usually take more tokens per word.

Tokens are also how you're **billed**: API pricing is per million input tokens and per million output tokens.

### 10.2 Context window

The context window is the model's **working memory for one request**. Everything has to fit inside it at the same time:

```
+----------------- Context window (e.g. 131k tokens) ------------------+
| System prompt | Tool definitions | Chat history | Retrieved docs |    |
| User question | ...                              | Model's answer    |
+-----------------------------------------------------------------------+
```

- **Input tokens:** the system prompt, MCP tool descriptions, previous messages, any documents you include, and the new question.
- **Output tokens:** the model's reply, including tool calls and any reasoning tokens.
- **Input plus output must fit in the window.** If they don't, the request fails or older content has to be cut or summarised.
- The model has no memory between requests. The agent resends the conversation each turn, so the history keeps using up the window.

### 10.3 Side by side

| | Tokens | Context window |
|---|---|---|
| What it is | Unit of text | Capacity limit, measured in tokens |
| Example | "Hello world" = 2 tokens | `openai/gpt-oss-120b` is about 131k tokens |
| Affects | Cost (you pay per token) and speed | What can fit in a single request |
| Analogy | Bytes | RAM size |

### 10.4 How this applies to this project

- **100-page guide:** about 50-75k tokens. That fits in a 131k window, which is why passing the whole guide works.
- **Each turn of the console agent** sends the system prompt, all tool definitions, the chat history and the question. A long chat can eventually fill the window.
- **A vector DB (RAG)** saves tokens by sending only the top 5 relevant chunks, about 1-2k tokens, instead of the whole guide. That means lower cost, faster responses, and room for more history.

Separately, the output limit is often smaller than the full window. Some models cap each reply at a lower number of tokens even when the window is large.
