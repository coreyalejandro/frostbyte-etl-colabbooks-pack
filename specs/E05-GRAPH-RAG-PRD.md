# Enhancement #5 – Graph RAG Support

## All-In-One Zero-Shot PRD

**Status:** Deterministic, executable  
**Format:** COSTAR System Prompt + Zero-Shot Prompt + PRD + Implementation Plan

---

## COSTAR System Prompt

```
[CONTEXT]
You are implementing Graph RAG (Retrieval-Augmented Generation) support for the Frostbyte ETL pipeline. The system must extract entities and relationships from ingested documents, store them in a graph database, and provide a natural language query endpoint that combines vector and graph retrieval. All design decisions (graph schema, extraction method, API endpoints) are defined in the PRD below. No decisions are left open.

[OBJECTIVE]
Generate the complete code for:
- Entity/relationship extraction pipeline (using spaCy + rule-based patterns)
- Neo4j graph storage and indexing
- FastAPI endpoint `/graph/query` for hybrid search
- Background worker to process documents and populate graph

[STYLE]
Imperative, production-ready. Provide each file content in a code block with its full relative path. No commentary.

[AUDIENCE]
Backend developer. Execute the steps exactly as written.
```

---

## Zero-Shot Prompt

*Concatenated with the PRD and Implementation Plan below – feed this entire document to the implementation LLM.*

---

## Production Requirements Document (PRD) – Graph RAG Support

### 1. Technology Choices

- **Graph Database**: Neo4j 5.x (community edition)
- **Python Driver**: `neo4j`
- **NLP Library**: `spaCy` with `en_core_web_sm` model
- **Custom Entity Patterns**: Defined in `graph/entity_patterns.json`
- **Hybrid Query**: Combine vector similarity (from existing Qdrant) with graph traversal.

### 2. Graph Data Model

**Nodes**:

- `Document`: properties `{id: str, filename: str, tenant_id: str}`
- `Chunk`: properties `{chunk_id: str, content: str, embedding: list}`
- `Entity`: properties `{name: str, type: str, normalized: str}`

**Relationships**:

- `(:Chunk)-[:HAS_ENTITY]->(:Entity)`
- `(:Document)-[:CONTAINS]->(:Chunk)`
- `(:Entity)-[:RELATES_TO]->(:Entity)` (with property `relation_type`)

**Indexes**:

- `Entity(name)` unique constraint
- `Entity(type)` index

### 3. Extraction Pipeline

- **Trigger**: After a document chunk is created (post‑embedding).
- **Input**: `chunk_id`, `content` (string).
- **Process**:
  1. Load `en_core_web_sm` model.
  2. Apply custom NER patterns (JSON‑based rule matcher).
  3. Extract entities: deduplicate, normalize (lowercase, strip).
  4. Extract relationships: using dependency parsing + pattern rules (e.g., `[SUBJ] works_for [OBJ]`).
- **Output**: Cypher `MERGE` statements to Neo4j.

### 4. Hybrid Query Endpoint

**Endpoint**: `POST /graph/query`

**Request Body**:

```json
{
  "tenant_id": "uuid",
  "natural_language": "string",
  "entity_filters": ["Person", "Organization"],
  "vector_weight": 0.7,
  "graph_weight": 0.3,
  "top_k": 10
}
```

**Process**:

1. Generate embedding for `natural_language` via OpenRouter.
2. Perform vector search in Qdrant, return candidate chunks.
3. Extract entities from query text (same spaCy pipeline).
4. Traverse graph: find chunks connected to those entities, assign relevance score based on shortest path.
5. Combine scores using weighted linear combination.
6. Return ranked chunks.

**Response**:

```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "content": "string",
      "document_id": "uuid",
      "score": 0.95,
      "graph_entities": [{"name": "...", "type": "..."}]
    }
  ]
}
```

### 5. Database Configuration

Neo4j connection settings **must** be read from environment:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

---

## Deterministic Implementation Plan

### Step 1 – Install dependencies

```bash
pip install neo4j spacy
python -m spacy download en_core_web_sm
```

### Step 2 – Create directory structure

```bash
mkdir -p app/graph
mkdir -p app/graph/patterns
```

### Step 3 – Define entity patterns

**File**: `app/graph/patterns/entity_patterns.json`

```json
{
  "entity_rules": [
    {
      "label": "PERSON",
      "pattern": [{"LOWER": {"IN": ["mr", "ms", "mrs", "dr"]}}, {"POS": "PROPN"}]
    },
    {
      "label": "ORG",
      "pattern": [{"LOWER": "company"}, {"POS": "PROPN"}]
    }
  ],
  "relation_rules": [
    {
      "name": "WORKS_FOR",
      "subject_pos": "PROPN",
      "verb": {"LEMMA": "work"},
      "object_pos": "PROPN"
    }
  ]
}
```

### Step 4 – Create Neo4j connection utility

**File**: `app/graph/neo4j_client.py`

```python
import os
from neo4j import GraphDatabase, AsyncGraphDatabase

class Neo4jClient:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()

    def create_indexes(self):
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
            session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (c:Chunk) ON (c.chunk_id)")

neo4j_client = Neo4jClient()
```

### Step 5 – Implement entity/relation extractor

**File**: `app/graph/extractor.py`

