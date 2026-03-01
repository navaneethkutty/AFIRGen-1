"""
Export IPC sections and embeddings from ChromaDB.
Saves to JSON file for migration to new vector database.
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChromaDBExporter:
    """Exports IPC sections from ChromaDB to JSON."""
    
    def __init__(self, chroma_path: str, collection_name: str = 'ipc_sections'):
        """
        Initialize exporter.
        
        Args:
            chroma_path: Path to ChromaDB storage
            collection_name: Name of collection to export
        """
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
    
    def connect(self) -> None:
        """Connect to ChromaDB."""
        try:
            self.client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.chroma_path
            ))
            
            self.collection = self.client.get_collection(self.collection_name)
            logger.info(f"Connected to ChromaDB collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise
    
    def export(self, output_file: str) -> int:
        """
        Export all IPC sections to JSON file.
        
        Args:
            output_file: Path to output JSON file
        
        Returns:
            Number of sections exported
        """
        if not self.collection:
            raise RuntimeError("Not connected to ChromaDB")
        
        try:
            # Get all documents from collection
            results = self.collection.get(
                include=['embeddings', 'metadatas', 'documents']
            )
            
            # Format data
            exported_data = []
            
            for i in range(len(results['ids'])):
                section_data = {
                    'id': results['ids'][i],
                    'section_number': results['metadatas'][i].get('section_number', ''),
                    'description': results['documents'][i] if results['documents'] else '',
                    'penalty': results['metadatas'][i].get('penalty', ''),
                    'embedding': results['embeddings'][i] if results['embeddings'] else None,
                    'metadata': results['metadatas'][i]
                }
                exported_data.append(section_data)
            
            # Write to JSON file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(exported_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(exported_data)} IPC sections to {output_file}")
            return len(exported_data)
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self.collection:
            raise RuntimeError("Not connected to ChromaDB")
        
        count = self.collection.count()
        
        return {
            'collection_name': self.collection_name,
            'document_count': count,
            'chroma_path': self.chroma_path
        }


def main():
    """Main export function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export IPC sections from ChromaDB')
    parser.add_argument(
        '--chroma-path',
        required=True,
        help='Path to ChromaDB storage directory'
    )
    parser.add_argument(
        '--collection',
        default='ipc_sections',
        help='Collection name (default: ipc_sections)'
    )
    parser.add_argument(
        '--output',
        default='ipc_sections_export.json',
        help='Output JSON file path (default: ipc_sections_export.json)'
    )
    
    args = parser.parse_args()
    
    try:
        # Create exporter
        exporter = ChromaDBExporter(args.chroma_path, args.collection)
        
        # Connect
        exporter.connect()
        
        # Get stats
        stats = exporter.get_stats()
        logger.info(f"Collection stats: {stats}")
        
        # Export
        count = exporter.export(args.output)
        
        logger.info("=" * 60)
        logger.info("Export completed successfully!")
        logger.info(f"Exported {count} IPC sections")
        logger.info(f"Output file: {args.output}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
