"""
Convert HuggingFace KB datasets to MySQL-compatible JSON format
Combines BNS_basic, BNS_indepth, and spacts into single legal_sections.json
"""

import json
import os
from pathlib import Path

def load_jsonl(file_path):
    """Load JSONL file and return list of records"""
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def convert_bns_basic(records):
    """Convert BNS_basic format to MySQL format"""
    converted = []
    for record in records:
        section = {
            "section_number": str(record.get("Section", "")),
            "title": record.get("Title", ""),
            "description": record.get("Legal Definition", ""),
            "penalty": "",  # BNS_basic doesn't have separate penalty field
            "category": "BNS",
            "source": "BNS_basic"
        }
        converted.append(section)
    return converted

def convert_bns_indepth(records):
    """Convert BNS_indepth format to MySQL format"""
    converted = []
    for record in records:
        section = {
            "section_number": str(record.get("Section", "")),
            "title": record.get("Title", ""),
            "description": record.get("Legal Definition", ""),
            "penalty": record.get("Punishment", ""),
            "category": "BNS",
            "source": "BNS_indepth"
        }
        converted.append(section)
    return converted

def convert_spacts(records):
    """Convert special acts format to MySQL format"""
    converted = []
    for record in records:
        section = {
            "section_number": str(record.get("Number", "")),
            "title": record.get("Title", ""),
            "description": record.get("Legal Definition", ""),
            "penalty": "",  # Extract from description if needed
            "category": record.get("Category", "Special Acts"),
            "source": "special_acts"
        }
        converted.append(section)
    return converted

def main():
    # Paths
    kb_dir = Path("../general retrieval db")
    output_file = Path("legal_sections.json")
    
    print("Converting HuggingFace KB datasets to MySQL format...")
    print("=" * 60)
    
    all_sections = []
    
    # Load and convert BNS_basic
    print("\n1. Loading BNS_basic.jsonl...")
    bns_basic_path = kb_dir / "BNS_basic.jsonl"
    if bns_basic_path.exists():
        bns_basic = load_jsonl(bns_basic_path)
        converted_basic = convert_bns_basic(bns_basic)
        all_sections.extend(converted_basic)
        print(f"   ✓ Loaded {len(converted_basic)} sections from BNS_basic")
    else:
        print(f"   ✗ File not found: {bns_basic_path}")
    
    # Load and convert BNS_indepth
    print("\n2. Loading BNS_indepth.jsonl...")
    bns_indepth_path = kb_dir / "BNS_indepth.jsonl"
    if bns_indepth_path.exists():
        bns_indepth = load_jsonl(bns_indepth_path)
        converted_indepth = convert_bns_indepth(bns_indepth)
        all_sections.extend(converted_indepth)
        print(f"   ✓ Loaded {len(converted_indepth)} sections from BNS_indepth")
    else:
        print(f"   ✗ File not found: {bns_indepth_path}")
    
    # Load and convert special acts
    print("\n3. Loading spacts.jsonl...")
    spacts_path = kb_dir / "spacts.jsonl"
    if spacts_path.exists():
        spacts = load_jsonl(spacts_path)
        converted_spacts = convert_spacts(spacts)
        all_sections.extend(converted_spacts)
        print(f"   ✓ Loaded {len(converted_spacts)} sections from special_acts")
    else:
        print(f"   ✗ File not found: {spacts_path}")
    
    # Save combined file
    print(f"\n4. Saving combined file: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_sections, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ Saved {len(all_sections)} total sections")
    
    # Summary
    print("\n" + "=" * 60)
    print("CONVERSION COMPLETE")
    print("=" * 60)
    print(f"Total sections: {len(all_sections)}")
    print(f"Output file: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Category breakdown
    categories = {}
    for section in all_sections:
        cat = section.get("category", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nBreakdown by category:")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count} sections")
    
    # Sample section
    if all_sections:
        print("\nSample section:")
        sample = all_sections[0]
        print(f"  Section: {sample['section_number']}")
        print(f"  Title: {sample['title'][:80]}...")
        print(f"  Category: {sample['category']}")

if __name__ == "__main__":
    main()
