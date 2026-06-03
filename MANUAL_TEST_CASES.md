# WebLift - Manual Test Cases (Table Format)

## Legend
- **P:** Priority (C=Critical, H=High, M=Medium, L=Low)
- **Status:** ☐ = Not tested, ☑ = Pass, ☒ = Fail

---

## 1. Authentication (24 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-AUTH-001 | Valid Registration | C | Fill register form with valid data | Account created, redirected to home | ☐ |
| TC-AUTH-002 | Duplicate Username | H | Register with existing username | Error: "Username already taken" | ☐ |
| TC-AUTH-003 | Password Mismatch | H | Enter different passwords | Error: Passwords don't match | ☐ |
| TC-AUTH-004 | Weak Password | M | Enter short password (123) | Validation error for password strength | ☐ |
| TC-AUTH-005 | Valid Login | C | Enter correct credentials | Redirected to /home/, session created | ☐ |
| TC-AUTH-006 | Invalid Password | H | Correct user, wrong password | Error: "Invalid credentials" | ☐ |
| TC-AUTH-007 | Non-existent User | H | Enter unknown username | Error: "Invalid credentials" | ☐ |
| TC-AUTH-008 | Empty Login Fields | M | Submit empty form | Validation error for required fields | ☐ |
| TC-AUTH-009 | Logout | C | Click logout | Session cleared, redirected to / | ☐ |
| TC-AUTH-010 | Forgot Password Valid | H | Enter registered email | Reset email sent, token stored | ☐ |
| TC-AUTH-011 | Forgot Password Invalid | M | Enter unknown email | Generic success message (security) | ☐ |
| TC-AUTH-012 | Change Password Valid | H | Use valid reset token | Password updated, token invalidated | ☐ |
| TC-AUTH-013 | Change Password Invalid | H | Use invalid/expired token | Error: "Invalid or expired token" | ☐ |
| TC-AUTH-014 | Session Persistence | M | Close browser, reopen | User still logged in (if remember me) | ☐ |
| TC-AUTH-015 | Invalid Email Format | M | Enter email: "invalid-email" | Validation error for email format | ☐ |
| TC-AUTH-016 | Username Special Chars | M | Enter username: "user@#$%" | Validation error or sanitized | ☐ |
| TC-AUTH-017 | Very Long Username | L | Enter 50+ character username | Validation error or truncated | ☐ |
| TC-AUTH-018 | Case Sensitivity | H | Username "TestUser" vs "testuser" | Treated as different users | ☐ |
| TC-AUTH-019 | Password Reuse Check | H | Try changing to same password | Error: "Cannot reuse old password" | ☐ |
| TC-AUTH-020 | Login After Password Change | C | Login with old password after change | Login fails, new password required | ☐ |
| TC-AUTH-021 | Multiple Failed Logins | H | Enter wrong password 5 times | Account temporarily locked or warning | ☐ |
| TC-AUTH-022 | Blank Space Only | M | Enter spaces for username | Validation error, not accepted | ☐ |
| TC-AUTH-023 | Unicode Username | M | Enter username with emojis | Accepted or proper error shown | ☐ |
| TC-AUTH-024 | Email Verification Flow | H | Register and verify email | Verification email sent, account activated | ☐ |

---

