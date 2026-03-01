"""
Migrate IPC sections to new vector database.
Generates new embeddings with Titan and inserts into target database.
"""

import json
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.aws.titan_embeddings_client import TitanEmbeddingsClient
from services.vector_db.factory import VectorDBFactory


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDBMigrator:
    """Migrates IPC sections to new vector database."""
    
    def __init__(
        self,
        titan_client: TitanEmbeddingsClient,
        vector_db,
        batch_size: int = 25
    ):
        """
        Initialize migrator.
        
        Args:
            titan_client: Titan embeddings client
            vector_db: Target vector database
            batch_size: Batch size for processing
        """
        self.titan_client = titan_client
        self.vector_db = vector_db
        self.batch_size = batch_size
    
    async def migrate(
        self,
        input_file: str,
        index_name: str,
        regenerate_embeddings: bool = True
    ) -> Dict[str, Any]:
        """
        Migrate IPC sections from JSON file.
        
        Args:
            input_file: Path to exported JSON file
            index_name: Target index/table name
            regenerate_embeddings: Whether to regenerate embeddings
        
        Returns:
            Migration statistics
        """
        logger.info(f"Starting migration from {input_file}")
        
        # Load data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} IPC sections")
        
        # Connect to vector database
        await self.vector_db.connect()
        logger.info("Connected to vector database")
        
        # Create index if not exists
        if not await self.vector_db.index_exists(index_name):
            await self.vector_db.create_index(
                index_name=index_name,
                dimension=1536,
                metric='cosine'
            )
            logger.info(f"Created index: {index_name}")
        
        # Process in batches
        total_inserted = 0
        failed_count = 0
        
        for i in range(0, len(data), self.batch_size):
            batch = data[i:i + self.batch_size]
            logger.info(f"Processing batch {i // self.batch_size + 1} ({len(batch)} sections)")
            
            try:
                # Prepare texts and metadata
                texts = [item['description'] for item in batch]
                metadata_list = [
                    {
                        'section_number': item['section_number'],
                        'description': item['description'],
                        'penalty': item['penalty']
                    }
                    for item in batch
                ]
                
                # Generate embeddings
                if regenerate_embeddings:
                    logger.info("Generating new embeddings with Titan...")
                    embeddings = await self.titan_client.generate_batch_embeddings(texts)
                else:
                    # Use existing embeddings
                    embeddings = [
                        np.array(item['embedding'], dtype=np.float32)
                        for item in batch
                        if item.get('embedding')
                    ]
                    
                    if len(embeddings) != len(batch):
                        logger.warning(
                            f"Missing embeddings in batch, regenerating..."
                        )
                        embeddings = await self.titan_client.generate_batch_embeddings(texts)
                
                # Insert into vector database
                ids = await self.vector_db.insert_vectors(
                    index_name=index_name,
                    vectors=embeddings,
                    metadata=metadata_list
                )
                
                total_inserted += len(ids)
                logger.info(f"Inserted {len(ids)} sections (total: {total_inserted})")
                
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                failed_count += len(batch)
        
        # Verify migration
        stats = await self.vector_db.get_index_stats(index_name)
        logger.info(f"Index stats: {stats}")
        
        # Perform sample search
        await self._verify_search(index_name, data[0]['description'])
        
        return {
            'total_sections': len(data),
            'inserted': total_inserted,
            'failed': failed_count,
            'index_stats': stats
        }
    
    async def _verify_search(self, index_name: str, sample_text: str) -> None:
        """Verify search functionality with sample query."""
        try:
            logger.info("Verifying search functionality...")
            
            # Generate embedding for sample
            embedding = await self.titan_client.generate_embedding(sample_text)
            
            # Perform search
            results = await self.vector_db.similarity_search(
                index_name=index_name,
                query_vector=embedding,
                top_k=3
            )
            
            logger.info(f"Search returned {len(results)} results")
            if results:
                logger.info(f"Top result: Section {results[0].section_number} (score: {results[0].score:.4f})")
            
        except Exception as e:
            logger.error(f"Search verification failed: {e}")


async def main():
    """Main migration function."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Migrate IPC sections to vector database')
    parser.add_argument(
        '--input',
        required=True,
        help='Input JSON file from export'
    )
    parser.add_argument(
        '--index-name',
        default='ipc_sections',
        help='Target index/table name (default: ipc_sections)'
    )
    parser.add_argument(
        '--regenerate-embeddings',
        action='store_true',
        help='Regenerate embeddings with Titan (default: use existing)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=25,
        help='Batch size for processing (default: 25)'
    )
    
    args = parser.parse_args()
    
    try:
        # Get configuration from environment
        region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Create clients
        titan_client = TitanEmbeddingsClient(region=region)
        vector_db = VectorDBFactory.create_vector_db()
        
        # Create migrator
        migrator = VectorDBMigrator(
            titan_client=titan_client,
            vector_db=vector_db,
            batch_size=args.batch_size
        )
        
        # Run migration
        stats = await migrator.migrate(
            input_file=args.input,
            index_name=args.index_name,
            regenerate_embeddings=args.regenerate_embeddings
        )
        
        # Close connections
        await vector_db.close()
        
        logger.info("=" * 60)
        logger.info("Migration completed successfully!")
        logger.info(f"Total sections: {stats['total_sections']}")
        logger.info(f"Inserted: {stats['inserted']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
