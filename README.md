# Medical PDF Analyzer

This tool uses Claude AI to analyze medical PDF documents and extract important information like circled or highlighted fields.

## Setup

1. **Install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install anthropic
   ```

2. **Add your API key:**
   - Edit `config.py`
   - Replace `"your-api-key-here"` with your actual Anthropic API key
   - Get your API key from: https://console.anthropic.com/

3. **Update the PDF path:**
   - Edit `docs.py`
   - Change the `pdf_path` variable to point to your PDF file

## Usage

```bash
cd medical-pdf-analyzer
source venv/bin/activate
python docs.py
```

## Files

- `docs.py` - Main script that analyzes the PDF
- `config.py` - Configuration file for API key
- `venv/` - Python virtual environment (created after setup)

## Notes

- Uses Claude Sonnet model for analysis
- Supports PDF documents up to reasonable sizes
- Extracts patient information, highlighted items, and medical findings
- Output includes comprehensive document summary