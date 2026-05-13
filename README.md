# WebLift - AI-Powered SEO Platform

[![Django](https://img.shields.io/badge/Django-4.2+-092E20?style=flat&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**WebLift** is a comprehensive SEO (Search Engine Optimization) platform featuring AI-powered keyword research, content analysis, and competitor comparison tools. It combines traditional SEO auditing with modern machine learning and LLM-based keyword suggestion systems.

---

## 🎯 What Is This Project?

WebLift helps website owners and SEO professionals:

- **🔍 Analyze** website technical health and SEO metrics
- **🤖 Discover** high-value keywords using AI and ML models
- **📊 Compare** performance against competitors
- **📈 Optimize** content with data-driven suggestions
- **🎓 Learn** from continuous feedback and model improvements

---

## ✨ Features

### Core SEO Analysis
- Website crawler and technical audit
- Meta tag analysis (title, description, headers)
- Page speed insights (Google PageSpeed API)
- Mobile-friendliness testing
- Backlink analysis (Moz API integration)
- Readability scoring

### AI-Powered Keyword Research
- **6 Keyword Discovery Methods:**
  | Method | Description |
  |--------|-------------|
  | **TF-IDF** | Statistical word importance analysis |
  | **KeyBERT** | AI-based key phrase extraction |
  | **Similarity** | Semantic keyword expansion |
  | **ML Generation** | Neural network keyword suggestions |
  | **Semantic** | Conceptually related terms |
  | **LLM Enhancement** | GPT-powered expert suggestions |

- **Intelligent Scoring:** 50% relevance + 25% difficulty + 25% competition gap
- **Search Intent Classification:** Informational, navigational, transactional, commercial
- **SERP Feature Prediction:** Featured snippets, knowledge panels, etc.

### Advanced Capabilities
- **RAG (Retrieval-Augmented Generation):** Uses pgvector for semantic similarity search
- **Async Processing:** Celery-based background task processing
- **Batch Analysis:** Process multiple URLs simultaneously
- **Continuous Learning:** Model improvement from user feedback
- **Content Optimization:** AI-generated improvement suggestions

---

## 🏗️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Django 4.2+ |
| **Database** | PostgreSQL with pgvector extension |
| **Task Queue** | Celery + Redis |
| **ML/Embeddings** | sentence-transformers (all-MiniLM-L6-v2), PyTorch |
| **Vector Search** | FAISS (CPU/GPU) |
| **LLM APIs** | OpenAI, OpenRouter, Groq |
| **NLP** | KeyBERT, spaCy, scikit-learn |
| **Frontend** | Django Templates + Custom CSS/JS |

---

## 📁 Project Structure

```
WebLift/
│
├── Project/                    # Django project configuration
│   ├── settings.py            # Main settings (DB, APIs, Celery)
│   ├── urls.py                # Root URL configuration
│   ├── celery.py              # Celery task broker setup
│   └── wsgi.py / asgi.py      # WSGI/ASGI entry points
│
├── SEOAnalyzer/               # Main web application
│   ├── views.py               # Web views (dashboard, tools, auth)
│   ├── models.py              # User profiles
│   ├── templates/             # HTML templates (20+)
│   ├── static/                # CSS, JS, images
│   └── services/              # SEO analysis services
│
├── keyword_ai/                # AI keyword research system
│   ├── pipeline_v2.py        # Main 18-step analysis pipeline
│   ├── views.py               # REST API endpoints
│   ├── models.py              # Database models (ContentAnalysis, etc.)
│   ├── tasks.py               # Celery async tasks
│   ├── ml_models/             # ML model implementations
│   │   ├── relevance_scorer_v2.py
│   │   ├── semantic_mapper.py
│   │   └── faiss_index.bin    # Vector search index
│   └── services/              # 14+ analysis services
│
├── comparative_analysis/      # Competitor analysis tools
│   ├── models.py              # Comparison reports
│   └── services/              # Data extraction, authority analysis
│
├── logs/                      # Application logs
├── requirements.txt           # Python dependencies
└── manage.py                  # Django management script
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ with pgvector extension
- Redis (for Celery)

### Step 1: Clone and Setup Environment

```bash
# Navigate to project directory
cd e:\Project

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Setup

```bash
# Create PostgreSQL database
createdb keywordai_db

# Enable pgvector extension (run in psql)
CREATE EXTENSION IF NOT EXISTS vector;

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 3: Environment Configuration

Create a `.env` file in the project root:

```env
# Required
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DATABASE_URL=postgresql://postgres:admin123@localhost:5432/keywordai_db

# AI API Keys (at least one required for AI features)
OPENAI_API_KEY=your-openai-key
# OR
GROQ_API_KEY=your-groq-key
USE_GROQ=true

# Optional: SEO APIs
MOZ_ACCESS_ID=your-moz-id
MOZ_SECRET_KEY=your-moz-secret
PAGESPEED_API_KEY=your-google-api-key

# Celery
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

### Step 4: Start Services

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
celery -A Project worker -l info

# Terminal 3: Start Django Server
python manage.py runserver
```

Access the application at: **http://127.0.0.1:8000/**

---

## 📚 API Documentation

### Main Endpoints

#### Analyze URL (Synchronous)
```http
POST /api/keywords/v2/
Content-Type: application/json

{
  "url": "https://example.com/blog-post",
  "page_topic": "machine learning",
  "use_llm": true,
  "use_advanced_ai": true,
  "analyze_competitors": false
}
```

#### Analyze URL (Asynchronous)
```http
POST /api/keywords/analyze-async/
Content-Type: application/json

{
  "url": "https://example.com",
  "page_topic": "topic"
}

# Returns: {"task_id": "uuid", "status": "pending"}

# Check status:
GET /api/keywords/task-status/?task_id=uuid
```

#### Batch Analysis
```http
POST /api/keywords/analyze-batch/
Content-Type: application/json

{
  "urls": [
    "https://example.com/page1",
    "https://example.com/page2"
  ],
  "page_topic": "topic"
}
```

#### Submit Feedback
```http
POST /api/keywords/feedback/
Content-Type: application/json

{
  "opportunity_id": 123,
  "action": "accepted",
  "rating": 5,
  "comment": "Great suggestion!"
}
```

### Response Format

```json
{
  "url": "https://example.com",
  "page_title": "Example Page",
  "relevant_keywords": ["kw1", "kw2", "kw3"],
  "scored_keywords": [
    {
      "keyword": "machine learning tutorial",
      "relevance_score": 85.5,
      "difficulty_score": 40,
      "is_relevant": true
    }
  ],
  "focus_keywords": ["top5", "keywords"],
  "intent_groups": {
    "Informational": ["how to...", "what is..."],
    "Transactional": ["buy...", "best..."]
  },
  "content_analysis": {
    "quality_score": 75,
    "word_count": 1200,
    "readability": {
      "ease_score": 65,
      "grade_level": 10
    }
  },
  "ml_generated_suggestions": [...],
  "semantic_keywords": [...],
  "rag_enabled": true,
  "pipeline_version": "2.1"
}
```

---

## 🤖 Machine Learning Components

### 1. Text Embeddings (all-MiniLM-L6-v2)
- Converts text to 384-dimensional vectors
- Enables semantic similarity comparison
- Used for RAG retrieval and keyword matching

### 2. FAISS Vector Search
- Fast approximate nearest neighbor search
- Millisecond-level keyword similarity lookup
- Supports both CPU and GPU backends

### 3. ML Relevance Scorer
Features analyzed (11 total):
1. Content semantic similarity
2. Keyword length and word count
3. Presence of numbers
4. Special characters
5. Question format detection
6. Power words ("best", "guide", "ultimate")
7. Title case ratio
8. Search intent classification

Scoring formula:
```
Final Score = 
  50% × Content Similarity +
  25% × (100 - Difficulty) +
  25% × Competition Gap
```

### 4. Continuous Learning Pipeline
```
User Feedback → Store in DB → Periodic Retraining → Model Update
```

---

## 📊 Database Models

### Core Models

| Model | Purpose |
|-------|---------|
| **ContentAnalysis** | Stores analyzed URLs with content metrics, embeddings |
| **KeywordOpportunity** | Individual keyword suggestions with scores |
| **SuggestionFeedback** | User acceptance/rejection data for learning |
| **AnalysisTask** | Async task tracking (progress, status, results) |
| **ModelPerformance** | ML model metrics and acceptance rates |

### Key Fields

**ContentAnalysis:**
- `url` (indexed, unique)
- `quality_score` (0-100)
- `embedding` (pgvector, 384 dimensions)
- `tfidf_keywords` (JSON)
- `structure_data` (JSON)

**KeywordOpportunity:**
- `keyword` (indexed)
- `relevance_score`, `difficulty_score`
- `search_intent` (enum: informational, navigational, transactional, commercial)
- `ai_reasoning`, `suggested_action`
- `is_accepted`, `is_rejected` (user feedback)

---

## 🔧 Configuration Options

### AI Provider Selection
```python
# settings.py - Priority order:
1. GROQ (free tier available)
2. OpenRouter (aggregated APIs)
3. OpenAI (GPT-4, GPT-4o-mini)
```

### Pipeline Features
```python
run_keyword_pipeline_v2(
    url="https://example.com",
    use_llm=True,              # LLM keyword refinement
    use_advanced_ai=True,      # ML generation + semantic search
    analyze_competitors=True,  # Competitor gap analysis
    generate_optimization=True # Content optimization tips
)
```

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Import errors" | `pip install -r requirements.txt` |
| "Database errors" | `python manage.py migrate` |
| "pgvector not found" | `CREATE EXTENSION vector;` in psql |
| "Celery not working" | Start Redis: `redis-server` |
| "0 keywords found" | Check content length > 50 chars |
| "API rate limits" | Set up API keys in `.env` |

### Logs
Check `logs/django.log` for detailed error information.

---

## 📈 Project Stats

- **Total Files:** 100+
- **Lines of Code:** ~15,000+
- **Database Models:** 15+
- **API Endpoints:** 20+
- **ML Models:** 3
- **Analysis Services:** 20+
- **Templates:** 20+

---

## 🗺️ Roadmap

- [ ] User dashboard with analytics
- [ ] Export reports (PDF, CSV)
- [ ] Chrome extension
- [ ] Multi-language support
- [ ] A/B testing for suggestions
- [ ] Integration with Google Search Console

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and test
4. Submit a pull request

---

## 📄 License

This project is licensed under the MIT License.

---

## 📞 Support

- **Documentation:** See `README_FIRST.md` for detailed guides
- **Code Issues:** Check logs in `logs/django.log`
- **API Questions:** Review `keyword_ai/views.py` for endpoint details

---

**Built with ❤️ using Django, PyTorch, and AI magic.**
