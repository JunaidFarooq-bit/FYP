# Traffic Data API Configuration

To get **actual traffic numbers** (e.g., "12,500 monthly searches") instead of estimates, you need to configure keyword research API keys.

## Supported Data Providers

### 1. SEMrush API (Recommended)
**Best for:** Comprehensive SEO data, volume, difficulty, CPC

**Setup:**
1. Sign up at [SEMrush API](https://www.semrush.com/api/)
2. Get your API key from the dashboard
3. Add to your `.env` file:
```bash
SEMRUSH_API_KEY=your_api_key_here
```

**Pricing:** Starts at ~$200/month for API access

---

### 2. DataForSEO (Pay-as-you-go)
**Best for:** Startups, low volume, flexible pricing

**Setup:**
1. Register at [DataForSEO](https://dataforseo.com/)
2. Get Login and Password from dashboard
3. Add to your `.env` file:
```bash
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password
```

**Pricing:** ~$0.001 per keyword, $50 minimum deposit

---

### 3. Serpstat API (Affordable)
**Best for:** Budget-conscious, good volume data

**Setup:**
1. Sign up at [Serpstat](https://serpstat.com/)
2. Generate API token in settings
3. Add to your `.env` file:
```bash
SERPSTAT_API_KEY=your_api_key
```

**Pricing:** API included in plans starting at ~$69/month

---

### 4. Google Trends (Free - Already Configured)
**Best for:** Trend analysis, relative interest over time

**Note:** Already integrated via `pytrends`. No API key needed but provides **relative** scores (0-100), not exact volumes.

---

## Configuration Priority

The system tries data providers in this order:
1. **SEMrush** - Most comprehensive data
2. **DataForSEO** - Pay-as-you-go fallback
3. **Serpstat** - Budget option
4. **Google Trends** - Trend data only
5. **Estimation** - Intelligent heuristics (always available)

## Environment Variables

Add these to your `.env` file:

```bash
# SEMrush (highest priority)
SEMRUSH_API_KEY=your_semrush_api_key

# DataForSEO (pay-as-you-go)
DATAFORSEO_LOGIN=your_dataforseo_login
DATAFORSEO_PASSWORD=your_dataforseo_password

# Serpstat (budget option)
SERPSTAT_API_KEY=your_serpstat_key
```

## Without API Keys (Estimation Mode)

If no APIs are configured, the system uses **intelligent estimation** based on:
- Keyword length (short = higher volume)
- Commercial terms (buy, price = higher CPC)
- Question patterns (how, what = informational intent)
- Trending patterns (AI, automation = rising)

**Accuracy:** ~70% compared to real data

## Testing Your Configuration

Check which providers are active:
```python
from keyword_ai.services.traffic_data_providers import check_provider_status

status = check_provider_status()
print(status)
# {
#   'semrush': True,
#   'dataforseo': False,
#   'serpstat': False,
#   'any_enabled': True
# }
```

Test a single keyword:
```python
from keyword_ai.services.traffic_data_providers import get_keyword_volume

volume = get_keyword_volume("SEO automation")
print(volume)  # 12500 (actual number from API)
```

Test multiple keywords:
```python
from keyword_ai.services.traffic_data_providers import get_bulk_volumes

volumes = get_bulk_volumes(["SEO automation", "AI tools", "keyword research"])
print(volumes)
# {'SEO automation': 12500, 'AI tools': 45000, 'keyword research': 33100}
```

## Display in Templates

When real data is available, the template shows:
- **Exact monthly volume** (e.g., "12,500/mo")
- **Traffic potential** (e.g., "~3,750/mo" if ranked #1)
- **Difficulty score** (0-100 exact number)
- **CPC value** (e.g., "$2.50")
- **Data provider** badge (SEMrush, DataForSEO, etc.)

When no API is configured:
- Shows estimated ranges ("10K-100K")
- Category labels ("High", "Medium", "Low")
- "Estimated" badge

## Cost Optimization Tips

1. **Use DataForSEO for testing** - Pay only for what you use
2. **Cache aggressively** - Results cached for 60 minutes by default
3. **Bulk requests** - SEMrush supports 100 keywords per API call
4. **Prioritize focus keywords** - Only fetch real data for top 20 keywords
5. **Fallback gracefully** - System works without APIs

## Troubleshooting

### "All providers showing False"
- Check `.env` file is loaded: `python -c "from django.conf import settings; print(settings.SEMRUSH_API_KEY)"`
- Restart Django server after adding env vars
- Verify key format (no extra spaces)

### "API errors in logs"
- Check API credits/quota
- Verify API key is active
- Check rate limits (add delays between batches)

### "Still seeing estimates"
- API may not have data for that keyword
- Long-tail keywords often lack volume data
- System falls back to estimation automatically

## Next Steps

1. Choose a provider based on your budget
2. Add API keys to `.env`
3. Restart your Django server
4. Run a keyword analysis
5. Check results for actual numbers!
