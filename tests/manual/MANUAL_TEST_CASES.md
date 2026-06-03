# WebLift SEO Platform — Manual Test Cases

> **Scope:** All tests that require human judgment, real browser interaction,
> live external services, visual verification, or production-like environments.
> Automated equivalents exist for most logic; these tests cover the remainder.

---

## Table of Contents

1. [Authentication & User Management](#1-authentication--user-management)
2. [SEO Audit Tool](#2-seo-audit-tool)
3. [PDF Report Generation & Email](#3-pdf-report-generation--email)
4. [Subscription & Payment Flow](#4-subscription--payment-flow)
5. [Keyword AI Suggestions](#5-keyword-ai-suggestions)
6. [Comparative Analysis](#6-comparative-analysis)
7. [Admin Panel](#7-admin-panel)
8. [UI / UX & Responsiveness](#8-ui--ux--responsiveness)
9. [Performance & Caching](#9-performance--caching)
10. [Security Testing](#10-security-testing)
11. [Email Delivery](#11-email-delivery)
12. [Edge Cases & Boundary Conditions](#12-edge-cases--boundary-conditions)

---

## 1. Authentication & User Management

### TC-AUTH-001 — Standard Registration
**Priority:** Critical  
**Steps:**
1. Navigate to `/register/`
2. Fill in valid username, email, password (≥ 8 chars with uppercase + number)
3. Submit form
**Expected:** User created, redirected to home/login, welcome message shown.
**Verify:** Check Django admin that User, Profile, Subscription (free), and UsageTracker were all created.

### TC-AUTH-002 — Duplicate Username Registration
**Priority:** High  
**Steps:**
1. Register user "john123"
2. Try to register another user with username "john123"
**Expected:** Error message "username already taken" shown. Only one user in DB.

### TC-AUTH-003 — Login with Valid Credentials
**Priority:** Critical  
**Steps:**
1. Navigate to `/`
2. Enter valid username and password
3. Submit
**Expected:** Redirected to `/home/`, user session active, username visible in navbar.

### TC-AUTH-004 — Login with Invalid Password
**Priority:** High  
**Steps:**
1. Navigate to `/`
2. Enter correct username, wrong password
**Expected:** Error message shown. User NOT logged in. No session created.

### TC-AUTH-005 — Password Reset Flow (Email Required)
**Priority:** High  
**Steps:**
1. Navigate to `/forget-password/`
2. Enter registered email address
3. Submit
4. Check inbox for reset email
5. Click reset link
6. Enter and confirm new password
7. Login with new password
**Expected:** Full reset cycle works. Old password no longer works. Token invalidated after use.
**Verify:** `Profile.forget_password_token` is cleared/changed after use.

### TC-AUTH-006 — Logout Clears Session
**Priority:** High  
**Steps:**
1. Login as any user
2. Click Logout
3. Try to navigate to `/home/`
**Expected:** Redirected to login page. Session cookie cleared.

### TC-AUTH-007 — Already Logged In User Visits Login Page
**Priority:** Medium  
**Steps:**
1. Login as user A
2. Navigate to `/`
**Expected:** Either redirected to `/home/` OR shown login form (check actual behavior, document it).

---

## 2. SEO Audit Tool

### TC-SEO-001 — Valid URL Audit (HTTPS Site)
**Priority:** Critical  
**Steps:**
1. Login with Pro subscription
2. Navigate to `/home/`
3. Enter `https://example.com`
4. Submit
**Expected:** Results page loads with:
- Title, meta description, scores
- Radar chart visible and animated
- Priority issues listed
- All score rings populated

### TC-SEO-002 — Valid URL Audit (HTTP Site)
**Priority:** High  
**Steps:**
1. Enter `http://example.com` in the audit form
**Expected:** Audit completes; HTTPS flag shows "Not secure". All other metrics populated.

### TC-SEO-003 — Audit with Slow-Loading Site
**Priority:** Medium  
**Steps:**
1. Enter URL of a known slow site (e.g., one with many resources)
**Expected:** Audit completes without timeout error. Page speed score reflects slow load time.

### TC-SEO-004 — Audit with Unreachable URL
**Priority:** High  
**Steps:**
1. Enter `https://this-url-does-not-exist-at-all-12345.com`
**Expected:** Graceful error message shown. No crash. No 500 error page.

### TC-SEO-005 — Audit Blocked After Free Trial Used
**Priority:** Critical  
**Steps:**
1. Register new user (free tier)
2. Run first audit (should succeed)
3. Run second audit
**Expected:** Second audit redirects to `/subscriptions/pricing/`. No audit runs.

### TC-SEO-006 — Audit Counter Accuracy
**Priority:** High  
**Steps:**
1. Login with Basic plan (10 audits/month)
2. Check `/subscriptions/dashboard/` — note current count
3. Run 1 audit
4. Check dashboard again
**Expected:** Counter increased by exactly 1.

### TC-SEO-007 — Keyword Density Display
**Priority:** Medium  
**Steps:**
1. Run audit on content-rich page
**Expected:** Keyword density list shown with percentage values. No negative or >100% values.

### TC-SEO-008 — Mobile-Friendliness Tool
**Priority:** Medium  
**Steps:**
1. Navigate to `/mobiletest/`
2. Enter a mobile-optimized URL
3. Submit
**Expected:** Mobile score > 70. Viewport and responsive design flags shown.

### TC-SEO-009 — robots.txt Checker
**Priority:** Medium  
**Steps:**
1. Navigate to `/robot/`
2. Enter URL with a robots.txt file
3. Enter URL without a robots.txt file
**Expected:** First shows parsed content. Second shows "not found" message.

### TC-SEO-010 — Grammar Analyzer on Content-Heavy Page
**Priority:** Medium  
**Steps:**
1. Run SEO audit on a page with known grammar errors
**Expected:** Grammar errors section shows detected issues. No false positives on correct sentences.

---

## 3. PDF Report Generation & Email

### TC-RPT-001 — PDF Download (Basic+ Plan)
**Priority:** Critical  
**Steps:**
1. Login with Basic plan
2. Run an audit
3. Click "Download PDF Report"
**Expected:** PDF file downloaded. File opens correctly. Contains audit data matching screen.

### TC-RPT-002 — PDF Email Send
**Priority:** High  
**Steps:**
1. Login with Pro plan
2. Run an audit
3. Click "Send Report to Email"
**Expected:** Success message shown. Email arrives in registered inbox. PDF attachment present.

### TC-RPT-003 — PDF Blocked for Free User
**Priority:** Critical  
**Steps:**
1. Login with free account (trial used)
2. Navigate to `/report/download/`
**Expected:** Redirected to pricing page. No PDF generated.

### TC-RPT-004 — PDF Cache Miss (Re-runs Audit)
**Priority:** Medium  
**Steps:**
1. Login, run audit, wait >1 hour (or clear cache manually)
2. Click "Download PDF"
**Expected:** Audit re-runs automatically. PDF generated with fresh data.

### TC-RPT-005 — PDF Contains Keyword AI Data
**Priority:** Medium  
**Steps:**
1. Login with Pro plan
2. Run audit on content-rich URL
3. Download PDF
**Expected:** PDF includes keyword suggestions section populated from `keyword_ai` pipeline.

---

## 4. Subscription & Payment Flow

### TC-SUB-001 — View Pricing Page
**Priority:** High  
**Steps:**
1. Login as any user
2. Navigate to `/subscriptions/pricing/`
**Expected:** 4 tiers shown (Free, Basic, Pro, Enterprise). Current plan highlighted. Prices correct.

### TC-SUB-002 — Select Free Plan (Immediate Activation)
**Priority:** High  
**Steps:**
1. Login as user with no active subscription
2. Go to pricing → Select "Free"
3. Submit
**Expected:** Subscription immediately activated. No payment form shown. Redirected to dashboard.

### TC-SUB-003 — Select Paid Plan → Bank Transfer Instructions
**Priority:** Critical  
**Steps:**
1. Login
2. Go to pricing → Select "Pro - Monthly"
**Expected:** Payment instructions page shows:
- Bank name, account number, IBAN from `.env`
- Unique reference code: `WEBLIFT-{user_id}-{timestamp}`
- Correct amount ($29.00)

### TC-SUB-004 — Submit Payment Proof
**Priority:** Critical  
**Steps:**
1. Fill payment proof form: sender name, transaction reference, date, amount
2. Optionally upload a screenshot file
3. Submit
**Expected:** Confirmation page shown with reference number. `ManualPaymentSubmission` record created with `status=pending`. User sees "Pending verification" on dashboard.

### TC-SUB-005 — Upload Oversized Proof Document
**Priority:** Medium  
**Steps:**
1. Try to upload a file > 10MB as payment proof
**Expected:** File size validation error shown. Submission not created.

### TC-SUB-006 — Admin Verifies Payment
**Priority:** Critical  
**Steps:**
1. Login as admin
2. Go to `/subscriptions/admin/pending-payments/`
3. Find the pending submission
4. Click "Verify"
**Expected:** Subscription upgraded to paid tier. `current_period_end` = today + 30 days. User can now use paid features.

### TC-SUB-007 — Admin Rejects Payment
**Priority:** High  
**Steps:**
1. Login as admin
2. Find pending submission → Click "Reject" with notes
**Expected:** Submission status = "rejected". User subscription NOT upgraded. User sees rejection on dashboard.

### TC-SUB-008 — Cancel Active Subscription
**Priority:** High  
**Steps:**
1. Login with active Pro subscription
2. Go to `/subscriptions/cancel/`
3. Confirm cancellation
**Expected:** `Subscription.status = 'canceled'`. User loses access to Pro features on next action check.

### TC-SUB-009 — Yearly Billing — 365-Day Period
**Priority:** Medium  
**Steps:**
1. Select Pro plan — Yearly billing
2. Admin verifies
**Expected:** `current_period_end` = today + 365 days. Price shown as $290 (yearly rate).

### TC-SUB-010 — Feature Access Log Audit Trail
**Priority:** Low  
**Steps:**
1. Login as free user
2. Try to access `/report/download/` (blocked)
3. Check Django admin → FeatureAccessLog
**Expected:** Log entry created with: user, feature=pdf_export, access_granted=False, reason shown.

---

## 5. Keyword AI Suggestions

### TC-KW-001 — Keyword Suggestions via UI
**Priority:** Critical  
**Steps:**
1. Login with Pro subscription
2. Navigate to `/keyword-ai-suggestions/`
3. Enter a URL and submit
**Expected:** List of keyword suggestions with relevance scores, intent labels, priority badges.

### TC-KW-002 — Keyword Clusters Displayed
**Priority:** High  
**Steps:**
1. Run keyword AI on content-rich URL
**Expected:** Keywords grouped by cluster/intent. Headings like "Informational", "Transactional" visible.

### TC-KW-003 — Accept/Reject Feedback Buttons
**Priority:** High  
**Steps:**
1. Run keyword AI
2. Click "Accept" on one keyword
3. Click "Reject" on another
**Expected:** Visual feedback (button state change). DB updated: `is_accepted=True` / `is_rejected=True`.

### TC-KW-004 — Export Keywords as CSV
**Priority:** Medium  
**Steps:**
1. Run keyword AI
2. Click "Export CSV"
**Expected:** CSV file downloaded. Contains keyword, score, intent, priority columns. No empty rows.

### TC-KW-005 — Export Keywords as JSON
**Priority:** Medium  
**Steps:**
1. Run keyword AI
2. Click "Export JSON"
**Expected:** Valid JSON file downloaded. Parseable. Contains same data as CSV.

### TC-KW-006 — LLM-Generated Keyword Variants
**Priority:** High  
**Steps:**
1. Run keyword AI with `USE_GROQ=true` in environment
**Expected:** LLM keywords section populated with question-form keywords ("How to...", "What is..."). Different from TF-IDF keywords.

### TC-KW-007 — Keyword AI Blocked for Free User
**Priority:** Critical  
**Steps:**
1. Login as free user (trial used)
2. Navigate to `/keyword-ai-suggestions/`
**Expected:** Redirected to pricing page. No pipeline runs.

### TC-KW-008 — Batch Analysis via API (Celery)
**Priority:** Medium  
**Steps:**
1. Submit POST to `/api/keywords/batch/` with 3 URLs
2. Poll `/api/keywords/tasks/{id}/` every 5 seconds
**Expected:** Task progresses from `pending` → `processing` → `completed`. Results populated in DB.

---

## 6. Comparative Analysis

### TC-COMP-001 — Side-by-Side Comparison
**Priority:** Critical  
**Steps:**
1. Login with Pro subscription
2. Navigate to `/comparative-analysis/`
3. Enter primary URL and competitor URL
4. Enter optional target keyword
5. Submit
**Expected:** Results page shows side-by-side score bars, keyword placement table, E-E-A-T comparison, technical comparison.

### TC-COMP-002 — LLM Ranking Explanation
**Priority:** High  
**Steps:**
1. Run comparison with `USE_GROQ=true`
**Expected:** "Why competitor ranks higher" section populated with structured reasons and recommendations from LLM.

### TC-COMP-003 — Same URL for Both Inputs
**Priority:** Medium  
**Steps:**
1. Enter same URL in both "Your URL" and "Competitor URL" fields
**Expected:** Either validation error shown OR comparison completes with all scores equal.

### TC-COMP-004 — Comparison with Unreachable URL
**Priority:** High  
**Steps:**
1. Enter unreachable URL as competitor
**Expected:** Graceful error. Primary URL results shown if possible, or error message. No 500 crash.

### TC-COMP-005 — Results Persist After Session Expiry
**Priority:** Medium  
**Steps:**
1. Run comparison, note the result URL `/comparative-analysis/results/{id}/`
2. Close browser (clear session)
3. Login again, navigate to the saved URL
**Expected:** Results page loads from DB (scores visible, detailed breakdown may be limited — per Known Quirks).

### TC-COMP-006 — Moz API Integration (if enabled)
**Priority:** Medium  
**Steps:**
1. Set `USE_MOZ_API=true`, configure valid API key
2. Run comparison on two real domains
**Expected:** Domain Authority, Page Authority, Backlink data populated. Not "N/A".

### TC-COMP-007 — Comparison Blocked for Basic User
**Priority:** High  
**Steps:**
1. Login with Basic plan
2. Try to access `/comparative-analysis/analyze/`
**Expected:** Redirected to pricing page. Note: currently this gate is not wired in code (see Known Quirks).

---

## 7. Admin Panel

### TC-ADMIN-001 — Access Admin Panel
**Priority:** High  
**Steps:**
1. Login as superuser
2. Navigate to `/admin/`
**Expected:** Django admin panel loads. All registered models visible.

### TC-ADMIN-002 — Bulk Verify Payments
**Priority:** High  
**Steps:**
1. Create 3 pending payment submissions
2. Select all in admin
3. Choose "Verify selected payments and activate subscriptions"
**Expected:** All 3 subscriptions activated. `PaymentRecord` created for each.

### TC-ADMIN-003 — Bulk Reject Payments
**Priority:** Medium  
**Steps:**
1. Select multiple pending payments
2. Choose "Reject selected payments"
**Expected:** All selected set to `rejected`. No subscriptions changed.

### TC-ADMIN-004 — Edit Subscription Tier Limits
**Priority:** Medium  
**Steps:**
1. In admin, edit "Basic" tier `max_audits_per_month` from 10 to 15
2. Save
3. Login as Basic user, check dashboard
**Expected:** Dashboard shows new limit of 15 audits.

### TC-ADMIN-005 — Reset User Usage Manually
**Priority:** Low  
**Steps:**
1. In admin, edit a UsageTracker record
2. Set `audits_used_this_month = 0`
3. Save
**Expected:** User can run audits again (if within limit).

### TC-ADMIN-006 — FeatureAccessLog View
**Priority:** Low  
**Steps:**
1. As free user, attempt PDF download (blocked)
2. Go to admin → FeatureAccessLog
**Expected:** Entry visible with correct user, feature name, `access_granted=False`.

---

## 8. UI / UX & Responsiveness

### TC-UI-001 — Dashboard Radar Chart
**Priority:** Medium  
**Steps:**
1. Run any SEO audit
2. Inspect the radar/spider chart on results page
**Expected:** Chart renders correctly in Chrome, Firefox, Safari. 5 dimensions labeled. Responsive on mobile.

### TC-UI-002 — Score Ring Animation
**Priority:** Low  
**Steps:**
1. Run audit
2. Observe the circular score ring on results page
**Expected:** SVG ring animates on page load. Score value displayed in center.

### TC-UI-003 — Mobile Responsive Layout
**Priority:** High  
**Steps:**
1. Open the platform on a mobile device (or browser devtools mobile emulation)
2. Test: login, home, audit results, pricing, dashboard
**Expected:** All pages readable without horizontal scroll. Buttons tappable. Navigation accessible.

### TC-UI-004 — Dark Mode / Browser Theming
**Priority:** Low  
**Steps:**
1. Enable OS dark mode
2. Browse the platform
**Expected:** No white-on-white or black-on-black text issues. (Note: dedicated dark mode may not be implemented.)

### TC-UI-005 — Priority Issues Color Coding
**Priority:** Medium  
**Steps:**
1. Run audit on a page with known issues
**Expected:** Critical issues shown in red, warnings in orange/yellow, info in blue/green.

---

## 9. Performance & Caching

### TC-PERF-001 — Audit Result Caching (1-Hour TTL)
**Priority:** High  
**Steps:**
1. Run audit on URL X
2. Note response time
3. Run audit on URL X again immediately
**Expected:** Second audit response is faster (served from cache). Cache-Control headers visible in devtools.

### TC-PERF-002 — Pricing Page Cache (30-Minute TTL)
**Priority:** Low  
**Steps:**
1. Load `/subscriptions/pricing/`
2. In admin, change a tier price
3. Reload pricing page within 30 minutes
**Expected:** Old price still shown (cached). After 30 min, new price reflected.

### TC-PERF-003 — Concurrent Audit Requests
**Priority:** Medium  
**Steps:**
1. Use a load testing tool (e.g., Locust) to fire 10 simultaneous audit requests
**Expected:** No race conditions in `UsageTracker` counter. Each request either succeeds or is correctly gated.

### TC-PERF-004 — Report Cache Reuse
**Priority:** Medium  
**Steps:**
1. Run audit, then immediately click "Download PDF"
**Expected:** PDF uses cached audit data (no second network fetch). Audit count NOT incremented again for the PDF download.

---

## 10. Security Testing

### TC-SEC-001 — CSRF Protection on All Forms
**Priority:** Critical  
**Steps:**
1. Use a tool (e.g., curl) to POST to `/show/` without CSRF token
**Expected:** 403 Forbidden. Form not processed.

### TC-SEC-002 — SQL Injection in URL Input
**Priority:** Critical  
**Steps:**
1. Enter `https://example.com/' OR '1'='1` in audit URL field
**Expected:** Input sanitized. No DB error. Audit either runs normally or shows validation error.

### TC-SEC-003 — XSS in Keyword Input
**Priority:** Critical  
**Steps:**
1. In keyword position checker, enter `<script>alert('xss')</script>`
**Expected:** Script NOT executed. Input escaped in HTML output.

### TC-SEC-004 — Direct Access to Admin Payment Views
**Priority:** Critical  
**Steps:**
1. Login as non-staff user
2. Navigate to `/subscriptions/admin/pending-payments/`
**Expected:** 302 redirect to login OR 403 Forbidden. Page NOT accessible.

### TC-SEC-005 — Password Reset Token Reuse
**Priority:** High  
**Steps:**
1. Generate a password reset token for user
2. Use it to change password
3. Try to use the same token again
**Expected:** Token invalid/expired on second use. Password not changed.

### TC-SEC-006 — Payment Proof File Upload — Malicious File
**Priority:** High  
**Steps:**
1. Try to upload a `.php` or `.exe` file as payment proof
**Expected:** File type validation rejects it. Only images/PDFs accepted.

### TC-SEC-007 — Forced Browsing to Other User's Report
**Priority:** High  
**Steps:**
1. Login as User A, get a comparison report ID
2. Login as User B, navigate to `/comparative-analysis/results/{User_A_report_id}/`
**Expected:** Either 404 or the report is visible (since reports are not user-scoped per the model). Document current behavior.

### TC-SEC-008 — Rate Limiting on Login
**Priority:** Medium  
**Steps:**
1. Make 20 rapid failed login attempts
**Expected:** Either rate limiting triggers (if configured) OR CAPTCHA shown. Document actual behavior.

---

## 11. Email Delivery

### TC-EMAIL-001 — Password Reset Email Received
**Priority:** High  
**Steps:**
1. Submit forget-password form with real email
**Expected:** Email received within 2 minutes. Contains reset link with valid token. Link goes to correct URL.

### TC-EMAIL-002 — Audit Report Email Delivery
**Priority:** High  
**Steps:**
1. Run audit, click "Send Report to Email"
**Expected:** Email received with PDF attachment. Subject includes site name. Body has summary.

### TC-EMAIL-003 — Email to Non-Registered Address
**Priority:** Medium  
**Steps:**
1. Submit forget-password form with an email not in the system
**Expected:** No error shown to user (security: don't reveal if email exists). No email sent (or a generic "if registered" message shown).

---

## 12. Edge Cases & Boundary Conditions

### TC-EDGE-001 — URL with Query Parameters
**Priority:** Medium  
**Steps:**
1. Enter `https://example.com/page?utm_source=test&id=123` in audit form
**Expected:** Audit runs successfully. URL handled correctly in cache key generation.

### TC-EDGE-002 — Internationalized Domain Name (IDN)
**Priority:** Low  
**Steps:**
1. Enter a URL with non-ASCII characters (e.g., `https://münchen.de`)
**Expected:** Either proper handling OR graceful error. No UnicodeDecodeError.

### TC-EDGE-003 — Very Long URL (> 2000 chars)
**Priority:** Low  
**Steps:**
1. Construct a URL exceeding 2000 characters and submit
**Expected:** Validation error or truncation. No DB constraint violation.

### TC-EDGE-004 — Enterprise User — Unlimited Audits
**Priority:** Medium  
**Steps:**
1. Login as Enterprise user
2. Set `audits_used_this_month = 500` in DB
3. Try to run an audit
**Expected:** Audit allowed. No "limit reached" message.

### TC-EDGE-005 — Audit Result With Missing SSL
**Priority:** Medium  
**Steps:**
1. Audit an HTTP-only site (no SSL)
**Expected:** SSL fields show "Not Available" or equivalent. No `AttributeError` on cert data.

### TC-EDGE-006 — Comparative Analysis with No Target Keyword
**Priority:** Medium  
**Steps:**
1. Submit comparative analysis without filling the "Target Keyword" field
**Expected:** Analysis completes using auto-detected keywords. Results page loads normally.

### TC-EDGE-007 — Dashboard With Zero Usage
**Priority:** Low  
**Steps:**
1. View `/subscriptions/dashboard/` for a brand-new user
**Expected:** All counters show 0. Progress bars at 0%. No division-by-zero errors.

### TC-EDGE-008 — Multiple Browser Tabs — Same Audit
**Priority:** Low  
**Steps:**
1. Open two tabs, both logged in as same Pro user
2. Submit audit from both simultaneously
**Expected:** `audits_used_this_month` incremented by 2 (not 1). No race condition corruption.

---

## Test Execution Checklist

Before each release, mark these as PASS / FAIL / SKIP:

| ID | Title | Priority | Status | Notes |
|----|-------|----------|--------|-------|
| TC-AUTH-001 | Standard Registration | Critical | — | |
| TC-AUTH-003 | Login Valid Credentials | Critical | — | |
| TC-AUTH-005 | Password Reset Flow | High | — | |
| TC-SEO-001 | Valid URL Audit | Critical | — | |
| TC-SEO-005 | Free Trial Gate | Critical | — | |
| TC-RPT-001 | PDF Download | Critical | — | |
| TC-RPT-003 | PDF Blocked Free User | Critical | — | |
| TC-SUB-003 | Bank Transfer Instructions | Critical | — | |
| TC-SUB-006 | Admin Verifies Payment | Critical | — | |
| TC-KW-001 | Keyword Suggestions UI | Critical | — | |
| TC-KW-007 | Keyword AI Blocked Free | Critical | — | |
| TC-COMP-001 | Side-by-Side Comparison | Critical | — | |
| TC-SEC-001 | CSRF Protection | Critical | — | |
| TC-SEC-004 | Admin View Access Control | Critical | — | |

---

*Last updated: May 2026*
