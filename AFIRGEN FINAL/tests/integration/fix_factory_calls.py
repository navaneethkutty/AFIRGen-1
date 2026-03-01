#!/usr/bin/env python3
"""
Script to fix VectorDBFactory.create calls in integration tests.
"""

import re

def fix_factory_calls(filepath):
    """Fix VectorDBFactory.create calls to use create_vector_db."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern to match VectorDBFactory.create calls
    old_pattern = r'vector_db = VectorDBFactory\.create\(\s*db_type=vector_db_type,\s*region=aws_region,\s*opensearch_endpoint=opensearch_endpoint,\s*aurora_config=aurora_config\s*\)'
    
    new_code = '''from services.vector_db.factory import VectorDBFactory
    
    vector_db = VectorDBFactory.create_vector_db(
        db_type=vector_db_type,
        endpoint=opensearch_endpoint,
        host=aurora_config.get("host"),
        port=aurora_config.get("port"),
        database=aurora_config.get("database"),
        user=aurora_config.get("user"),
        password=aurora_config.get("password"),
        table_name=aurora_config.get("table")
    )'''
    
    # Replace
    content = re.sub(old_pattern, new_code, content)
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")

if __name__ == "__main__":
    fix_factory_calls("test_fir_generation_integration.py")
    print("Done!")