## 2. SEO Audit (30 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-SEO-001 | HTTP Site Audit | C | Analyze http://example.com | Audit completes, results displayed | ☐ |
| TC-SEO-002 | HTTPS Site Audit | C | Analyze https://example.com | Audit completes with all metrics | ☐ |
| TC-SEO-003 | Invalid URL | H | Enter "not-a-valid-url" | Error: "Invalid URL format" | ☐ |
| TC-SEO-004 | Empty URL | H | Submit empty URL field | Validation: "URL is required" | ☐ |
| TC-SEO-005 | Unreachable Site | H | Enter non-existent domain | Error: "Could not reach URL" | ☐ |
| TC-SEO-006 | JavaScript-Heavy Site | M | Analyze SPA website | Completes without timeout/crash | ☐ |
| TC-SEO-007 | SEO Metrics Display | C | View audit results | Scores (0-100), radar chart visible | ☐ |
| TC-SEO-008 | PDF Export | H | Click download PDF | PDF generated and downloaded | ☐ |
| TC-SEO-009 | PDF Without Feature | H | Free user tries PDF export | Redirected to pricing/upgrade prompt | ☐ |
| TC-SEO-010 | Mobile Test | H | Enter URL in /mobiletest/ | Mobile compatibility results shown | ☐ |
| TC-SEO-011 | Robots.txt Analysis | M | Enter URL in /robot/ | Robots.txt content displayed | ☐ |
| TC-SEO-012 | Keyword Position | M | Enter keyword + URL | Search position displayed | ☐ |
| TC-SEO-013 | Keyword Suggestions | M | Enter seed keyword | Keyword list generated | ☐ |
| TC-SEO-014 | Sentiment Analysis | M | Enter URL, select mode | Sentiment score displayed | ☐ |
| TC-SEO-015 | SEO Metrics Page | M | Navigate to /seo-metrics/ | Metrics and charts loaded | ☐ |
| TC-SEO-016 | URL with Port | M | Enter http://site.com:8080 | Audit works or proper error | ☐ |
| TC-SEO-017 | URL with Auth | M | Enter http://user:pass@site.com | Credentials stripped or error | ☐ |
| TC-SEO-018 | FTP Protocol | L | Enter ftp://ftp.example.com | Error: "Unsupported protocol" | ☐ |
| TC-SEO-019 | File Protocol | L | Enter file:///etc/passwd | Error: "Invalid URL" | ☐ |
| TC-SEO-020 | Timeout Handling | H | Analyze extremely slow site | Graceful timeout after 30s | ☐ |
| TC-SEO-021 | Redirect Chain | M | Site with 5+ redirects | Follows redirects, final result | ☐ |
| TC-SEO-022 | SSL Certificate Error | M | Site with expired SSL | Error or warning about certificate | ☐ |
| TC-SEO-023 | Cloudflare/Protected | M | Analyze Cloudflare-protected site | Returns available data or error | ☐ |
| TC-SEO-024 | Empty HTML Page | M | Analyze page with no content | Handles gracefully, low scores | ☐ |
| TC-SEO-025 | Binary File URL | L | Enter .pdf or .jpg URL | Error or limited analysis | ☐ |
| TC-SEO-026 | 500 Error Site | M | Analyze site returning 500 | Error: "Server error" displayed | ☐ |
| TC-SEO-027 | Infinite Redirect | H | Site with redirect loop | Detects loop, error shown | ☐ |
| TC-SEO-028 | Very Large Page | M | Page > 10MB HTML | Handles without memory crash | ☐ |
| TC-SEO-029 | International Domain | M | https://münchen.de (IDN) | Correctly punycode converted | ☐ |
| TC-SEO-030 | Duplicate Audit Request | M | Submit same URL twice quickly | Second shows cached or in-progress | ☐ |

---

## 3. Subscription (20 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-SUB-001 | Pricing Page | C | View /subscriptions/pricing/ | All tiers displayed with features | ☐ |
| TC-SUB-002 | Free Tier Limits | C | Free user tries premium feature | Upgrade prompt shown, restricted | ☐ |
| TC-SUB-003 | Payment Instructions | H | Select paid plan | Bank details and reference shown | ☐ |
| TC-SUB-004 | Submit Payment Proof | H | Fill and submit payment form | Submission confirmed, status pending | ☐ |
| TC-SUB-005 | Dashboard | H | View /subscriptions/dashboard/ | Plan, usage, billing info displayed | ☐ |
| TC-SUB-006 | Usage Tracking | H | Perform audits, check dashboard | Audit count increments correctly | ☐ |
| TC-SUB-007 | Usage Limit Reached | H | Try audit at limit | Upgrade prompt, audit blocked | ☐ |
| TC-SUB-008 | Change Plan | M | Select different tier | Plan updated, features changed | ☐ |
| TC-SUB-009 | Cancel Subscription | M | Confirm cancellation | Cancelled, access until period end | ☐ |
| TC-SUB-010 | API Usage | L | Access /subscriptions/api/usage/ | JSON usage data returned | ☐ |
| TC-SUB-011 | Double Payment Submit | H | Click submit twice rapidly | Single submission, no duplicates | ☐ |
| TC-SUB-012 | Expired Subscription | H | Use features after expiry | Redirected to renew or limited | ☐ |
| TC-SUB-013 | Plan Downgrade | M | Change from Pro to Basic | Features restricted, data preserved | ☐ |
| TC-SUB-014 | Usage Reset | M | Start new billing period | Counters reset to zero | ☐ |
| TC-SUB-015 | Payment File Upload Large | M | Upload 50MB proof file | Error: "File too large" | ☐ |
| TC-SUB-016 | Payment Wrong File Type | M | Upload .exe as proof | Error: "Invalid file type" | ☐ |
| TC-SUB-017 | Concurrent Plan Change | L | Change plan from two devices | Last change wins or error | ☐ |
| TC-SUB-018 | Free Trial Reset | H | Try free audit after using it | Upgrade required, trial used | ☐ |
| TC-SUB-019 | Negative Usage | L | Tamper to show negative count | Validation prevents, shows 0 | ☐ |
| TC-SUB-020 | Subscription Webhook Fail | M | Webhook timeout during renewal | Graceful handling, retry logic | ☐ |

