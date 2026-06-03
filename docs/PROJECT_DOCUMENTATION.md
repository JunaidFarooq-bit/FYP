# WebLift - SEO Analysis Platform
## Complete Project Documentation for Diagram Generation

---

## 1. PROJECT OVERVIEW

**Project Name:** WebLift (SEO Analyzer)  
**Technology Stack:** Django 4.x, Python, Celery, Redis, PostgreSQL  
**Architecture:** Monolithic Django with Celery for async processing  
**Purpose:** AI-powered SEO analysis platform that provides comprehensive website auditing, keyword suggestions, competitor analysis, sentiment analysis, and subscription-based access control.

---

## 2. ACTORS / USER ROLES

| Actor | Description |
|-------|-------------|
| **Guest** | Unauthenticated user. Can only access login, register, and forget password pages. |
| **Registered User (Free Tier)** | Authenticated user with limited features (1 free audit). |
| **Basic Subscriber** | Paid user with basic features (limited audits/month). |
| **Pro Subscriber** | Paid user with AI suggestions, competitor analysis, PDF export. |
| **Enterprise Subscriber** | Full access including API, priority support, unlimited audits. |
| **Admin (Staff)** | Django staff user who verifies manual payments, manages subscriptions, and accesses the admin panel. |
| **System (Celery Worker)** | Background process handling async tasks, batch analysis, and model retraining. |

---

## 3. DJANGO APPS & MODULES

