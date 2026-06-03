# WebLift SEO Platform — Test Suite

Comprehensive test coverage across all 4 Django apps.

## Folder Structure

```
tests/
├── conftest.py              # Shared fixtures (users, subscriptions, mocks, HTML samples)
├── pytest.ini               # Pytest configuration
├── README.md                # This file
│
├── unit/                    # Pure unit tests — no network, minimal DB
│   ├── test_subscription_models.py   # SubscriptionTier, Subscription, UsageTracker, ManualPaymentSubmission
│   ├── test_subscription_service.py  # SubscriptionService business logic
│   ├── test_seo_services.py          # ContentAnalysis, SEO, Technical, LinkChecker, EEAT, Sentiment
│   ├── test_keyword_ai_models.py     # ContentAnalysis, KeywordOpportunity, SuggestionFeedback, AnalysisTask
│   ├── test_keyword_pipeline.py      # Pipeline v2 phases, helpers, RelevanceScorerV2
│   └── test_comparative_services.py  # DataExtractor, ScoringEngine, GapAnalyzer, ComparisonReport
│
├── integration/             # Integration tests — DB + mocked external services
│   ├── test_auth_views.py             # Login, register, logout, password reset, login-required gates
│   ├── test_seo_audit_views.py        # /home/, /show/, /report/, sentiment analysis, SEO tools
│   ├── test_subscription_views.py     # Pricing, dashboard, payment submit, admin verify/reject
│   ├── test_subscription_decorators.py # @require_subscription, @track_usage, @require_feature, @api_subscription_check
│   └── test_comparative_views.py      # Comparison input, analyze, results page
│
├── api/                     # REST API endpoint tests
│   └── test_keyword_ai_api.py  # All /api/keywords/* endpoints
│
├── e2e/                     # End-to-end user journey tests
│   └── test_user_journeys.py   # 6 full journeys: registration, paid audit, admin payment, comparative, usage reset, keyword feedback
│
└── manual/                  # Human-executed test cases
    └── MANUAL_TEST_CASES.md  # 50+ manual test cases across 12 categories
```

## Running Tests

### Run all automated tests
```powershell
cd e:\Project
python -m pytest tests/ -v
```

### Run by category
```powershell
# Unit tests only (fastest)
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# API tests
python -m pytest tests/api/ -v

# E2E journeys
python -m pytest tests/e2e/ -v
```

### Run by marker
```powershell
# All subscription-related
python -m pytest tests/ -m subscription -v

# All SEO-related
python -m pytest tests/ -m seo -v

# All auth-related
python -m pytest tests/ -m auth -v

# Skip slow tests
python -m pytest tests/ -m "not slow" -v
```

### Run with coverage
```powershell
python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
```

### Run a single file
```powershell
python -m pytest tests/unit/test_subscription_service.py -v
```

## Test Categories

| Category | Description | Speed | DB Required |
|----------|-------------|-------|-------------|
| `unit` | Logic-only tests, heavily mocked | Fast | No/minimal |
| `integration` | View + DB tests, external services mocked | Medium | Yes |
| `api` | REST endpoint tests | Medium | Yes |
| `e2e` | Full user journeys through views | Slow | Yes |
| `manual` | Human-executed (see MANUAL_TEST_CASES.md) | N/A | N/A |

## Coverage Goals

| App | Target |
|-----|--------|
| subscriptions (models + service) | 90% |
| SEOAnalyzer (services) | 80% |
| keyword_ai (pipeline + models) | 75% |
| comparative_analysis (services) | 75% |
| All views (auth + decorators) | 70% |

## Key Fixtures (conftest.py)

| Fixture | Description |
|---------|-------------|
| `test_user` | Standard Django user |
| `admin_user` | Superuser |
| `subscription_tiers` | All 4 tiers (free, basic, pro, enterprise) |
| `free_subscription` | Free tier subscription for test_user |
| `basic_subscription` | Active Basic subscription |
| `pro_subscription` | Active Pro subscription |
| `enterprise_subscription` | Active Enterprise subscription |
| `expired_subscription` | Pro subscription with past period_end |
| `authenticated_client` | Django test client logged in as test_user |
| `pro_client` | Client logged in with pro_subscription |
| `basic_client` | Client logged in with basic_subscription |
| `admin_client` | Client logged in as admin |
| `sample_html` | Full HTML with title, meta, h1, h2, links |
| `sample_content_analysis` | ContentAnalysis DB record |
| `sample_keyword_opportunities` | 6 KeywordOpportunity records |
| `sample_comparison_report` | ComparisonReport DB record |
| `mock_groq` | Mocked Groq LLM client |
| `mock_requests` | Mocked requests.get / post |
| `disable_celery` | Forces Celery tasks to run synchronously |

## Prerequisites

```powershell
pip install pytest pytest-django pytest-cov factory-boy numpy
```

Ensure `Project/settings_test.py` exists with:
- `USE_SQLITE = True`
- `CELERY_TASK_ALWAYS_EAGER = True`
- `USE_GROQ = False`
- `USE_PINECONE = False`
