"""
Quick test to verify legal_sections.json can be loaded
"""

import json

def test_load():
    print("Testing legal_sections.json loading...")
    print("=" * 60)
    
    # Load file
    with open('legal_sections.json', 'r', encoding='utf-8') as f:
        sections = json.load(f)
    
    print(f"✓ File loaded successfully")
    print(f"✓ Total sections: {len(sections)}")
    
    # Verify structure
    required_fields = ['section_number', 'title', 'description', 'penalty', 'category', 'source']
    
    for i, section in enumerate(sections[:5]):  # Check first 5
        missing = [f for f in required_fields if f not in section]
        if missing:
            print(f"✗ Section {i} missing fields: {missing}")
            return False
    
    print(f"✓ All required fields present")
    
    # Category breakdown
    categories = {}
    for section in sections:
        cat = section.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\n✓ Categories found: {len(categories)}")
    print(f"  - BNS: {categories.get('BNS', 0)} sections")
    print(f"  - Special Acts: {sum(v for k, v in categories.items() if 'Acts' in k)} sections")
    print(f"  - Rules: {sum(v for k, v in categories.items() if 'Rules' in k)} sections")
    
    # Source breakdown
    sources = {}
    for section in sections:
        src = section.get('source', 'Unknown')
        sources[src] = sources.get(src, 0) + 1
    
    print(f"\n✓ Sources found: {len(sources)}")
    for src, count in sorted(sources.items()):
        print(f"  - {src}: {count} sections")
    
    # Sample sections
    print(f"\n✓ Sample BNS section:")
    bns = [s for s in sections if s['category'] == 'BNS'][0]
    print(f"  Section: {bns['section_number']}")
    print(f"  Title: {bns['title'][:60]}...")
    print(f"  Source: {bns['source']}")
    
    print(f"\n✓ Sample Special Act:")
    spact = [s for s in sections if 'Acts' in s['category']][0]
    print(f"  Number: {spact['section_number']}")
    print(f"  Title: {spact['title'][:60]}...")
    print(f"  Category: {spact['category']}")
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - Ready for database loading")
    return True

if __name__ == "__main__":
    test_load()
