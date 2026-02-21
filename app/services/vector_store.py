from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    SparseVector, SparseVectorParams, Modifier,
    Prefetch, FusionQuery, Fusion,
    MultiVectorConfig, MultiVectorComparator
)
from app.services.colbert_service import ColbertService
from app.config import get_settings
from app.services.sparse_vector_service import SparseVectorService
from loguru import logger
from uuid import uuid4


class VectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.client = QdrantClient(
            url=self.settings.qdrant_url,
            api_key=self.settings.qdrant_api_key
        )
        self.collection_name = self.settings.qdrant_collection_name
        self.sparse_service = SparseVectorService()
        self.colbert_service = ColbertService()
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create hybrid collection with dense, colbert and sparse vectors if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": VectorParams(
                            size=self.settings.embedding_dimensions,
                            distance=Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "sparse": SparseVectorParams()
                    }
                )
                logger.info(f"Created hybrid collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Collection creation error: {e}")
            raise
    
    def upsert_chunks(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict]
    ) -> list[str]:
        """Insert chunks with dense, colbert and sparse vectors"""
        points = []
        chunk_ids = []

        for i, (chunk, embedding, metadata) in enumerate(zip(chunks, embeddings, metadatas)):
            chunk_id = str(uuid4())
            chunk_ids.append(chunk_id)

            # Generate sparse vector for the chunk
            sparse_vector = self.sparse_service.generate_sparse_vector(chunk)
            
            vector_dict = {
                "dense": embedding,
                "sparse": sparse_vector
            }
            
            if self.colbert_service.enabled and colbert_vectors:
                vector_dict["colbert"] = colbert_vectors[i]

            points.append(PointStruct(
                id=chunk_id,
                vector=vector_dict,
                payload={
                    "content": chunk,
                    **metadata
                }
            ))

        try:
            # self.client.upsert(
            #     collection_name=self.collection_name,
            #     points=points
            # )
            # logger.info(f"Upserted {len(points)} chunks with dual vectors")
            
            
            # Upsert in batches to avoid payload size limits (ColBERT vectors are large)
            batch_size = 5 if self.colbert_service.enabled else 50
            
            for i in range(0, len(points), batch_size):
                batch_points = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points
                )
                logger.info(f"Upserted batch {i//batch_size + 1}: {len(batch_points)} chunks")
            
            logger.info(f"Successfully upserted all {len(points)} chunks with dual vectors")
            return chunk_ids
        except Exception as e:
            logger.error(f"Upsert error: {e}")
            raise
        
    def search_colbert(
        self,
        query_text: str,
        top_k: int,
        search_filter=None
    ) -> list:
        """ColBERT-only multi-vector search"""
        if not self.colbert_service.enabled:
            logger.warning("ColBERT search requested but service is disabled")
            return []
            
        colbert_query = self.colbert_service.generate_colbert_vectors([query_text])[0]
        
        return self.client.query_points(
            collection_name=self.collection_name,
            query=colbert_query,
            using="colbert",
            query_filter=search_filter,
            limit=top_k,
            with_payload=True
        ).points
        
        
    def search_dense(
        self,
        query_vector: list[float],
        top_k: int,
        search_filter=None
    ) -> list:
        """Dense-only semantic search"""
        return self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using="dense",
            query_filter=search_filter,
            limit=top_k,
            with_payload=True
        ).points

    def search_sparse(
        self,
        query_text: str,
        top_k: int,
        search_filter=None
    ) -> list:
        """Sparse-only keyword search (BM25)"""
        sparse_query = self.sparse_service.generate_sparse_vector(query_text)

        return self.client.query_points(
            collection_name=self.collection_name,
            query=sparse_query,
            using="sparse",
            query_filter=search_filter,
            limit=top_k,
            with_payload=True
        ).points

    def search_hybrid(
        self,
        query_vector: list[float],
        query_text: str,
        top_k: int,
        search_filter=None
    ) -> list:
        """Hybrid search with RRF fusion"""
        sparse_query = self.sparse_service.generate_sparse_vector(query_text)

        return self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                Prefetch(query=sparse_query, using="sparse", limit=top_k * 3),
                Prefetch(query=query_vector, using="dense", limit=top_k * 3)
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
            with_payload=True
        ).points

    def search(
        self,
        query_vector: list[float] | None = None,
        top_k: int = 5,
        filter_conditions: dict | None = None,
        mode: str = "hybrid",
        query_text: str | None = None
    ) -> list[dict]:
        """
        Search for similar chunks using specified mode.

        Args:
            query_vector: Dense embedding vector (optional if query_text provided and mode is sparse/colbert)
            top_k: Number of results to return
            filter_conditions: Optional filter conditions
            mode: Search mode - "dense", "sparse", "colbert", or "hybrid" (default)
            query_text: Original query text (required for sparse/colbert/hybrid modes)

        Returns:
            List of search results with scores and metadata
        """
        try:
            search_filter = None
            if filter_conditions:
                # Build Qdrant filter from conditions if needed
                pass

            # Delegate to appropriate search method
            if mode == "dense":
                if not query_vector:
                    raise ValueError("query_vector required for dense search")
                results = self.search_dense(query_vector, top_k, search_filter)
            elif mode == "sparse":
                if not query_text:
                    raise ValueError("query_text required for sparse search")
                results = self.search_sparse(query_text, top_k, search_filter)
            elif mode == "colbert":
                if not query_text:
                    raise ValueError("query_text required for colbert search")
                results = self.search_colbert(query_text, top_k, search_filter)
            elif mode == "hybrid":
                if not query_text or not query_vector:
                    raise ValueError("query_text and query_vector required for hybrid search")
                results = self.search_hybrid(query_vector, query_text, top_k, search_filter)
            else:
                raise ValueError(f"Invalid search mode: {mode}. Must be 'dense', 'sparse', 'colbert', or 'hybrid'")

            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.payload.get("content"),
                    "metadata": {k: v for k, v in hit.payload.items() if k != "content"}
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise
    
    def delete_by_source(self, source_file: str):
        """Delete all chunks from a source file"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="source_file",
                            match=MatchValue(value=source_file)
                        )
                    ]
                )
            )
            logger.info(f"Deleted chunks from: {source_file}")
        except Exception as e:
            logger.error(f"Delete error: {e}")
            raise
