# AFIRGen Deployment Scripts

Automated scripts for downloading models and knowledge base from HuggingFace.

## Scripts Overview

### 1. download-models.sh
Downloads all required ML models from HuggingFace.

**Usage:**
```bash
chmod +x download-models.sh
./download-models.sh
```

**Downloads:**
- complaint_2summarizing.gguf (~1.5GB)
- complaint_summarizing_model.gguf (~1.5GB)
- BNS-RAG-q4k.gguf (~2GB)
- Whisper 'tiny' model (~75MB)
- Donut OCR model (~500MB)

**Total Size:** ~5GB

**Time:** 10-20 minutes (depending on internet speed)

**Environment Variables:**
- `MODELS_DIR`: Target directory (default: `./models`)

**Example:**
```bash
# Download to custom directory
MODELS_DIR=/opt/afirgen/models ./download-models.sh
```

### 2. download-knowledge-base.sh
Downloads knowledge base datasets from HuggingFace.

**Usage:**
```bash
chmod +x download-knowledge-base.sh
./download-knowledge-base.sh
```

**Downloads:**
- BNS_basic_chroma.jsonl (BNS definitions)
- BNS_details_chroma.jsonl (BNS detailed sections)
- BNS_spacts_chroma.jsonl (Special acts)
- BNS_basic.jsonl (General retrieval)
- BNS_indepth.jsonl (Detailed retrieval)
- spacts.jsonl (Special acts retrieval)

**Total Size:** ~50-100MB

**Time:** 2-5 minutes

**Environment Variables:**
- `RAG_DB_DIR`: RAG database directory (default: `./rag db`)
- `GENERAL_DB_DIR`: General retrieval directory (default: `./general retrieval db`)

**Example:**
```bash
# Download to custom directories
RAG_DB_DIR=/opt/afirgen/rag-db \
GENERAL_DB_DIR=/opt/afirgen/general-db \
./download-knowledge-base.sh
```

### 3. setup-env.sh
Generates .env configuration file with secure keys.

**Usage:**
```bash
chmod +x setup-env.sh
./setup-env.sh
```

**Features:**
- Auto-fetches RDS endpoint from Terraform
- Auto-fetches EC2 IP from Terraform
- Generates secure random keys (32 bytes)
- Configures CORS origins
- Sets up all environment variables

**Environment Variables:**
- `ENV_FILE`: Output file path (default: `.env`)

**Example:**
```bash
# Generate to custom location
ENV_FILE=/opt/afirgen/.env ./setup-env.sh
```

## Requirements

All scripts require:
- Python 3.7+
- pip (Python package manager)

The scripts will automatically install required Python packages:
- `huggingface-hub[cli]`
- `datasets`
- `openai-whisper`
- `transformers`
- `torch`
- `pillow`

## HuggingFace Source

All models and datasets are from:
- **User**: [navaneeth005](https://huggingface.co/navaneeth005)
- **Models**: https://huggingface.co/navaneeth005
- **Datasets**: https://huggingface.co/datasets/navaneeth005

## Troubleshooting

### "Permission denied"
```bash
chmod +x *.sh
```

### "pip: command not found"
Install Python and pip:
```bash
# Ubuntu/Debian
sudo apt-get install python3-pip

# macOS
brew install python3

# Windows
# Download from https://www.python.org/downloads/
```

### "huggingface-hub not found"
The scripts install it automatically, but you can install manually:
```bash
pip install huggingface-hub[cli] datasets
```

### Download fails
Check your internet connection and try again. The scripts will resume from where they left off.

### Out of disk space
Ensure you have at least 10GB free space:
```bash
df -h
```

## Integration with Makefile

These scripts are integrated into the main Makefile:

```bash
# Download models
make download-models

# Download knowledge base
make download-kb

# Setup environment
make setup-env

# Do everything
make deploy-all
```

## Manual Verification

After running the scripts, verify downloads:

```bash
# Check models
ls -lh models/
# Should show:
# - complaint_2summarizing.gguf
# - complaint_summarizing_model.gguf
# - BNS-RAG-q4k.gguf

# Check RAG database
ls -lh "rag db/"
# Should show:
# - BNS_basic_chroma.jsonl
# - BNS_details_chroma.jsonl
# - BNS_spacts_chroma.jsonl

# Check general retrieval
ls -lh "general retrieval db/"
# Should show:
# - BNS_basic.jsonl
# - BNS_indepth.jsonl
# - spacts.jsonl

# Check environment
cat .env
# Should show all configuration variables
```

## Security Notes

- The `setup-env.sh` script generates cryptographically secure random keys
- Never commit the generated `.env` file to version control
- Keep your `.env` file secure and backed up
- Rotate keys periodically in production

## Performance Tips

1. **Parallel Downloads**: Run model and KB downloads in parallel:
   ```bash
   ./download-models.sh &
   ./download-knowledge-base.sh &
   wait
   ```

2. **Resume Downloads**: If a download fails, just run the script again. HuggingFace CLI will resume.

3. **Cache Location**: Models are cached in `~/.cache/huggingface/`. Delete to force re-download:
   ```bash
   rm -rf ~/.cache/huggingface/
   ```

## License

These scripts are part of the AFIRGen project. See the main repository for license information.

## Support

For issues or questions:
1. Check the main deployment guide: [AWS-DEPLOYMENT-PLAN.md](../../AWS-DEPLOYMENT-PLAN.md)
2. Review HuggingFace documentation: https://huggingface.co/docs
3. Check script output for error messages