```python
import json
import spacy
from spacy.matcher import Matcher
from pathlib import Path

class GraphExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.matcher = Matcher(self.nlp.vocab)
        self._load_patterns()

    def _load_patterns(self):
        patterns_path = Path(__file__).parent / "patterns" / "entity_patterns.json"
        with open(patterns_path) as f:
            data = json.load(f)
        for rule in data["entity_rules"]:
            self.matcher.add(rule["label"], [rule["pattern"]])

    def extract_entities(self, text: str):
        doc = self.nlp(text)
        matches = self.matcher(doc)
        entities = []
        for match_id, start, end in matches:
            span = doc[start:end]
            label = self.nlp.vocab.strings[match_id]
            entities.append({
                "name": span.text,
                "type": label,
                "normalized": span.text.lower().strip()
            })
        # also include built-in NER
        for ent in doc.ents:
            entities.append({
                "name": ent.text,
                "type": ent.label_,
                "normalized": ent.text.lower().strip()
            })
        # deduplicate
        unique = {e["normalized"]: e for e in entities}.values()
        return list(unique)
```

### Step 6 – Create background task for graph ingestion

**File**: `app/graph/ingest.py`

```python
import asyncio
from app.graph.neo4j_client import neo4j_client
from app.graph.extractor import GraphExtractor
from app.db import get_connection

extractor = GraphExtractor()

async def process_chunk_for_graph(chunk_id: str, content: str):
    entities = extractor.extract_entities(content)
    with neo4j_client.driver.session() as session:
        # Merge chunk node
        session.run(
            "MERGE (c:Chunk {chunk_id: $chunk_id})",
            chunk_id=chunk_id
        )
        # Merge entities and create relationships
        for ent in entities:
            session.run(
                """
                MERGE (e:Entity {name: $normalized})
                ON CREATE SET e.type = $type, e.display_name = $name
                WITH e
                MATCH (c:Chunk {chunk_id: $chunk_id})
                MERGE (c)-[:HAS_ENTITY]->(e)
                """,
                normalized=ent["normalized"],
                type=ent["type"],
                name=ent["name"],
                chunk_id=chunk_id
            )
    return len(entities)
```

### Step 7 – Hook into existing document processing

In `app/api/endpoints/documents.py`, after chunk is created and embedded, call:

```python
from app.graph.ingest import process_chunk_for_graph

# inside the function that creates a chunk
asyncio.create_task(process_chunk_for_graph(str(chunk_id), content))
```

### Step 8 – Implement hybrid query endpoint

**File**: `app/api/endpoints/graph.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from app.graph.neo4j_client import neo4j_client
from app.services.embeddings import get_embedding
from app.services.vector_search import search_qdrant

router = APIRouter(prefix="/graph", tags=["graph"])

class GraphQueryRequest(BaseModel):
    tenant_id: UUID
    natural_language: str
    entity_filters: Optional[List[str]] = None
    vector_weight: float = 0.7
    graph_weight: float = 0.3
    top_k: int = 10

class GraphQueryResponse(BaseModel):
    results: List[dict]

@router.post("/query", response_model=GraphQueryResponse)
async def hybrid_query(request: GraphQueryRequest):
    # 1. Vector search
    embedding = await get_embedding(request.natural_language)
    vector_results = await search_qdrant(
        tenant_id=request.tenant_id,
        vector=embedding,
        top_k=request.top_k * 2
    )
    # 2. Extract entities from query
    from app.graph.extractor import extractor
    query_entities = extractor.extract_entities(request.natural_language)
    entity_names = [e["normalized"] for e in query_entities]
    if request.entity_filters:
        entity_names = [e for e in entity_names if e in request.entity_filters]  # simplified

    # 3. Graph traversal: for each candidate chunk, compute graph score
    chunk_scores = []
    with neo4j_client.driver.session() as session:
        for vec_result in vector_results:
            chunk_id = vec_result["chunk_id"]
            # Count how many query entities are connected to this chunk
            result = session.run(
                """
                MATCH (c:Chunk {chunk_id: $chunk_id})-[:HAS_ENTITY]->(e:Entity)
                WHERE e.name IN $entities
                RETURN count(DISTINCT e) AS entity_count
                """,
                chunk_id=chunk_id,
                entities=entity_names
            )
            record = result.single()
            entity_count = record["entity_count"] if record else 0
            graph_score = entity_count / max(len(entity_names), 1)
            combined = (request.vector_weight * vec_result["score"]) + (request.graph_weight * graph_score)
            chunk_scores.append({
                "chunk_id": chunk_id,
                "content": vec_result["content"],
                "document_id": vec_result["document_id"],
                "score": combined,
                "graph_entities": []  # optional enrichment
            })
    # Sort and top_k
    chunk_scores.sort(key=lambda x: x["score"], reverse=True)
    return GraphQueryResponse(results=chunk_scores[:request.top_k])
```

### Step 9 – Create database migration for Neo4j constraints

Execute the following Python script once (e.g., as a startup task):

```python
from app.graph.neo4j_client import neo4j_client
neo4j_client.create_indexes()
```

### Step 10 – Commit

```bash
git add app/graph
git add app/api/endpoints/graph.py
git commit -m "feat(graph): add Graph RAG support with Neo4j and hybrid query"
```