---

## 4. Admin (10 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-ADMIN-001 | Pending Payments | H | Staff views pending payments | List displayed with verify/reject buttons | ☐ |
| TC-ADMIN-002 | Verify Payment | H | Click verify, add notes | Status verified, subscription activated | ☐ |
| TC-ADMIN-003 | Reject Payment | H | Click reject, add reason | Status rejected, user notified | ☐ |
| TC-ADMIN-004 | Non-Admin Access | H | Regular user tries admin URL | 403 Forbidden or redirect | ☐ |
| TC-ADMIN-005 | Bulk Payment Verify | M | Verify multiple payments at once | All processed, no partial updates | ☐ |
| TC-ADMIN-006 | Payment Photo Preview | L | Click to view proof document | Modal/preview opens correctly | ☐ |
| TC-ADMIN-007 | Admin Action Audit Log | M | Verify a payment | Log entry created with admin name | ☐ |
| TC-ADMIN-008 | Rejected Payment Re-submit | H | User resubmits rejected payment | New pending entry created | ☐ |
| TC-ADMIN-009 | Duplicate Verification | M | Try to verify already verified | Error or no-op, idempotent | ☐ |
| TC-ADMIN-010 | Admin Logout Mid-Action | L | Click verify then logout before finish | Action cancelled or completed | ☐ |

---

## 5. Keyword AI (20 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-KAI-001 | AI Suggestions Page | C | Navigate to keyword suggestions | Interface loads with URL input | ☐ |
| TC-KAI-002 | Suggestions V2 | H | Enter URL in v2 endpoint | Results with relevance scores | ☐ |
| TC-KAI-003 | Streaming | M | Start streaming analysis | Real-time results appear | ☐ |
| TC-KAI-004 | Submit Feedback | M | Rate a keyword thumbs up/down | Feedback recorded, confirmation shown | ☐ |
| TC-KAI-005 | Export Results | M | Click export, select format | File downloads in selected format | ☐ |
| TC-KAI-006 | Async Analysis | H | Submit async request | Task ID returned, status checkable | ☐ |
| TC-KAI-007 | Batch Analysis | M | Submit multiple URLs | Batch job created, progress tracked | ☐ |
| TC-KAI-008 | Task Status | M | Check task status endpoint | Current status and progress shown | ☐ |
| TC-KAI-009 | Analytics Dashboard | L | View analytics dashboard | Stats and performance metrics shown | ☐ |
| TC-KAI-010 | Traffic Analysis | M | Enter URL for traffic analysis | Traffic signals and recommendations | ☐ |
| TC-KAI-011 | Empty URL Analysis | H | Submit empty URL to analyze | Validation error, no crash | ☐ |
| TC-KAI-012 | Malformed URL | M | Enter "not a url" in analysis | Error: "Invalid URL format" | ☐ |
| TC-KAI-013 | API Key Missing | H | Call API without auth header | 401 Unauthorized | ☐ |
| TC-KAI-014 | Rate Limit Exceeded | H | Submit 100+ rapid requests | 429 Too Many Requests | ☐ |
| TC-KAI-015 | Invalid Task ID | M | Check status of fake task ID | Error: "Task not found" | ☐ |
| TC-KAI-016 | Export Empty Results | M | Export with no keywords | Empty file or error message | ☐ |
| TC-KAI-017 | Cancel Async Task | M | Cancel running analysis | Task stopped, status cancelled | ☐ |
| TC-KAI-018 | Batch with Invalid URLs | M | Mix valid and invalid URLs | Valid processed, errors logged | ☐ |
| TC-KAI-019 | Feedback Spam | L | Submit 1000+ feedback rapidly | Rate limited or blocked | ☐ |
| TC-KAI-020 | LLM API Failure | H | Groq API returns 500 | Fallback or graceful error | ☐ |

