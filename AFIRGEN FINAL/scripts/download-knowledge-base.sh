#!/bin/bash
# download-knowledge-base.sh
# Automated script to download knowledge base files from HuggingFace

set -e  # Exit on error

echo "=========================================="
echo "AFIRGen Knowledge Base Download Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
RAG_DB_DIR="${RAG_DB_DIR:-./rag db}"
GENERAL_DB_DIR="${GENERAL_DB_DIR:-./general retrieval db}"
HF_USER="navaneeth005"

# Create directories
mkdir -p "$RAG_DB_DIR"
mkdir -p "$GENERAL_DB_DIR"

echo -e "${YELLOW}Installing huggingface-hub CLI...${NC}"
pip install -q huggingface-hub[cli] datasets || {
    echo -e "${RED}Failed to install required packages${NC}"
    exit 1
}

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Function to download dataset and convert to JSONL
download_dataset() {
    local dataset_id=$1
    local output_file=$2
    local output_dir=$3
    
    echo -e "${YELLOW}Downloading ${output_file}...${NC}"
    echo "  Dataset: ${dataset_id}"
    
    python3 << EOF
from datasets import load_dataset
import json
import os

try:
    # Load dataset from HuggingFace
    dataset = load_dataset("${dataset_id}", split="train")
    
    # Create output directory
    os.makedirs("${output_dir}", exist_ok=True)
    
    # Save as JSONL
    output_path = os.path.join("${output_dir}", "${output_file}")
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✓ Saved {len(dataset)} records to {output_path}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Downloaded ${output_file}${NC}"
    else
        echo -e "${RED}✗ Failed to download ${output_file}${NC}"
        return 1
    fi
    echo ""
}

# Download RAG database files
echo "=========================================="
echo "Downloading RAG Database Files"
echo "=========================================="
echo ""

download_dataset \
    "${HF_USER}/BNS_definitions" \
    "BNS_basic_chroma.jsonl" \
    "$RAG_DB_DIR"

download_dataset \
    "${HF_USER}/BNS_detailed" \
    "BNS_details_chroma.jsonl" \
    "$RAG_DB_DIR"

download_dataset \
    "${HF_USER}/special_acts" \
    "BNS_spacts_chroma.jsonl" \
    "$RAG_DB_DIR"

# Download general retrieval database files
echo "=========================================="
echo "Downloading General Retrieval Files"
echo "=========================================="
echo ""

download_dataset \
    "${HF_USER}/BNS_definitions" \
    "BNS_basic.jsonl" \
    "$GENERAL_DB_DIR"

download_dataset \
    "${HF_USER}/BNS_detailed" \
    "BNS_indepth.jsonl" \
    "$GENERAL_DB_DIR"

download_dataset \
    "${HF_USER}/special_acts" \
    "spacts.jsonl" \
    "$GENERAL_DB_DIR"

# Verify downloads
echo "=========================================="
echo "Verifying Downloads"
echo "=========================================="
echo ""

echo "RAG Database Files:"
for file in "BNS_basic_chroma.jsonl" "BNS_details_chroma.jsonl" "BNS_spacts_chroma.jsonl"; do
    if [ -f "$RAG_DB_DIR/$file" ]; then
        lines=$(wc -l < "$RAG_DB_DIR/$file")
        size=$(du -h "$RAG_DB_DIR/$file" | cut -f1)
        echo -e "${GREEN}✓${NC} $file (${lines} records, ${size})"
    else
        echo -e "${RED}✗${NC} $file (missing)"
    fi
done

echo ""
echo "General Retrieval Files:"
for file in "BNS_basic.jsonl" "BNS_indepth.jsonl" "spacts.jsonl"; do
    if [ -f "$GENERAL_DB_DIR/$file" ]; then
        lines=$(wc -l < "$GENERAL_DB_DIR/$file")
        size=$(du -h "$GENERAL_DB_DIR/$file" | cut -f1)
        echo -e "${GREEN}✓${NC} $file (${lines} records, ${size})"
    else
        echo -e "${RED}✗${NC} $file (missing)"
    fi
done

echo ""
echo -e "${GREEN}=========================================="
echo "Knowledge base downloaded successfully!"
echo "==========================================${NC}"
echo ""
echo "RAG DB location: $RAG_DB_DIR"
echo "General DB location: $GENERAL_DB_DIR"
