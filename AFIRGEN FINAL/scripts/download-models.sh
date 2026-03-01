#!/bin/bash
# download-models.sh
# Automated script to download all required models from HuggingFace

set -e  # Exit on error

echo "=========================================="
echo "AFIRGen Model Download Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
MODELS_DIR="${MODELS_DIR:-./models}"
HF_USER="navaneeth005"

# Create models directory if it doesn't exist
mkdir -p "$MODELS_DIR"

echo -e "${YELLOW}Installing huggingface-hub CLI...${NC}"
pip install -q huggingface-hub[cli] || {
    echo -e "${RED}Failed to install huggingface-hub${NC}"
    exit 1
}

echo -e "${GREEN}✓ huggingface-hub installed${NC}"
echo ""

# Function to download a model file
download_model() {
    local repo_id=$1
    local filename=$2
    local output_name=$3
    
    echo -e "${YELLOW}Downloading ${output_name}...${NC}"
    echo "  Repository: ${repo_id}"
    echo "  File: ${filename}"
    
    huggingface-cli download \
        "${repo_id}" \
        "${filename}" \
        --local-dir "$MODELS_DIR" \
        --local-dir-use-symlinks False \
        --quiet || {
        echo -e "${RED}✗ Failed to download ${output_name}${NC}"
        return 1
    }
    
    # Rename if needed
    if [ "$filename" != "$output_name" ]; then
        mv "$MODELS_DIR/$filename" "$MODELS_DIR/$output_name" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✓ Downloaded ${output_name}${NC}"
    echo ""
}

# Download GGUF models
echo "=========================================="
echo "Downloading GGUF Models"
echo "=========================================="
echo ""

# 1. 2-line summarizer
download_model \
    "${HF_USER}/complaint_2summarizing" \
    "complaint_2summarizing.gguf" \
    "complaint_2summarizing.gguf"

# 2. Complaint summarizer
download_model \
    "${HF_USER}/complaint_summarizing_model_gguf" \
    "complaint_summarizing_model.gguf" \
    "complaint_summarizing_model.gguf"

# 3. RAG model
download_model \
    "${HF_USER}/BNS-RAG-gguf" \
    "BNS-RAG-q4k.gguf" \
    "BNS-RAG-q4k.gguf"

# Download Whisper model (using whisper library)
echo "=========================================="
echo "Downloading Whisper Model"
echo "=========================================="
echo ""

echo -e "${YELLOW}Installing openai-whisper...${NC}"
pip install -q openai-whisper || {
    echo -e "${RED}Failed to install openai-whisper${NC}"
    exit 1
}

echo -e "${YELLOW}Downloading Whisper 'tiny' model...${NC}"
python3 << 'EOF'
import whisper
import os

# This will download the model to the cache
model = whisper.load_model("tiny")
print("✓ Whisper model downloaded successfully")
EOF

echo -e "${GREEN}✓ Whisper model ready${NC}"
echo ""

# Download Donut OCR model
echo "=========================================="
echo "Downloading Donut OCR Model"
echo "=========================================="
echo ""

echo -e "${YELLOW}Installing transformers...${NC}"
pip install -q transformers torch pillow || {
    echo -e "${RED}Failed to install transformers${NC}"
    exit 1
}

echo -e "${YELLOW}Downloading Donut OCR model...${NC}"
python3 << 'EOF'
from transformers import DonutProcessor, VisionEncoderDecoderModel

# Download the model (will be cached)
processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base")
print("✓ Donut OCR model downloaded successfully")
EOF

echo -e "${GREEN}✓ Donut OCR model ready${NC}"
echo ""

# Verify downloads
echo "=========================================="
echo "Verifying Downloads"
echo "=========================================="
echo ""

REQUIRED_FILES=(
    "complaint_2summarizing.gguf"
    "complaint_summarizing_model.gguf"
    "BNS-RAG-q4k.gguf"
)

ALL_GOOD=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$MODELS_DIR/$file" ]; then
        size=$(du -h "$MODELS_DIR/$file" | cut -f1)
        echo -e "${GREEN}✓${NC} $file (${size})"
    else
        echo -e "${RED}✗${NC} $file (missing)"
        ALL_GOOD=false
    fi
done

echo ""
if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}=========================================="
    echo "All models downloaded successfully!"
    echo "==========================================${NC}"
    echo ""
    echo "Models location: $MODELS_DIR"
    echo ""
    echo "Total size:"
    du -sh "$MODELS_DIR"
else
    echo -e "${RED}=========================================="
    echo "Some models failed to download"
    echo "==========================================${NC}"
    exit 1
fi