---

## 6. Comparative Analysis (14 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-COMP-001 | Input Form | C | Navigate to /comparative-analysis/ | Form with URL and keyword fields | ☐ |
| TC-COMP-002 | Run Comparison | C | Enter URLs and keyword, submit | Analysis runs, results page loads | ☐ |
| TC-COMP-003 | View Results | C | Access results page | Side-by-side comparison, gaps shown | ☐ |
| TC-COMP-004 | Without Feature | H | Free user tries to access | Upgrade prompt, feature restricted | ☐ |
| TC-COMP-005 | Invalid URL | M | Enter invalid primary URL | Validation error on specific field | ☐ |
| TC-COMP-006 | Same URL Both | L | Enter same URL for both sites | Warning or graceful handling | ☐ |
| TC-COMP-007 | Subdomain vs Root | M | Compare blog.site.com vs site.com | Different scores, valid comparison | ☐ |
| TC-COMP-008 | HTTP vs HTTPS Same | M | http vs https of same domain | Detects as same or different | ☐ |
| TC-COMP-009 | Empty Keyword | H | Leave keyword field empty | Validation: "Keyword required" | ☐ |
| TC-COMP-010 | Very Long Keyword | M | Enter 100+ character keyword | Handled or truncated | ☐ |
| TC-COMP-011 | Non-Latin Keyword | M | Enter keyword in Chinese/Arabic | UTF-8 handling, results shown | ☐ |
| TC-COMP-012 | Competitor Not Indexed | M | Competitor URL not in search | Error or "Not found" result | ☐ |
| TC-COMP-013 | Report Expired | L | Access old report after 30 days | Archived or regenerated | ☐ |
| TC-COMP-014 | Concurrent Comparison | L | Start 5 comparisons at once | All queue properly, no crash | ☐ |

---

## 7. UI/UX (18 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-UI-001 | Desktop Layout | H | View on 1920x1080 | Elements aligned, nav visible | ☐ |
| TC-UI-002 | Tablet Layout | H | View on 768x1024 | Responsive layout, menu accessible | ☐ |
| TC-UI-003 | Mobile Layout | H | View on 375x667 | Mobile optimized, touch-friendly | ☐ |
| TC-UI-004 | Navigation | H | Click each menu item | All links work, active page highlighted | ☐ |
| TC-UI-005 | Form Validation | M | Submit form with errors | Error fields highlighted red | ☐ |
| TC-UI-006 | Loading States | M | Trigger long operation | Loading spinner shown, no freeze | ☐ |
| TC-UI-007 | 404 Page | M | Access non-existent page | Branded 404 with home link | ☐ |
| TC-UI-008 | Dark Mode | L | Toggle dark mode | Theme applies consistently | ☐ |
| TC-UI-009 | Zoom 200% | M | Browser zoom to 200% | Layout intact, readable | ☐ |
| TC-UI-010 | Print Stylesheet | L | Print preview of report | Print-friendly layout shown | ☐ |
| TC-UI-011 | Browser Back/Forward | M | Navigate back then forward | Pages reload correctly | ☐ |
| TC-UI-012 | Right-to-Left | L | Test with Arabic language | Layout flips correctly | ☐ |
| TC-UI-013 | Modal Scroll Lock | M | Open modal, try scroll bg | Background locked, modal scrolls | ☐ |
| TC-UI-014 | Form Autofill | M | Browser autofill on forms | Autofill works, no style breaks | ☐ |
| TC-UI-015 | Disabled JavaScript | L | Turn off JS, load site | Graceful degradation | ☐ |
| TC-UI-016 | Slow 3G Network | M | Throttle to Slow 3G | Loading states visible | ☐ |
| TC-UI-017 | Tab Navigation | M | Use Tab key through form | Focus order logical | ☐ |
| TC-UI-018 | Screen Reader | L | Test with NVDA/VoiceOver | ARIA labels read correctly | ☐ |

