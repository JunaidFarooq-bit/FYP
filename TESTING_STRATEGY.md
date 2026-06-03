# WebLift Manual Testing Strategy

## Test Categories

| Category | Priority | Test Cases |
|----------|----------|------------|
| Authentication | Critical | Registration, login, logout, password reset |
| SEO Audit | Critical | URL audit, reports, charts, PDF export |
| Subscriptions | Critical | Pricing, payment, upgrade, downgrade |
| Keyword AI | High | Suggestions, feedback, export |
| Comparative | High | Competitor analysis, gap reports |
| Admin | Medium | User management, payment verification |
| UI/UX | Medium | Responsive design, navigation |
| Security | High | SQL injection, XSS, auth bypass |

## Testing Levels

| Level | Focus | When |
|-------|-------|------|
| Unit | Individual functions/components | Developer checks |
| Integration | Module interactions | Feature completion |
| System | End-to-end workflows | Release candidate |
| UAT | Business requirements validation | Pre-release |
| Smoke | Critical path validation | After deployment |

---

## Test Environments

- Local development server
- Staging environment
- Production (smoke tests only)

---

## Browsers to Test

- Chrome
- Firefox
- Safari
- Edge

---

## Devices

- Desktop (1920x1080)
- Tablet (768x1024)
- Mobile (375x667)

---

## Test Documentation

See `tests/manual/MANUAL_TEST_CASES.md` for detailed test cases.

---

## Bug Reporting

1. Steps to reproduce
2. Expected result
3. Actual result
4. Screenshots
5. Browser/device info