| App | Responsibility |
|-----|---------------|
| **Project/** | Root config: settings, URLs, Celery, WSGI/ASGI |
| **SEOAnalyzer/** | Core SEO audit engine, authentication, page views, services |
| **keyword_ai/** | AI keyword suggestion pipeline, ML models, async tasks, analytics |
| **comparative_analysis/** | Side-by-side competitor comparison analysis |
| **subscriptions/** | Subscription tiers, usage tracking, payments, access control |

---

## 4. USE CASE DIAGRAM DETAILS

### 4.1 Guest Use Cases
- **UC-01:** Register Account
- **UC-02:** Login
- **UC-03:** Forget Password (request reset email)
- **UC-04:** Change Password (via token link)

### 4.2 Authenticated User Use Cases
- **UC-05:** Run SEO Audit (enter URL → get full audit report)
- **UC-06:** View Audit Dashboard (scores, issues, charts)
- **UC-07:** Generate PDF Report (email or download)
- **UC-08:** Download PDF Report (premium feature)
- **UC-09:** Check SEO Metrics (Moz API: DA, PA, backlinks)
- **UC-10:** Mobile Friendliness Test (PageSpeed Insights API)
- **UC-11:** Generate Robots.txt
- **UC-12:** Check Keyword Position (Google rank)
- **UC-13:** Get Keyword Suggestions (Google Autocomplete)
- **UC-14:** AI Keyword Analysis (ML pipeline v2)
- **UC-15:** Sentiment Analysis (URL content)
- **UC-16:** Comparative Analysis (your site vs competitor)
- **UC-17:** View Subscription Dashboard
- **UC-18:** View Pricing Plans
- **UC-19:** Submit Manual Payment Proof
- **UC-20:** Cancel Subscription
- **UC-21:** Change Plan
- **UC-22:** Logout

### 4.3 API Use Cases (keyword_ai endpoints)
- **UC-23:** Keyword Suggestions API (v1)
- **UC-24:** Keyword Suggestions API (v2 - enhanced)
- **UC-25:** Streaming Keyword Suggestions
- **UC-26:** Submit Feedback on Suggestions
- **UC-27:** Get Keyword Opportunities
- **UC-28:** Async Single URL Analysis
- **UC-29:** Async Batch URL Analysis
- **UC-30:** Check Task Status
- **UC-31:** List Tasks
- **UC-32:** Export Results (CSV/JSON)

### 4.4 Analytics API Use Cases
- **UC-33:** View Analytics Dashboard Summary
- **UC-34:** View Model Performance Metrics
- **UC-35:** View Feedback Analytics
- **UC-36:** View A/B Test Results
- **UC-37:** View Retraining Status
- **UC-38:** View Usage Metrics
- **UC-39:** Trigger Model Retraining
- **UC-40:** Create A/B Test
- **UC-41:** Stop A/B Test

### 4.5 Admin Use Cases
- **UC-42:** View Pending Payments
- **UC-43:** Verify Payment (activate subscription)
- **UC-44:** Reject Payment
- **UC-45:** Django Admin Panel (manage all models)

### 4.6 System (Background) Use Cases
- **UC-46:** Process Async Analysis Task (Celery)
- **UC-47:** Process Batch Analysis (Celery)
- **UC-48:** Reset Monthly Usage Counters
- **UC-49:** Model Retraining Pipeline

---

## 5. CLASS DIAGRAM / DATA MODEL

### 5.1 SEOAnalyzer App
```
Profile
├── user: OneToOne → User
├── forget_password_token: CharField
└── created_at: DateTimeField
```

### 5.2 Subscriptions App
```
SubscriptionTier
├── name: CharField (free/basic/pro/enterprise)
├── display_name: CharField
├── price_monthly: DecimalField
├── price_yearly: DecimalField
├── has_ai_suggestions: BooleanField
├── has_competitor_analysis: BooleanField
├── has_pdf_export: BooleanField
├── has_api_access: BooleanField
├── has_priority_support: BooleanField
├── max_audits_per_month: IntegerField (nullable=unlimited)
├── max_keywords_per_analysis: IntegerField
├── max_competitors_per_analysis: IntegerField
├── features_list: JSONField
└── is_active: BooleanField

Subscription
├── user: OneToOne → User
├── tier: ForeignKey → SubscriptionTier
├── status: CharField (active/trialing/past_due/canceled/unpaid/incomplete/free_trial_used)
├── billing_cycle: CharField (monthly/yearly)
├── current_period_start: DateTimeField
├── current_period_end: DateTimeField
├── trial_end: DateTimeField
├── canceled_at: DateTimeField
├── stripe_customer_id: CharField
└── stripe_subscription_id: CharField

UsageTracker
├── user: OneToOne → User
├── audits_used_this_month: IntegerField
├── keywords_generated_this_month: IntegerField
├── competitor_analyses_this_month: IntegerField
├── pdf_exports_this_month: IntegerField
├── free_audit_used: BooleanField
├── free_audit_used_at: DateTimeField
├── last_reset_date: DateTimeField
└── usage_history: JSONField

PaymentRecord
├── user: ForeignKey → User
├── subscription: ForeignKey → Subscription
├── amount: DecimalField
├── currency: CharField
├── status: CharField (pending/completed/failed/refunded)
├── stripe_payment_intent_id: CharField
└── stripe_invoice_id: CharField

ManualPaymentSubmission
├── user: ForeignKey → User
├── tier: ForeignKey → SubscriptionTier
├── billing_cycle: CharField
├── amount: DecimalField
├── sender_name: CharField
├── sender_account_last4: CharField
├── transaction_reference: CharField
├── payment_date: DateField
├── proof_document: FileField
├── notes: TextField
├── status: CharField (pending/verified/rejected/expired)
├── verified_by: ForeignKey → User (admin)
└── verified_at: DateTimeField

FeatureAccessLog
├── user: ForeignKey → User
├── feature_name: CharField
├── access_granted: BooleanField
├── reason: CharField
└── timestamp: DateTimeField
```

### 5.3 Keyword AI App
```
ContentAnalysis
├── url: URLField (unique)
├── content_hash: CharField
├── title: CharField
├── meta_description: TextField
├── full_text: TextField
├── word_count: IntegerField
├── quality_score: FloatField
├── readability_ease: FloatField
├── readability_grade: FloatField
├── structure_data: JSONField
├── entities_data: JSONField
├── tfidf_keywords: JSONField
├── embedding: JSONField (vector for Pinecone/pgvector)
├── analyzed_at: DateTimeField
└── updated_at: DateTimeField

KeywordOpportunity
├── content_analysis: ForeignKey → ContentAnalysis
├── keyword: CharField
├── keyword_type: CharField (tfidf/gap/llm/longtail)
├── relevance_score: FloatField (0-100)
├── search_volume_estimate: CharField
├── difficulty_score: FloatField (0-100)
├── competition_gap_score: FloatField (0-100)
├── search_intent: CharField (informational/navigational/transactional/commercial)
├── priority: CharField (high/medium/low)
├── ai_reasoning: TextField
├── suggested_action: TextField
├── is_accepted: BooleanField
└── is_rejected: BooleanField

SuggestionFeedback
├── opportunity: ForeignKey → KeywordOpportunity
├── user_action: CharField (accepted/rejected/ignored/implemented)
├── user_comment: TextField
├── rating: IntegerField (1-5)
├── session_id: CharField
├── ranking_before: IntegerField
├── ranking_after_30_days: IntegerField
└── traffic_increase_estimate: FloatField

CompetitorAnalysis (keyword_ai)
├── user_content: ForeignKey → ContentAnalysis
├── competitor_url: URLField
├── competitor_title: CharField
├── meta_keywords: TextField
├── headings_data: JSONField
├── top_keywords: JSONField
└── status: CharField

AnalysisTask
├── task_id: CharField (unique)
├── task_type: CharField (single_url/batch_urls/content_text/competitor_analysis)
├── parameters: JSONField
├── status: CharField (pending/processing/completed/failed/cancelled)
├── progress_percent: IntegerField (0-100)
├── current_step: CharField
├── result_data: JSONField
├── error_message: TextField
├── total_urls: IntegerField
├── processed_urls: IntegerField
├── failed_urls: IntegerField
├── started_at: DateTimeField
└── completed_at: DateTimeField

GapAnalysis
├── content_analysis: OneToOne → ContentAnalysis
├── total_gap_opportunities: IntegerField
├── high_priority_gaps: JSONField
├── all_gap_keywords: JSONField
└── recommendations: JSONField

ModelPerformance
├── model_name: CharField
├── model_version: CharField
├── total_predictions: IntegerField
├── accepted_suggestions: IntegerField
├── rejected_suggestions: IntegerField
├── ignored_suggestions: IntegerField
├── avg_relevance_score: FloatField
├── avg_user_rating: FloatField
├── precision_at_k: JSONField
└── recorded_at: DateTimeField

ABTest
├── test_name: CharField
├── test_description: TextField
├── control_model: CharField
├── treatment_model: CharField
├── traffic_split_percent: IntegerField
├── control_metrics: JSONField
├── treatment_metrics: JSONField
├── status: CharField (running/completed/stopped)
├── winner: CharField
├── confidence_level: FloatField
├── started_at: DateTimeField
└── completed_at: DateTimeField

KeywordRanking
├── opportunity: ForeignKey → KeywordOpportunity
├── keyword: CharField
├── url: URLField
├── ranking_position: IntegerField
├── search_volume: IntegerField
└── checked_at: DateTimeField

UserSessionMetrics
├── session_id: CharField
├── total_analyses: IntegerField
├── total_keywords_generated: IntegerField
├── total_feedback_submitted: IntegerField
├── avg_time_on_page: IntegerField
├── features_used: JSONField
├── first_activity: DateTimeField
└── last_activity: DateTimeField
```

### 5.4 Comparative Analysis App
```
ComparisonReport
├── url_primary: URLField
├── url_competitor: URLField
├── target_keyword: CharField
├── detected_keyword_primary: CharField
├── detected_keyword_competitor: CharField
├── intent_type_primary: CharField
├── intent_type_competitor: CharField
├── scores_primary: JSONField
├── scores_competitor: JSONField
├── gap_summary: TextField
├── ranking_explanation: TextField
├── analysis_duration: FloatField
└── created_at: DateTimeField
```

---

## 6. ACTIVITY DIAGRAMS

### 6.1 User Registration Flow
```
[Start]
  → User opens Register page
  → User fills form (username, email, first_name, last_name, password1, password2)
  → Submit form
  → [Decision] All fields filled?
    → No: Show "Please fill in all fields" → Back to form
    → Yes: Continue
  → [Decision] Passwords match?
    → No: Show "Passwords do not match" → Back to form
    → Yes: Continue
  → [Decision] Email valid format?
    → No: Show "Invalid email" → Back to form
    → Yes: Continue
  → [Decision] Email already exists?
    → Yes: Show "Email already registered" → Back to form
    → No: Continue
  → Create User object
  → Create Profile object
  → Redirect to Login page
[End]
```

### 6.2 User Login Flow
```
[Start]
  → User opens Login page
  → User enters username + password
  → Submit form
  → [Decision] Fields filled?
    → No: Show "Please fill in all fields" → Back to form
    → Yes: Continue
  → Django authenticate(username, password)
  → [Decision] Credentials valid?
    → No: Show "Invalid Credentials" → Back to form
    → Yes: login(request, user) → Redirect to Home
[End]
```

### 6.3 Forget Password Flow
```
[Start]
  → User opens Forget Password page
  → User enters email
  → Submit form
  → [Decision] User with email exists?
    → No: Show "No account found" → Back to form
    → Yes: Continue
  → Generate UUID token
  → Save token to Profile.forget_password_token
  → Send password reset email with token link
  → Show "Email sent!" message
[End]
```

### 6.4 SEO Audit Flow (Main Feature)
```
[Start]
  → User enters URL on Home page
  → Submit form (POST to /show/)
  → @login_required check
  → @track_usage('audit') decorator:
    → Get/create UsageTracker
    → [Decision] Usage limit reached?
      → Yes: Set upgrade_required session flag → Redirect
      → No: Continue
  → Validate URL format
  → [Decision] Valid URL?
    → No: Show error → Back to index
    → Yes: Continue
  → Create Website_Audit instance
  → Run full analysis:
    → Fetch page HTML (requests.get with timeout)
    → Parse with BeautifulSoup
    → Extract title, meta description, headings
    → Analyze keyword density
    → Check robots.txt, sitemap.xml
    → Check SSL/HTTPS
    → Analyze page speed (TTFB)
    → Check Schema markup
    → Check Open Graph tags
    → Check social media links
    → Analyze images (alt text)
    → Check internal/external/broken links
    → Grammar analysis
    → Readability scoring
    → E-E-A-T analysis
    → Mobile optimization check
  → Cache audit results (1 hour TTL)
  → Prepare dashboard data (chart scores, priority issues)
  → Render home.html with full audit context
[End]
```

### 6.5 PDF Report Generation Flow
```
[Start]
  → User clicks "Download Report" or "Email Report"
  → @login_required check
  → @require_feature('pdf_export') check:
    → [Decision] User tier has PDF export?
      → No: Set upgrade_required → Redirect
      → Yes: Continue
  → Get URL from request
  → Try to get cached audit results (from previous audit)
  → [Decision] Cached data found?
    → Yes: Use cached data
    → No: Run fresh audit
  → Generate comprehensive report data
  → Generate PDF using modern_report module
  → [Decision] Email or Download?
    → Email: Send PDF as email attachment → Show success message
    → Download: Return FileResponse with PDF attachment
[End]
```

### 6.6 AI Keyword Suggestion Flow (Pipeline v2)
```
[Start]
  → User provides URL or text content + optional page_topic
  → @track_usage('audit') check
  → [Decision] URL or Text provided?
    → Neither: Show error
    → Yes: Continue
  → Run keyword_pipeline_v2:
    → Step 1: Extract content (fetch URL or use text)
    → Step 2: Analyze content (word count, readability, entities, TF-IDF)
    → Step 3: Generate content embedding (sentence-transformers)
    → Step 4: KeyBERT keyword extraction
    → Step 5: Semantic keyword expansion (similarity search)
    → Step 6: ML Relevance Scoring v2 (custom trained model)
    → Step 7: Search Intent Classification
    → Step 8: ML Suggestion Generation
    → Step 9: Semantic Keyword Mapping
    → Step 10: [If use_llm=True] LLM Refinement (Groq/OpenAI)
    → Step 11: [If use_llm=True] LLM Expansion (question keywords, clusters)
    → Step 12: [If analyze_competitors=True] Competitor gap analysis
    → Step 13: [If generate_optimization=True] Content optimization suggestions
    → Step 14: RAG context retrieval (similar past analyses)
    → Step 15: Save to database (ContentAnalysis + KeywordOpportunity records)
  → Return results (scored keywords, intent groups, focus keywords, etc.)
  → Render keyword_ai_suggestions.html with results
[End]
```

### 6.7 Async Batch Analysis Flow
```
[Start]
  → User submits list of URLs via API (POST /api/keywords/analyze-batch/)
  → Validate URLs (max 50)
  → Create AnalysisTask record (status=pending)
  → Dispatch Celery task (start_batch_analysis)
  → Return task_id immediately to user
  → [Background - Celery Worker]:
    → For each URL in batch:
      → Update progress (processed_urls / total_urls)
      → Run keyword_pipeline_v2 for URL
      → Save results to AnalysisTask.result_data
      → [Decision] URL failed?
        → Yes: Increment failed_urls, log error
        → No: Store URL results
    → Mark task completed
  → [User polls GET /api/keywords/task-status/?task_id=X]
  → Return progress/results
[End]
```

### 6.8 Comparative Analysis Flow
```
[Start]
  → User opens Comparative Analysis input form
  → Enter primary URL + competitor URL + optional target keyword
  → Submit form (POST to /comparative-analysis/analyze/)
  → Validate both URLs
  → Create ComparisonOrchestrator instance
  → Run full analysis:
    → Fetch both pages
    → Semantic analysis (keyword detection, intent, content quality, E-E-A-T)
    → Technical SEO analysis (speed, mobile, SSL, structured data)
    → Authority analysis (domain authority, backlinks)
    → Calculate on-page scores
    → Generate gap analysis (AI explanation of ranking differences)
  → Save ComparisonReport to database
  → Store full results in session
  → Redirect to results page
  → Render results template (side-by-side comparison)
[End]
```

### 6.9 Subscription & Payment Flow
```
[Start]
  → User views Pricing page (GET /subscriptions/pricing/)
  → User selects a plan
  → [Decision] Free plan?
    → Yes: Downgrade/cancel current → redirect to dashboard
    → No: Continue to payment
  → Show Payment Instructions (bank transfer details)
  → User makes bank transfer
  → User submits payment proof:
    → Fill form (sender name, transaction ref, date, upload proof)
    → POST to /subscriptions/payment/submit/
    → Create ManualPaymentSubmission (status=pending)
  → [Admin Flow]:
    → Admin views pending payments (GET /subscriptions/admin/pending-payments/)
    → Admin reviews proof document
    → [Decision] Payment valid?
      → Yes: Verify payment → Activate subscription → Set status=verified
      → No: Reject payment → Set status=rejected → Notify user
  → User subscription activated
  → Usage limits updated based on new tier
[End]
```

### 6.10 Sentiment Analysis Flow
```
[Start]
  → User opens Sentiment Analysis page
  → Enter URL + select mode (auto/detailed)
  → Submit form
  → Fetch page content (requests.get)
  → Extract text (remove scripts, styles, nav, footer)
  → Extract page title and meta description
  → Count words
  → Run sentiment analysis (analyze_sentiment service)
  → Return results:
    → Overall sentiment (positive/negative/neutral)
    → Confidence score
    → Section-by-section breakdown
  → Render sentiment_results.html
[End]
```

### 6.11 Feedback & Continuous Learning Flow
```
[Start]
  → User receives keyword suggestions
  → User provides feedback (accept/reject/implement/ignore + rating)
  → POST to /api/keywords/feedback/
  → Create SuggestionFeedback record
  → [Background - Periodic]:
    → FeedbackCollector aggregates feedback
    → PerformanceTracker updates model metrics
    → ContinuousLearningMonitor checks if retraining needed
    → [Decision] Retraining threshold met?
      → Yes: Trigger RetrainingPipeline
      → No: Continue monitoring
  → ModelPerformance record updated
[End]
```

---

## 7. SEQUENCE DIAGRAMS (Key Interactions)

### 7.1 SEO Audit Sequence
```
User → Browser → Django (show view)
  → @login_required middleware
  → @track_usage decorator → UsageTracker.record_audit()
  → Website_Audit.__init__(url)
  → requests.get(url) → Target Website
  → BeautifulSoup(html)
  → ContentAnalysisService.analyze_content_quality()
  → GrammarAnalyzer.analyze()
  → EEATAnalyzer.analyze()
  → LinkChecker.check_links()
  → TechnicalAudit.run()
  → cache.set(audit_results)
  → _prepare_dashboard_data(audit_data)
  → render(home.html, context) → Browser → User
```

### 7.2 Keyword AI Pipeline v2 Sequence
```
User → Browser → Django (keyword_ai_suggestions view)
  → run_keyword_pipeline_v2(url, params)
    → extract_content(url) → Target Website HTML
    → analyze_content(meta) → ContentAnalysis
    → get_single_embedding(text) → sentence-transformers model
    → extract_keywords(text) → KeyBERT model
    → expand_keywords(keywords) → similarity_search
    → score_keywords_v2(keywords) → ML relevance model
    → classify_intent(keywords) → Intent classifier
    → generate_keyword_suggestions(analysis) → ML generator
    → find_semantic_keywords(text) → Semantic mapper
    → refine_keywords(keywords) → LLM API (Groq)
    → expand_keywords_with_llm(keywords) → LLM API
    → retrieve_similar_analyses(embedding) → RAG/Vector DB
    → save_content_analysis() → PostgreSQL DB
    → save KeywordOpportunity records → PostgreSQL DB
  → Return results dict → render template → User
```

### 7.3 Subscription Check Sequence (Decorator)
```
User → Request any protected endpoint
  → @api_subscription_check / @enforce_free_trial_limit / @require_feature
  → Check request.user.is_authenticated
    → No: Return 401
  → Get user.subscription (or create default)
  → [Decision] subscription.is_active() or has_free_trial_available()?
    → No: Return 403 / Set upgrade_required session flag
    → Yes: Continue to view function
  → Execute view → Return response
```

---

## 8. COMPONENT / PACKAGE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                        WebLift Platform                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐           │
│  │ SEOAnalyzer │  │  keyword_ai  │  │ comparative_analysis│          │
│  │             │  │              │  │                     │          │
│  │ - Views     │  │ - Pipeline   │  │ - Orchestrator     │          │
│  │ - Services  │  │ - ML Models  │  │ - Services         │          │
│  │ - Templates │  │ - Services   │  │ - Templates        │          │
│  │             │  │ - Tasks      │  │                     │          │
│  └──────┬──────┘  └──────┬───────┘  └─────────┬─────────┘          │
│         │                 │                     │                     │
│         └─────────────────┼─────────────────────┘                    │
│                           │                                           │
│              ┌────────────┴────────────┐                             │
│              │     subscriptions       │                             │
│              │                          │                             │
│              │ - Tiers & Plans          │                             │
│              │ - Usage Tracking         │                             │
│              │ - Decorators (ACL)       │                             │
│              │ - Payment Processing     │                             │
│              └────────────┬─────────────┘                            │
│                           │                                           │
├───────────────────────────┼───────────────────────────────────────────┤
│  Infrastructure Layer     │                                           │
│                           │                                           │
│  ┌──────────┐  ┌─────────┴───┐  ┌───────────┐  ┌─────────────┐    │
│  │ PostgreSQL│  │   Redis     │  │  Celery   │  │ External APIs│    │
│  │ Database  │  │ (Cache/     │  │ (Async    │  │ - Groq LLM  │    │
│  │           │  │  Broker)    │  │  Tasks)   │  │ - Moz API   │    │
│  │           │  │             │  │           │  │ - PageSpeed  │    │
│  │           │  │             │  │           │  │ - Google     │    │
│  └───────────┘  └─────────────┘  └───────────┘  └─────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. DEPLOYMENT DIAGRAM

```
┌────────────────────────────────┐
│        User's Browser          │
│  (Chrome, Firefox, Safari)     │
└──────────────┬─────────────────┘
               │ HTTPS
               ▼
┌────────────────────────────────┐
│     Web Server (Gunicorn)      │
│     Django Application         │
│     Port: 8000                 │
└───┬──────────────┬─────────────┘
    │              │
    ▼              ▼
┌─────────┐  ┌───────────────────┐
│PostgreSQL│  │ Redis Server      │
│ Database │  │ (Cache + Broker)  │
│ Port:5432│  │ Port: 6379        │
└──────────┘  └────────┬──────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ Celery Worker   │
              │ (Background)    │
              └─────────────────┘
```

---

## 10. DATA FLOW DIAGRAM (DFD)

### Level 0 (Context Diagram)
```
[User] → (WebLift System) → [User]
[External APIs] → (WebLift System)
[Target Websites] → (WebLift System)
```

### Level 1
```
[User] → 1.0 Authentication Module → [User]
[User] → 2.0 SEO Audit Engine → [User]
         2.0 ← [Target Website]
         2.0 → [Database]
[User] → 3.0 Keyword AI Module → [User]
         3.0 ← [LLM API]
         3.0 ← [Target Website]
         3.0 → [Database]
[User] → 4.0 Comparative Analysis → [User]
         4.0 ← [Target Websites]
         4.0 → [Database]
[User] → 5.0 Subscription Manager → [User]
         5.0 → [Database]
[Admin] → 6.0 Payment Verification → [Database]
[System] → 7.0 Background Processing (Celery) → [Database]
```

---

## 11. STATE DIAGRAMS

### 11.1 Subscription States
```
[New User] → free_trial_used
free_trial_used → active (on payment verified)
active → past_due (on payment failure)
active → canceled (user cancels)
past_due → active (payment resolved)
past_due → unpaid (grace period expired)
canceled → active (re-subscribes)
incomplete → active (payment completed)
```

### 11.2 Analysis Task States
```
[Created] → pending
pending → processing (worker picks up)
processing → completed (success)
processing → failed (error)
pending → cancelled (user cancels)
```

### 11.3 Manual Payment States
```
[Submitted] → pending
pending → verified (admin approves)
pending → rejected (admin rejects)
pending → expired (time limit exceeded)
```

---

## 12. URL ROUTING MAP (Complete Endpoints)

### Root URLs (Project/urls.py)
| Method | URL | View | Description |
|--------|-----|------|-------------|
| GET | `/` | loginuser | Login page |
| GET/POST | `/register/` | register | Registration |
| GET/POST | `/home/` | index | Home/Dashboard |
| POST | `/show/` | show | Run SEO Audit |
| GET | `/upload/` | upload | Upload handler |
| POST | `/report/` | Report | Generate email report |
| GET/POST | `/report/download/` | download_report | PDF download |
| GET/POST | `/seo-metrics/` | seo_metrics | Moz metrics |
| GET/POST | `/mobiletest/` | mobiletest | Mobile test |
| GET/POST | `/robot/` | robot | Robots.txt generator |
| GET/POST | `/keyPosition/` | keyPosition | Keyword rank check |
| GET/POST | `/keysuggestion/` | keysuggestion | Google autocomplete |
| GET/POST | `/keyword-ai-suggestions/` | keyword_ai_suggestions | AI keywords |
| GET/POST | `/sentimentanalysis/` | sentiment_analysis_page | Sentiment page |
| POST | `/sentimentanalysis/analyze/` | analyze_sentiment_view | Analyze sentiment |
| GET/POST | `/forget-password/` | ForgetPassword | Password reset request |
| GET/POST | `/change-password/<token>/` | ChangePassword | Reset password |
| GET | `/logout/` | logoutuser | Logout |
| GET | `/health/` | health_check | System health |
| GET | `/ready/` | readiness_check | Readiness probe |
| GET | `/live/` | liveness_check | Liveness probe |
| * | `/admin/` | Django Admin | Admin panel |

### Keyword AI URLs (/api/keywords/)
| Method | URL | View | Description |
|--------|-----|------|-------------|
| GET | `/api/keywords/` | keyword_suggestions | v1 suggestions |
| GET | `/api/keywords/v2/` | keyword_suggestions_v2 | v2 enhanced |
| GET | `/api/keywords/streaming/` | keyword_suggestions_streaming | SSE streaming |
| POST | `/api/keywords/feedback/` | submit_feedback | User feedback |
| GET | `/api/keywords/opportunities/` | get_opportunities | Stored opportunities |
| POST | `/api/keywords/analyze-async/` | analyze_url_async | Async single URL |
| POST | `/api/keywords/analyze-batch/` | analyze_batch_async | Async batch |
| GET | `/api/keywords/task-status/` | get_task_status | Task progress |
| GET | `/api/keywords/tasks/` | list_tasks | List user tasks |
| GET | `/api/keywords/export/` | export_results | CSV/JSON export |
| GET | `/api/keywords/analytics/dashboard/` | get_dashboard_summary | Analytics |
| GET | `/api/keywords/analytics/model-performance/` | get_model_performance | Model stats |
| GET | `/api/keywords/analytics/feedback/` | get_feedback_analytics | Feedback stats |
| GET | `/api/keywords/analytics/ab-tests/` | get_ab_test_results | A/B tests |
| GET | `/api/keywords/analytics/retraining/` | get_retraining_status | Retrain status |
| GET | `/api/keywords/analytics/usage/` | get_usage_metrics | Usage metrics |
| POST | `/api/keywords/analytics/trigger-retrain/` | trigger_retraining | Trigger retrain |
| POST | `/api/keywords/analytics/create-ab-test/` | create_ab_test | New A/B test |
| POST | `/api/keywords/analytics/stop-ab-test/` | stop_ab_test | Stop A/B test |

### Comparative Analysis URLs (/comparative-analysis/)
| Method | URL | View | Description |
|--------|-----|------|-------------|
| GET | `/comparative-analysis/` | input_form | Input form |
| POST | `/comparative-analysis/analyze/` | analyze_comparison | Run comparison |
| GET | `/comparative-analysis/results/<id>/` | view_results | View results |

### Subscription URLs (/subscriptions/)
| Method | URL | View | Description |
|--------|-----|------|-------------|
| GET | `/subscriptions/pricing/` | pricing | Plans & pricing |
| GET | `/subscriptions/payment/instructions/` | payment_instructions | Bank details |
| POST | `/subscriptions/payment/submit/` | submit_payment_proof | Submit proof |
| GET | `/subscriptions/dashboard/` | subscription_dashboard | User dashboard |
| POST | `/subscriptions/cancel/` | cancel_subscription | Cancel plan |
| POST | `/subscriptions/change-plan/` | change_plan | Change plan |
| GET | `/subscriptions/api/usage/` | usage_api | AJAX usage data |
| POST | `/subscriptions/api/clear-upgrade-flag/` | clear_upgrade_flag | Dismiss modal |
| GET | `/subscriptions/admin/pending-payments/` | pending_payments_admin | Admin: pending |
| POST | `/subscriptions/admin/verify-payment/<id>/` | verify_payment_admin | Admin: verify |
| POST | `/subscriptions/admin/reject-payment/<id>/` | reject_payment_admin | Admin: reject |

---

## 13. SERVICE LAYER DETAILS

### SEOAnalyzer Services
| Service | File | Purpose |
|---------|------|---------|
| ContentAnalysisService | content_analysis_service.py | Word count, readability, structure analysis |
| EEATAnalyzer | eeat_analyzer.py | Experience, Expertise, Authority, Trust analysis |
| GrammarAnalyzer | grammar_analyzer.py | Grammar and spelling checks |
| LinkChecker | link_checker.py | Internal/external/broken link analysis |
| SentimentAnalyzer | sentiment_analyzer.py | Content sentiment analysis |
| TechnicalAudit | technical_audit.py | Technical SEO checks |
| ReportOrchestrator | report_orchestrator.py | Comprehensive report data aggregation |
| MinificationChecker | minification_checker.py | CSS/JS minification check |
| CircuitBreaker | circuit_breaker.py | External API resilience pattern |
| AsyncHTTPClient | async_http_client.py | Non-blocking HTTP requests |

### Keyword AI Services
| Service | File | Purpose |
|---------|------|---------|
| extract_content | extract_content.py | Fetch and parse URL content |
| analyze_content | content_analyzer.py | TF-IDF, entities, structure |
| KeyBERT Extractor | keybert_extractor.py | ML keyword extraction |
| Similarity Search | similarity_search.py | Keyword expansion via embeddings |
| Relevance Scorer v1 | relevance_scorer.py | Rule-based scoring |
| Relevance Scorer v2 | ml_models/relevance_scorer_v2.py | ML-based scoring + intent |
| Suggestion Generator | ml_models/suggestion_generator.py | ML keyword generation |
| Semantic Mapper | ml_models/semantic_mapper.py | Semantic keyword discovery |
| LLM Refiner | llm_refiner.py | LLM-based keyword refinement |
| LLM Expander | llm_expander.py | Question keywords, clusters |
| Intent Classifier | intent_classifier.py | Search intent classification |
| Content Optimizer | content_optimizer.py | Content improvement suggestions |
| Feedback Collector | feedback_collector.py | User feedback aggregation |
| A/B Testing | ab_testing.py | Model variant testing |
| RAG Retriever | rag_retriever.py | Similar analysis retrieval |
| Embeddings | embeddings.py | Vector embedding generation |
| Pinecone Service | pinecone_service.py | Vector database integration |
| Model Manager | model_manager.py | ML model lifecycle management |

### Comparative Analysis Services
| Service | File | Purpose |
|---------|------|---------|
| ComparisonOrchestrator | comparison_orchestrator.py | Orchestrates full comparison |
| DataExtraction | data_extraction.py | Page data extraction |
| SemanticAnalysis | semantic_analysis.py | Content semantic scoring |
| TechnicalComparison | technical_comparison.py | Technical SEO comparison |
| AuthorityAnalysis | authority_analysis.py | Domain authority scoring |
| GapAnalysis | gap_analysis.py | Content/keyword gap identification |
| RankingExplainer | ranking_explainer.py | AI-powered ranking explanation |

### Subscription Services
| Service | File | Purpose |
|---------|------|---------|
| SubscriptionService | subscription_service.py | Subscription CRUD, tier management |

---

## 14. TECHNOLOGY & EXTERNAL INTEGRATIONS

| Technology/API | Purpose |
|----------------|---------|
| **Django 4.x** | Web framework |
| **PostgreSQL** | Primary database |
| **Redis** | Caching + Celery message broker |
| **Celery** | Asynchronous task processing |
| **BeautifulSoup4** | HTML parsing |
| **scikit-learn** | ML models (TF-IDF, classifiers) |
| **KeyBERT** | Keyword extraction |
| **sentence-transformers** | Text embeddings (384-dim) |
| **Groq API** | LLM inference (keyword refinement, expansion) |
| **Moz API** | Domain Authority, Page Authority, backlinks |
| **Google PageSpeed Insights API** | Mobile testing, Core Web Vitals |
| **Google Search** | Keyword position checking |
| **Google Suggest API** | Autocomplete keyword suggestions |
| **Pinecone** | Vector database for semantic search |
| **ReportLab/WeasyPrint** | PDF report generation |
| **SMTP** | Email sending (password reset, reports) |

---

## 15. SECURITY & ACCESS CONTROL FLOW

### Decorator Chain (Order of Execution)
```
Request → @login_required
        → @enforce_free_trial_limit / @track_usage
        → @require_feature('feature_name')
        → @rate_limit_api / @rate_limit_ai
        → View Function
        → Response
```

### Access Control Matrix
| Feature | Free | Basic | Pro | Enterprise |
|---------|------|-------|-----|-----------|
| SEO Audit | 1 free | 10/month | 50/month | Unlimited |
| Keyword Suggestions | Basic | Basic | AI-enhanced | AI-enhanced |
| Competitor Analysis | No | No | Yes (3) | Yes (10) |
| PDF Export | No | No | Yes | Yes |
| API Access | No | No | No | Yes |
| Priority Support | No | No | No | Yes |
| Keywords per Analysis | 5 | 20 | 50 | Unlimited |

---

## 16. ERROR HANDLING PATTERNS

```
All views follow:
  try:
    → Execute main logic
  except requests.exceptions.Timeout:
    → "Connection timed out" message
  except requests.exceptions.RequestException:
    → "Check internet connection" message
  except Exception as e:
    → Log error
    → Generic error message to user
    → Render safe fallback template
```

---

## 17. CACHING STRATEGY

| Cache Key Pattern | TTL | Purpose |
|-------------------|-----|---------|
| `audit_results_{md5(url)}` | 1 hour | Store audit results for PDF consistency |
| Session data | 24 hours | Store analysis results between pages |
| Django cache framework | Varies | General caching via Redis backend |

---

## 18. BACKGROUND TASK FLOWS (Celery)

### Task: analyze_single_url_task
```
[Dispatched] → status=pending
→ Celery picks up → status=processing, started_at=now
→ progress=10%: "Extracting content..."
→ Run pipeline_v2
→ progress=90%: "Saving results..."
→ [Success] → status=completed, progress=100%
→ [Failure] → status=failed, error_message=str(e)
→ [Retry] → max_retries=3
```

### Task: analyze_batch_urls
```
[Dispatched] → Create parent AnalysisTask
→ For each URL:
  → Update progress (processed/total * 100)
  → Run pipeline_v2
  → Accumulate results
→ Mark task completed with aggregated results
```

---

## 19. NOTES FOR DIAGRAM TOOLS

### Recommended Diagram Types:
1. **Use Case Diagram** - Section 4 (actors + use cases with include/extend relationships)
2. **Class Diagram** - Section 5 (all models with relationships)
3. **Activity Diagrams** - Section 6 (one per major flow)
4. **Sequence Diagrams** - Section 7 (key interactions)
5. **Component Diagram** - Section 8 (app architecture)
6. **Deployment Diagram** - Section 9 (infrastructure)
7. **Data Flow Diagram (DFD)** - Section 10 (Level 0 + Level 1)
8. **State Machine Diagrams** - Section 11 (subscription, task, payment states)
9. **Package Diagram** - Based on Section 3 + 13

### Key Relationships for Use Case Diagram:
- `<<include>>`: UC-05 (SEO Audit) includes authentication check
- `<<include>>`: UC-14 (AI Keywords) includes subscription check
- `<<extend>>`: UC-07 (PDF Report) extends UC-05 (SEO Audit)
- `<<extend>>`: UC-08 (Download PDF) extends UC-05 (SEO Audit)
- `<<include>>`: UC-28/29 (Async Analysis) includes UC-46/47 (Celery Processing)
- `<<extend>>`: UC-11 (Feedback) extends UC-14 (AI Keywords)

---