---

## 8. Security (22 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-SEC-001 | SQLi Login | C | Enter `' OR '1'='1` as username | Login fails, no SQL error exposed | ☐ |
| TC-SEC-002 | SQLi URL Audit | C | Enter URL with SQL injection | URL rejected, no injection possible | ☐ |
| TC-SEC-003 | XSS Input | C | Enter `<script>alert('XSS')</script>` | Script sanitized, not executed | ☐ |
| TC-SEC-004 | XSS URL Param | H | Add script to URL parameter | Script sanitized, no execution | ☐ |
| TC-SEC-005 | CSRF Protection | C | Remove token, submit form | Submission rejected, CSRF error | ☐ |
| TC-SEC-006 | Password Hash | C | Check database for password | Passwords hashed, not plain text | ☐ |
| TC-SEC-007 | Session Cookies | H | Inspect session cookie | HttpOnly, Secure, SameSite flags set | ☐ |
| TC-SEC-008 | Unauthorized Admin | H | User tries admin URLs | 403 or redirect to login | ☐ |
| TC-SEC-009 | File Upload | H | Upload .php or path traversal | Upload rejected or sanitized | ☐ |
| TC-SEC-010 | Rate Limiting | M | Rapid form submissions | Rate limit applied after threshold | ☐ |
| TC-SEC-011 | JWT Token Tampering | H | Modify JWT payload | Signature invalid, rejected | ☐ |
| TC-SEC-012 | Clickjacking | H | Site in iframe | X-Frame-Options prevents | ☐ |
| TC-SEC-013 | MIME Sniffing | M | Upload file with wrong extension | X-Content-Type-Options set | ☐ |
| TC-SEC-014 | Referrer Policy | L | Check referrer header | Referrer-Policy header present | ☐ |
| TC-SEC-015 | HSTS Header | M | HTTPS response headers | Strict-Transport-Security present | ☐ |
| TC-SEC-016 | Information Disclosure | H | Trigger 500 error | No stack trace to user | ☐ |
| TC-SEC-017 | Brute Force Protection | H | 1000 login attempts | IP blocked or CAPTCHA shown | ☐ |
| TC-SEC-018 | Directory Traversal | H | Access /../../etc/passwd | 404 or blocked | ☐ |
| TC-SEC-019 | Cookie Theft | L | Try accessing HttpOnly cookie | Cannot read via JavaScript | ☐ |
| TC-SEC-020 | Open Redirect | H | Redirect param to evil.com | Validated or blocked | ☐ |
| TC-SEC-021 | Command Injection | C | Input with `;rm -rf /` | Sanitized, no execution | ☐ |
| TC-SEC-022 | XML External Entity | L | Upload malicious XML | XXE prevention active | ☐ |

---

