

[![Django](https://img.shields.io/badge/Django-4.2+-092E20?style=flat&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Single source of truth** — this file replaces `README_FIRST.md`, `PROJECT_OVERVIEW.md`, `PINECONE_SETUP.md`, `SUBSCRIPTION_SETUP.md`, and `TEST_ENVIRONMENT_README.md`.

**WebLift** is a comprehensive SEO platform featuring AI-powered keyword research, content analysis, competitor comparison, and subscription-based access control. It combines traditional SEO auditing with modern ML and LLM-based keyword suggestion systems.

---

## 🎯 What Is This Project?

WebLift helps website owners and SEO professionals:

- **🔍 Analyze** website technical health and SEO metrics
- **🤖 Discover** high-value keywords using AI and ML models
- **📊 Compare** performance against competitors
- **📈 Optimize** content with data-driven suggestions
- **💳 Subscribe** via manual bank transfer for premium features

---

## ✨ Features

### Core SEO Analysis
- Website crawler and full technical audit
- Meta tag analysis (title, description, headings)
- Page speed insights (Google PageSpeed API)
- Mobile-friendliness, SSL, robots.txt, sitemap checks
- Backlink & domain authority analysis (Moz API)
- Grammar, readability, E-E-A-T scoring

### AI-Powered Keyword Research
- **6 Keyword Discovery Methods:**

  | Method | Description |
  |--------|-------------|
  | **TF-IDF** | Statistical word importance analysis |
  | **KeyBERT** | AI-based key phrase extraction |
  | **Similarity** | Semantic keyword expansion |
  | **ML Generation** | Neural network keyword suggestions |
  | **Semantic** | Conceptually related terms |
  | **LLM Enhancement** | Groq/OpenRouter/OpenAI-powered suggestions |

- **Intelligent Scoring:** 50% relevance + 25% difficulty + 25% competition gap
- **Search Intent Classification:** Informational, navigational, transactional, commercial

### Subscription System
- Free tier: 1 audit
- Basic / Pro / Enterprise tiers with monthly limits
- Manual bank transfer payments — admin verifies and activates
- Usage tracking per billing period

### Competitor Analysis
- Side-by-side URL comparison
- Authority, gap, and semantic analysis
- AI-generated competitive insights

---

## 🏗️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Django 4.2+ |
| **Database** | SQLite (file-based, zero config) |
| **Vector Search** | Pinecone (cloud, optional) |
| **Task Queue** | Celery (in-memory broker by default) |
| **ML/Embeddings** | sentence-transformers (all-MiniLM-L6-v2), PyTorch |
| **LLM APIs** | Groq (free), OpenRouter, OpenAI |
| **SEO APIs** | Moz API, Google PageSpeed Insights |
| **Frontend** | Django Templates + Custom CSS/JS |

---

## 📁 Project Structure

```
WebLift/
│
├── Project/                    # Django project configuration
│   ├── settings.py            # Main settings
│   ├── urls.py                # Root URL configuration
│   ├── celery.py              # Celery task setup
│   └── wsgi.py / asgi.py      # WSGI/ASGI entry points
│
├── SEOAnalyzer/               # Core SEO audit app
│   ├── views.py               # Audit orchestrator
│   ├── views_original.py      # Full audit implementation
│   ├── views_pages.py         # Page views (show, report, etc.)
│   ├── models.py              # User profiles
│   ├── templates/             # HTML templates
│   ├── static/                # CSS, JS, images
│   └── services/              # Analysis services (EEAT, grammar, links, etc.)
│
├── keyword_ai/                # AI keyword research system
│   ├── pipeline_v2.py        # Main analysis pipeline
│   ├── views.py               # API endpoints
│   ├── models.py              # ContentAnalysis, KeywordOpportunity, etc.
│   ├── tasks.py               # Celery async tasks
│   ├── ml_models/             # ML model implementations
│   └── services/              # Pinecone, RAG, embeddings, etc.
│
├── comparative_analysis/      # Competitor analysis
│   ├── models.py              # Comparison reports
│   └── services/              # Data extraction, authority, gap analysis
│
├── subscriptions/             # Subscription & billing
│   ├── models.py              # SubscriptionTier, Subscription, UsageTracker
│   ├── decorators.py          # @track_usage, @require_feature
│   └── services/              # SubscriptionService
│
├── logs/                      # Application logs (django.log)
├── requirements.txt           # Python dependencies
└── manage.py                  # Django management script
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- No database server required (SQLite is file-based)

### Step 1: Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Environment Configuration

Create a `.env` file in the project root:

```env
# Required
DJANGO_SECRET_KEY=your-secret-key-here-at-least-50-chars
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI API — Groq is free and recommended
USE_GROQ=true
GROQ_API_KEY=your-groq-key

# Optional: OpenRouter fallback
USE_OPENROUTER=false
OPENROUTER_API_KEY=

# Optional: SEO APIs
USE_MOZ_API=false
MOZ_ACCESS_ID=
MOZ_SECRET_KEY=
PAGESPEED_API_KEY=

# Optional: Pinecone vector search
USE_PINECONE=false
PINECONE_API_KEY=

# Email (for reports)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

### Step 3: Database & Static Files

```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Create default subscription tiers
python manage.py shell -c "from subscriptions.services.subscription_service import SubscriptionService; SubscriptionService.create_default_tiers()"
```

### Step 4: Run the Server

```bash
python manage.py runserver
```

Access the application at: **http://127.0.0.1:8000/**

> **No Redis or separate Celery worker needed for development.** Celery tasks run inline automatically when no broker is available.

---

## 📚 API Endpoints

### Keyword Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/keywords/v2/` | Synchronous keyword analysis |
| `POST` | `/api/keywords/analyze-async/` | Async analysis (returns task_id) |
| `GET` | `/api/keywords/task-status/?task_id=` | Check async task status |
| `POST` | `/api/keywords/analyze-batch/` | Batch URL analysis |
| `POST` | `/api/keywords/feedback/` | Submit keyword feedback |

### SEO Audit

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/show/` | Run full SEO audit |
| `POST` | `/report/` | Generate email report |
| `GET` | `/comparative-analysis/` | Competitor analysis |

---

## 🔧 Configuration

### AI Provider Priority
```
1. Groq      — free, fast (recommended)
2. OpenRouter — aggregated APIs
3. OpenAI    — GPT-4o-mini
```

Set `USE_GROQ=true` and add `GROQ_API_KEY` in `.env` to use Groq.

### Subscription Tiers

| Tier | Audits/month | Features |
|------|-------------|----------|
| Free | 1 (one-time) | Basic audit |
| Basic | 10 | + AI suggestions, PDF export |
| Pro | 50 | + Competitor analysis, API access |
| Enterprise | Unlimited | All features + priority support |

Payment is via manual bank transfer. Admin activates subscription after verifying payment at `/admin/`.

### Pinecone (Optional)
Set `USE_PINECONE=true` and `PINECONE_API_KEY` to enable cloud vector search for RAG keyword retrieval. Without it, the system falls back gracefully.

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | `pip install -r requirements.txt` |
| Database errors | `python manage.py migrate` |
| No audit results | Check `logs/django.log` for fetch errors |
| 0 keywords found | Ensure page content is > 50 characters |
| AI features not working | Set `GROQ_API_KEY` in `.env` |
| Subscription not enforced | Run `python manage.py migrate` |

Logs: `logs/django.log`

---

## 📊 Database Models

| Model | App | Purpose |
|-------|-----|---------|
| `Profile` | SEOAnalyzer | Extended user profile |
| `ContentAnalysis` | keyword_ai | Analyzed URLs with embeddings |
| `KeywordOpportunity` | keyword_ai | Keyword suggestions with scores |
| `SuggestionFeedback` | keyword_ai | User feedback for model learning |
| `AnalysisTask` | keyword_ai | Async task tracking |
| `ComparisonReport` | comparative_analysis | Competitor comparison results |
| `SubscriptionTier` | subscriptions | Plan definitions and limits |
| `Subscription` | subscriptions | User's active plan |
| `UsageTracker` | subscriptions | Monthly usage counters |
| `ManualPaymentSubmission` | subscriptions | Bank transfer payment records |

---

## 📄 License

This project is licensed under the MIT License.

---

**Built with Django, PyTorch, and Groq.**

---

## 🏛️ Architecture Overview

### Cross-App Integration

```
SEOAnalyzer (Core)
  views_pages.py
    show()  ←── @track_usage('audit')
      └── WebsiteAuditOrchestrator ──► 8 service modules
            └── home.html (results)
                  ├── /report/download/ ──► @require_feature('pdf_export')
                  └── report_orchestrator.py ◄── keyword_ai + Moz API
                                └── generate_seo_report() ──► PDF

subscriptions            keyword_ai                comparative_analysis
  UsageTracker             pipeline_v2.py             ComparisonOrchestrator
  Subscription               KeyBERT / TF-IDF           DataExtractor
  @decorators                Groq LLM / RAG             SemanticAnalyzer
                             ContentAnalysis (DB)        TechnicalAnalyzer
                             KeywordOpportunity          GapAnalyzer ──► Groq LLM
```

### Auth & Audit Flow

```
/register/ → User + Profile created → signal auto-creates Subscription + UsageTracker (free tier)
/home/     → index view (login required)
/show/     → @track_usage('audit') → WebsiteAuditOrchestrator → results on home.html
```

### Key Code Notes

- `views.py` — contains only `WebsiteAuditOrchestrator` class (no view functions)
- `views_pages.py` — all actual Django view functions; imported by `Project/urls.py`
- `views_pages.py` imports `Website_Audit` from `views_original.py` (the full battle-tested implementation)
- `subscriptions/decorators/` package re-exports everything from `decorators_impl.py` — always import from `subscriptions.decorators`
- `AsyncHTTPClient` uses lazy init — connector created only on first call to avoid event-loop errors at startup
- `Subscription` has `stripe_customer_id` / `stripe_subscription_id` fields reserved for future use — not active
- `comparative_analysis` views do **not** currently enforce `@require_feature('competitor_analysis')` — decorator exists but is not wired
- `pgvector` (`VectorField`) requires PostgreSQL — use `USE_PINECONE=true` with `USE_SQLITE=true`

---

## 🗄️ Database Models Reference

### SEOAnalyzer
| Model | Fields | Purpose |
|-------|--------|---------|
| `Profile` | user, forget_password_token, created_at | Password reset |

### subscriptions
| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `SubscriptionTier` | name, price_monthly, max_audits_per_month, feature flags | Plan definitions |
| `Subscription` | user(1:1), tier, status, current_period_end | Active user plan |
| `UsageTracker` | user(1:1), audits_used_this_month, free_audit_used | Monthly counter |
| `ManualPaymentSubmission` | user, tier, amount, status, proof_document | Bank transfer proofs |
| `PaymentRecord` | user, amount, status | Payment history |
| `FeatureAccessLog` | user, feature_name, access_granted | Access audit trail |

### keyword_ai
| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `ContentAnalysis` | url, embedding(384d), tfidf_keywords, quality_score | Analyzed URL data + vectors |
| `KeywordOpportunity` | keyword, relevance_score, intent, ai_reasoning | Keyword suggestions |
| `SuggestionFeedback` | opportunity, user_action, rating | User feedback for ML |
| `AnalysisTask` | status, result, created_at | Async task tracking |
| `GapAnalysis` | user_content, competitor_data | Competitor gap data |

### comparative_analysis
| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `ComparisonReport` | url_primary, url_competitor, scores_*, gap_summary, ranking_explanation | Comparison results |

---

## 🔌 Full URL Reference

### SEOAnalyzer (`/`)
| URL | View | Auth | Subscription |
|-----|------|------|-------------|
| `/` | `loginuser` | No | No |
| `/register/` | `register` | No | No |
| `/home/` | `index` | Yes | No |
| `/show/` | `show` | Yes | `@track_usage('audit')` |
| `/report/` | `Report` | Yes | No |
| `/report/download/` | `download_report` | Yes | `@require_feature('pdf_export')` |
| `/seo-metrics/` | `seo_metrics` | Yes | No |
| `/mobiletest/` | `mobiletest` | Yes | No |
| `/robot/` | `robot` | Yes | No |
| `/keyPosition/` | `keyPosition` | Yes | No |
| `/keysuggestion/` | `keysuggestion` | Yes | No |
| `/keyword-ai-suggestions/` | `keyword_ai_suggestions` | Yes | No |
| `/sentimentanalysis/` | `sentiment_analysis_page` | No | No |
| `/sentimentanalysis/analyze/` | `analyze_sentiment_view` | No | No |

### Subscriptions (`/subscriptions/`)
| URL | Purpose | Staff Only |
|-----|---------|-----------|
| `pricing/` | View all plans | No |
| `dashboard/` | User subscription dashboard | No |
| `payment/instructions/` | Bank transfer details | No |
| `payment/submit/` | Submit payment proof | No |
| `cancel/` | Cancel subscription | No |
| `api/usage/` | AJAX usage data | No |
| `admin/pending-payments/` | Verify/reject payments | Yes |
| `admin/verify-payment/<id>/` | Verify a payment | Yes |
| `admin/reject-payment/<id>/` | Reject a payment | Yes |

### Keyword AI (`/api/keywords/`)
| URL | Method | Subscription |
|-----|--------|-------------|
| `suggest/` | POST | `@api_subscription_check` |
| `feedback/` | POST | `@api_subscription_check` |
| `tasks/` | GET | `@api_subscription_check` |
| `tasks/<id>/` | GET | `@api_subscription_check` |
| `export/csv/` | GET | `@api_subscription_check` |
| `export/json/` | GET | `@api_subscription_check` |
| `history/` | GET | `@api_subscription_check` |
| `batch/` | POST | `@api_subscription_check` |

### Comparative Analysis (`/comparative-analysis/`)
| URL | Method | Purpose |
|-----|--------|---------|
| (root) | GET | Input form |
| `analyze/` | POST | Run comparison |
| `results/<id>/` | GET | View results |

---

## 💳 Subscription System

### Tiers

| Tier | Price/mo | Audits/mo | Keywords | PDF | AI | Competitors |
|------|---------|-----------|---------|-----|----|------------|
| Free | $0 | 1 (trial) | 20 | No | No | 0 |
| Basic | $9 | 10 | 50 | Yes | Yes | 0 |
| Pro | $29 | 50 | 200 | Yes | Yes | 3 |
| Enterprise | $99 | Unlimited | 500 | Yes | Yes | 10 |

### Decorators

```python
from subscriptions.decorators import track_usage, require_feature, api_subscription_check

@track_usage('audit')           # SEO audit views
@track_usage('keywords', count=50)  # keyword views
@require_feature('pdf_export')  # PDF download
@require_feature('competitor_analysis')  # Pro+ only
@api_subscription_check         # JSON API endpoints — returns 403 instead of redirect
```

### Manual Bank Transfer Payment Flow

```
1. User → /subscriptions/pricing/ → selects paid plan
2. /subscriptions/payment/instructions/ → shown bank details + unique ref code
3. User transfers money at their bank
4. /subscriptions/payment/submit/ → uploads proof (screenshot/receipt)
5. Admin → /subscriptions/admin/pending-payments/ → verifies transfer
6. POST /subscriptions/admin/verify-payment/<id>/ → subscription activates
```

### Bank Details (.env)

```env
BANK_NAME="Your Bank Name"
BANK_ACCOUNT_NAME="WebLift"
BANK_ACCOUNT_NUMBER="1234-5678-9012-3456"
BANK_IBAN="PK00XXXX0000000000000000"
BANK_SWIFT="XXXXXPKK"
BANK_BRANCH="Main Branch"
BANK_COUNTRY="Pakistan"
FREE_TRIAL_AUDITS=1
```

### Monthly Usage Reset

```bash
# Cron: 1st of every month at midnight
0 0 1 * * cd /path/to/project && python manage.py reset_monthly_usage
```

---

## 🤖 AI Keyword Pipeline (pipeline_v2.py)

```
Input: URL + optional target keyword

Phase 1 — Content Analysis
  extract_content(url)       → raw HTML fetch, text extraction
  analyze_content(text)      → TF-IDF, readability, entities
  get_single_embedding(text) → 384-dim vector (all-MiniLM-L6-v2)
  save_content_analysis()    → persist to ContentAnalysis model

Phase 2 — ML Scoring
  extract_keywords(text)     → KeyBERT extraction
  score_keywords_v2()        → RelevanceScorerV2 ML scoring
  predict_search_intent()    → intent classification
  expand_keywords()          → FAISS similarity expansion

Phase 3 — LLM Refinement (Groq/OpenAI)
  expand_keywords_with_llm() → LLM keyword variants
  refine_keywords()          → LLM filtering and ranking
  get_keyword_clusters_with_llm() → topic clusters
  analyze_content_optimization()  → gap suggestions

RAG Enhancement
  retrieve_similar_analyses() → past analyses via embeddings
  format_rag_context()        → formats as LLM context

Output: List of KeywordOpportunity objects + content optimization report
```

### Scoring Formula

```
Final Score = 50% × AI relevance + 25% × (100 - difficulty) + 25% × gap opportunity
```

### ML Training

```bash
# Train relevance scorer once
python keyword_ai/train_model.py

# Retrain from user feedback (management command)
python manage.py retrain_models
python manage.py retrain_models --model relevance_scorer_v2 --dry-run
```

---

## 📦 Vector Storage (Pinecone)

### Options

| Setup | Relational DB | Vector DB | Best For |
|-------|--------------|-----------|----------|
| SQLite + Pinecone | SQLite | Pinecone | Development |
| PostgreSQL + Pinecone | PostgreSQL | Pinecone | Production |
| PostgreSQL + pgvector | PostgreSQL | PostgreSQL | Simple/legacy |

### Pinecone Setup (.env)

```env
USE_PINECONE=true
PINECONE_API_KEY=pc_your_key_here
PINECONE_INDEX_NAME=keyword-ai-vectors
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
```

### Pinecone Management Commands

```bash
python manage.py sync_pinecone --test-connection
python manage.py sync_pinecone --create-index
python manage.py sync_pinecone --sync-all
python manage.py sync_pinecone --stats
python manage.py sync_pinecone --test-search "https://your-domain.com/page"
```

---

## ⚡ Caching Strategy

| Key Pattern | TTL | What's Cached |
|------------|-----|--------------|
| `audit_results_{md5(url)}` | 1 hour | Full SEO audit result dict |
| `comprehensive_report_{md5(url)}` | 24 hours | Report orchestrator data |
| `http_cache:{hash(url)}` | 5 min | Raw HTTP responses |
| Pricing page (`@cache_page`) | 30 min | Rendered pricing HTML |

Cache backends: `LocMemCache` (default/dev), Redis (`USE_REDIS_CACHE=true` for production).

---

## 🔄 Background Tasks (Celery)

```bash
# Worker
celery -A Project worker --loglevel=info

# Beat scheduler (periodic tasks)
celery -A Project beat --loglevel=info
```

| Task | Schedule | Purpose |
|------|----------|---------|
| `keyword_ai.tasks.cleanup_old_tasks` | Daily at 3 AM | Remove old AnalysisTask records |

Async tasks: `start_single_url_analysis(url)`, `start_batch_analysis(urls)` — results polled via `/api/keywords/tasks/<id>/`.

> No Redis or separate worker needed in development — Celery tasks run inline automatically.

---

## 🧪 Testing

### Quick Start

```bash
python setup_test_env.py   # one-time setup
python run_tests.py        # run all tests
python run_tests.py --coverage
```

### Test Commands

```bash
python run_tests.py --seo           # SEOAnalyzer tests
python run_tests.py --keyword       # keyword_ai tests
python run_tests.py --comparative   # comparative_analysis tests
python run_tests.py --subscription  # subscriptions tests
python run_tests.py --unit          # unit tests only
python run_tests.py --integration   # integration tests only
python run_tests.py --e2e           # end-to-end tests
python run_tests.py --parallel 4    # parallel execution
python run_tests.py --failfast      # stop on first failure
```

### pytest Markers

| Marker | Description |
|--------|-------------|
| `unit` | Fast, isolated unit tests |
| `integration` | Tests with DB |
| `e2e` | End-to-end tests |
| `slow` | Tests taking >5s |
| `seo` / `keyword` / `comparative` / `subscription` | Module-specific |

### Test Settings

- **Settings module**: `Project.settings_test`
- **Database**: SQLite in-memory
- **Celery**: Always eager (synchronous)
- **Email**: Console backend
- **Password hashers**: MD5 (fast)

### Available Fixtures (conftest.py)

- **Users**: `test_user`, `admin_user`, `another_user`
- **Subscriptions**: `subscription_tiers`, `free_subscription`, `basic_subscription`, `pro_subscription`
- **keyword_ai**: `sample_content_analysis`, `sample_keyword_opportunities`, `sample_analysis_task`
- **Mocks**: `mock_groq`, `mock_openai`, `mock_moz_api`, `mock_pinecone`, `mock_celery_task`
- **Clients**: `authenticated_client`, `admin_client`

### Coverage

```bash
pytest --cov=. --cov-report=term-missing   # terminal
pytest --cov=. --cov-report=html           # htmlcov/index.html
pytest --cov=. --cov-report=xml            # coverage.xml (CI)
```

### CI/CD (GitHub Actions)

```yaml
- run: pip install -r requirements.txt -r requirements-test.txt
- run: python setup_test_env.py
- run: python run_tests.py --coverage
```

---

## 🛠️ Admin Panel

Access at `/admin/` with a superuser account.

- **SubscriptionTier** — Edit plan limits, prices, feature flags
- **Subscription** — View/edit any user's active subscription
- **UsageTracker** — View and manually reset monthly usage
- **ManualPaymentSubmission** — Bulk verify/reject with action buttons
- **FeatureAccessLog** — Debug access denials

### Bulk Payment Actions
Select rows in ManualPaymentSubmission admin:
- **"Verify selected payments and activate subscriptions"**
- **"Reject selected payments"**

---

*Last updated: May 2026*
