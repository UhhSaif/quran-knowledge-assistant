# Setup Instructions

## Step-by-Step Setup Guide

### 1. Get a Quran PDF

You need an English translation of the Quran in PDF format. Here are some recommended sources:

#### Option A: Download from Quran.com
1. Visit https://quran.com
2. Navigate to their downloads section
3. Download an English translation (e.g., "The Clear Quran" by Dr. Mustafa Khattab)

#### Option B: Use a Free Translation
Several free English translations are available:
- **Sahih International**: https://www.islamicbulletin.org/
- **Yusuf Ali Translation**: Available on archive.org
- **Muhammad Asad Translation**: Available on various Islamic sites

#### Option C: Create Your Own (Advanced)
You can use the Quran API to generate a PDF:
```python
# Example script to download Quran text
import requests

response = requests.get("https://api.quran.com/api/v4/chapters")
# Process and save as PDF
```

**Important**: Place the PDF file in the `knowledge_base/` directory with a clear name like `quran_english.pdf`

### 2. Set Up Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Google Cloud (required)
GOOGLE_CLOUD_PROJECT=your-project-id-here
GOOGLE_CLOUD_LOCATION=us-central1

# For local development with API key
GOOGLE_GENAI_API_KEY=your-api-key-here

# OR for Vertex AI (recommended for production)
GOOGLE_GENAI_USE_VERTEXAI=true

# Tavily API (required) - Get from https://tavily.com
TAVILY_API_KEY=tvly-xxxxxxxxxxxxx
```

### 3. Get Required API Keys

#### Google GenAI API Key
1. Go to https://aistudio.google.com/app/apikey
2. Create a new API key
3. Copy it to `GOOGLE_GENAI_API_KEY` in your `.env` file

**OR**

#### Google Cloud Vertex AI (for production)
1. Create a Google Cloud Project
2. Enable Vertex AI API:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```
3. Set up authentication:
   ```bash
   gcloud auth application-default login
   ```
4. Set `GOOGLE_GENAI_USE_VERTEXAI=true` in your `.env`

#### Tavily API Key
1. Visit https://tavily.com
2. Sign up for a free account
3. Copy your API key from the dashboard
4. Add it to `TAVILY_API_KEY` in your `.env` file

### 4. Install Dependencies

Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install requirements:
```bash
pip install -r requirements.txt
```

### 5. Verify Setup

Check that everything is configured:
```bash
# Verify environment variables
cat .env

# Check knowledge base
ls knowledge_base/

# Should show your PDF file
```

### 6. Run the Application

Start the server:
```bash
uvicorn src.main:app --reload --port 8080
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

The system will automatically:
- Index the PDF in the background
- Create FAISS vector store
- Initialize all agents

### 7. Test the System

In a new terminal, run the test script:
```bash
python test_api.py
```

Or test manually:
```bash
# Health check
curl http://localhost:8080/health

# Chat
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the Quran say about patience?"}'
```

## Troubleshooting

### Issue: "No PDF files found in knowledge base"
**Solution**: Make sure you have placed a PDF file in the `knowledge_base/` directory.

### Issue: "GOOGLE_GENAI_API_KEY must be set"
**Solution**: Check that your `.env` file exists and contains the API key, and that you're running from the project root.

### Issue: "TAVILY_API_KEY environment variable must be set"
**Solution**: Sign up at tavily.com and add your API key to `.env`.

### Issue: ImportError for google.genai
**Solution**: Make sure you installed requirements correctly:
```bash
pip install google-genai>=0.3.0
```

### Issue: Vector store not ready
**Solution**: Wait 30-60 seconds for background ingestion to complete. Check logs for processing status.

## Next Steps

1. ✅ Place Quran PDF in `knowledge_base/`
2. ✅ Configure `.env` with API keys
3. ✅ Install dependencies
4. ✅ Run the application
5. ✅ Test with sample queries
6. ✅ Deploy to Cloud Run (optional)

## Sample Queries to Try

Once running, try these queries:

1. **Verse Search**:
   - "What does the Quran say about patience?"
   - "Find verses about Prophet Moses"
   - "Show me references to charity"

2. **Context Questions**:
   - "What's the historical context of Surah Al-Kahf?"
   - "When was Surah Al-Fatiha revealed?"

3. **Interpretation**:
   - "What is the meaning of Ayat al-Kursi?"
   - "Explain Surah Al-Ikhlas"

## Project Structure

```
SynapseAI_QuranProject/
├── knowledge_base/          # ← Put your Quran PDF here
├── index/                   # ← Auto-generated FAISS index
├── src/                     # Source code
├── deployment/              # Cloud Run configs
├── .env                     # ← Your API keys (create from .env.example)
├── requirements.txt
└── test_api.py
```

## Support

- Check logs for detailed error messages
- All logs are in structured JSON format
- Review README.md for architecture details