## 9. Edge Cases (18 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-EDGE-001 | Very Long URL | M | Enter 2000+ character URL | Handled gracefully, no crash | ☐ |
| TC-EDGE-002 | Special Characters | M | Enter `!@#$%^&*()` in inputs | No crash, proper escaping | ☐ |
| TC-EDGE-003 | Unicode | M | Enter unicode URL/username | Accepted and displayed correctly | ☐ |
| TC-EDGE-004 | Concurrent Users | L | Multiple users perform audits | No data mixing, session isolation | ☐ |
| TC-EDGE-005 | Browser Back | M | Complete audit, click back | Consistent state, no duplicates | ☐ |
| TC-EDGE-006 | Network Interrupt | M | Start audit, disconnect network | Graceful timeout, error message | ☐ |
| TC-EDGE-007 | Empty Database | L | Fresh install, access features | Graceful handling, defaults used | ☐ |
| TC-EDGE-008 | Maximum Input Length | M | Enter 10,000 character input | Handled or truncated gracefully | ☐ |
| TC-EDGE-009 | Null Bytes | L | Input with \x00 characters | Stripped or rejected | ☐ |
| TC-EDGE-010 | Control Characters | L | Input with \n\t\r only | Validation error or stripped | ☐ |
| TC-EDGE-011 | Emoji in URL | M | URL with emoji characters | Punycode conversion or error | ☐ |
| TC-EDGE-012 | Timezone Handling | M | Test at midnight UTC | Times display correctly | ☐ |
| TC-EDGE-013 | Leap Year Date | L | Feb 29 on non-leap year | Validation error | ☐ |
| TC-EDGE-014 | Decimal Precision | L | Enter 0.0000001 amount | Rounded or error | ☐ |
| TC-EDGE-015 | Negative Numbers | M | Enter -1 for quantity | Validation rejects negative | ☐ |
| TC-EDGE-016 | Zero Division | L | Trigger calculation with 0 | Handled gracefully | ☐ |
| TC-EDGE-017 | Maximum File Descriptors | L | Open many connections | Error or pool exhausted | ☐ |
| TC-EDGE-018 | Memory Pressure | L | Analyze huge batch of URLs | No OOM crash | ☐ |

---

## 10. System (15 Cases)

| ID | Test Case | P | Steps Summary | Expected Result | Status |
|----|-----------|---|---------------|-----------------|--------|
| TC-SYS-001 | Health Check | H | Access /health/ | 200 OK with JSON status | ☐ |
| TC-SYS-002 | Readiness | H | Access /ready/ | 200 when DB connected | ☐ |
| TC-SYS-003 | Liveness | H | Access /live/ | 200 OK status | ☐ |
| TC-SYS-004 | Database | C | Perform DB operation | Connection successful, query runs | ☐ |
| TC-SYS-005 | Static Files | M | Access CSS/JS directly | Files served with correct MIME | ☐ |
| TC-SYS-006 | Media Files | M | Upload and access file | Upload success, file accessible | ☐ |
| TC-SYS-007 | Disk Full | L | Disk at 100% capacity | Graceful error, no crash | ☐ |
| TC-SYS-008 | Memory Exhaustion | L | Memory at 95% usage | No OOM crash, errors handled | ☐ |
| TC-SYS-009 | Database Connection Pool | M | Max connections reached | Queue or error gracefully | ☐ |
| TC-SYS-010 | Celery Worker Down | H | Submit async task, workers off | Task queued, no data loss | ☐ |
| TC-SYS-011 | Redis Cache Fail | M | Redis unavailable | Fallback to DB, no crash | ☐ |
| TC-SYS-012 | Email Server Down | M | Trigger email, SMTP fails | Logged, retry later | ☐ |
| TC-SYS-013 | Log Rotation | L | Logs exceed max size | Rotation works, no disk fill | ☐ |
| TC-SYS-014 | Backup Restore | H | Restore from backup | Data integrity maintained | ☐ |
| TC-SYS-015 | Rolling Deployment | M | Deploy new version | Zero-downtime deployment | ☐ |

---

## Summary

| Module | Cases | Critical | High | Medium | Low |
|--------|-------|----------|------|--------|-----|
| Authentication | 24 | 7 | 10 | 6 | 1 |
| SEO Audit | 30 | 4 | 13 | 11 | 2 |
| Subscription | 20 | 6 | 10 | 4 | 0 |
| Admin | 10 | 2 | 5 | 2 | 1 |
| Keyword AI | 20 | 4 | 10 | 5 | 1 |
| Comparative | 14 | 3 | 5 | 5 | 1 |
| UI/UX | 18 | 3 | 8 | 6 | 1 |
| Security | 22 | 11 | 7 | 3 | 1 |
| Edge Cases | 18 | 0 | 3 | 12 | 3 |
| System | 15 | 4 | 4 | 5 | 2 |
| **TOTAL** | **191** | **44** | **75** | **59** | **13** |
