"""Evidence-backed geographic and answer-engine optimization audits.

Scores represent coverage of verifiable checks. They do not predict rankings,
traffic, inclusion in AI answers, or citations.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


LOCAL_MODIFIERS = {
    "near me", "nearby", "in my area", "around me", "open now",
    "delivery", "local", "best near",
}
REGION_MAP: Dict[str, List[str]] = {
    "NA": ["usa", "us", "united states", "canada", "ca", "mexico", "mx"],
    "EU": [
        "uk", "united kingdom", "england", "scotland", "wales", "ireland",
        "germany", "france", "spain", "italy", "netherlands", "sweden",
        "norway", "denmark", "finland", "poland",
    ],
    "APAC": [
        "australia", "au", "japan", "jp", "singapore", "sg", "india", "in",
        "china", "cn", "hong kong", "korea", "kr", "thailand", "indonesia",
        "philippines", "vietnam", "malaysia", "pakistan", "pk",
    ],
    "LATAM": ["brazil", "br", "argentina", "ar", "chile", "cl", "colombia"],
    "MEA": ["uae", "saudi arabia", "south africa", "egypt", "israel", "turkey"],
}
REGION_LABELS = {
    "GLOBAL": "Global",
    "NA": "North America",
    "EU": "Europe",
    "APAC": "Asia Pacific",
    "LATAM": "Latin America",
    "MEA": "Middle East and Africa",
}
REGION_LANGUAGE_PREFIXES = {
    "NA": {"en", "es", "fr"},
    "EU": {"en", "de", "fr", "es", "it", "nl", "sv", "no", "da", "fi", "pl"},
    "APAC": {"en", "zh", "ja", "ko", "hi", "ur", "ms", "id", "th", "vi"},
    "LATAM": {"es", "pt"},
    "MEA": {"ar", "en", "he", "tr", "fr"},
}
COMMON_CITY_TOKENS = {
    "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia",
    "san antonio", "san diego", "dallas", "san francisco", "seattle", "boston",
    "austin", "denver", "miami", "atlanta", "london", "manchester",
    "birmingham", "berlin", "munich", "paris", "madrid", "barcelona",
    "amsterdam", "rome", "milan", "dublin", "sydney", "melbourne", "tokyo",
    "osaka", "singapore", "mumbai", "delhi", "bangalore", "shanghai",
    "beijing", "hong kong", "seoul", "karachi", "lahore", "islamabad",
    "rawalpindi", "faisalabad", "peshawar",
}
AEO_QUESTION_STARTERS = (
    "what", "how", "why", "when", "where", "who", "which",
    "can", "is", "are", "should", "do", "does",
)
AEO_FORMAT_HINTS = {
    "definition": ["what is", "definition of", "meaning of", "explained"],
    "list": ["best", "top", "list of", "examples of", "types of", "ways to", "tips for", "tools for"],
    "tutorial": ["how to", "guide to", "tutorial", "step by step", "getting started"],
    "comparison": ["vs", "versus", "compared to", "difference between", "alternative", "comparison"],
    "faq": ["should i", "can i", "do i need", "is it worth", "when to", "why use", "how does"],
}
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "what",
    "when", "where", "which", "who", "why", "with",
}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(
    check_id: str,
    label: str,
    status: str,
    detail: str,
    source: str,
    weight: int,
) -> Dict:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "detail": detail,
        "source": source,
        "weight": weight,
    }


def _coverage_score(checks: List[Dict]) -> int:
    applicable = [item for item in checks if item["status"] != "not_applicable"]
    denominator = sum(item["weight"] for item in applicable)
    passed = sum(item["weight"] for item in applicable if item["status"] == "pass")
    return round(100 * passed / denominator) if denominator else 0


def _legacy_evidence(checks: List[Dict]) -> List[Dict]:
    return [
        {
            "signal": item["id"],
            "detail": item["detail"],
            "source": item["source"],
            "points": item["weight"] if item["status"] == "pass" else 0,
            "observed": item["source"] in {"page", "serpapi", "keyword_provider"},
            "status": item["status"],
        }
        for item in checks
        if item["status"] in {"pass", "fail"}
    ]


def _confidence(checks: List[Dict], live_checked: bool = False) -> str:
    known = sum(item["status"] in {"pass", "fail"} for item in checks)
    sources = {item["source"] for item in checks if item["status"] in {"pass", "fail"}}
    if live_checked and known >= 5 and "page" in sources:
        return "high"
    if known >= 3:
        return "medium"
    return "low"


def _tokens(value: str) -> set:
    return {
        token for token in re.findall(r"[a-z0-9]+", (value or "").lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _overlap(left: str, right: str) -> float:
    target = _tokens(left)
    if not target:
        return 0.0
    return len(target.intersection(_tokens(right))) / len(target)


def _detect_locations(keyword_lower: str) -> Tuple[List[str], List[str]]:
    cities = sorted(city for city in COMMON_CITY_TOKENS if city in keyword_lower)
    regions = []
    for region, values in REGION_MAP.items():
        if any(re.search(rf"\b{re.escape(value)}\b", keyword_lower) for value in values):
            regions.append(region)
    return cities, regions


def _has_local_modifier(keyword_lower: str) -> bool:
    return any(value in keyword_lower for value in LOCAL_MODIFIERS)


def _provider_names(regional_volume_data: Dict, serp_data: Dict) -> List[str]:
    names = set()
    if regional_volume_data:
        names.add("regional_keyword_provider")
    if (serp_data or {}).get("data_source"):
        names.add(str(serp_data["data_source"]))
    return sorted(names)


@dataclass
class GeoData:
    primary_scope: str = "national"
    detected_locations: List[str] = field(default_factory=list)
    detected_regions: List[str] = field(default_factory=list)
    has_local_modifier: bool = False
    geo_score: int = 0
    search_volume_by_region: Dict[str, Optional[int]] = field(default_factory=dict)
    target_region: str = "GLOBAL"
    target_region_label: str = "Global"
    confidence: str = "low"
    data_status: str = "insufficient_evidence"
    applicability: str = "not_applicable"
    score_type: str = "evidence_coverage"
    checks: List[Dict] = field(default_factory=list)
    evidence: List[Dict] = field(default_factory=list)
    provider_sources: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    measured_at: str = field(default_factory=_timestamp)

    def as_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AEOSignals:
    score: int = 0
    ai_friendly: bool = False
    query_suitable: bool = False
    suggested_formats: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)
    answer_extraction_likelihood: str = "insufficient_evidence"
    readiness_label: str = "Insufficient page evidence"
    confidence: str = "low"
    score_type: str = "evidence_coverage"
    data_status: str = "insufficient_evidence"
    checks: List[Dict] = field(default_factory=list)
    evidence: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    observed_visibility: Dict = field(default_factory=dict)
    provider_sources: List[str] = field(default_factory=list)
    measured_at: str = field(default_factory=_timestamp)

    def as_dict(self) -> Dict:
        return asdict(self)


def analyze_geo(
    keyword: str,
    regional_volume_data: Optional[Dict[str, int]] = None,
    target_region: str = "GLOBAL",
    page_signals: Optional[Dict] = None,
    serp_data: Optional[Dict] = None,
) -> GeoData:
    if not keyword:
        return GeoData()

    regional_volume_data = regional_volume_data or {}
    page_signals = page_signals or {}
    serp_data = serp_data or {}
    target_region = (target_region or "GLOBAL").upper()
    keyword_lower = keyword.lower().strip()
    cities, regions = _detect_locations(keyword_lower)
    has_local = _has_local_modifier(keyword_lower)
    geo_intent = bool(has_local or cities or regions)
    applicable = geo_intent or target_region != "GLOBAL"

    if has_local or cities:
        scope = "local"
    elif len(regions) >= 2:
        scope = "international"
    elif regions or target_region != "GLOBAL":
        scope = "regional"
    else:
        scope = "national"

    if not applicable:
        return GeoData(
            primary_scope=scope,
            detected_locations=cities,
            detected_regions=regions,
            target_region=target_region,
            target_region_label=REGION_LABELS.get(target_region, target_region),
            applicability="not_applicable",
            recommendations=["No geographic intent was detected; evaluate this keyword as a non-local query."],
        )

    checks = []
    checks.append(_check(
        "geographic_query_intent",
        "Explicit geographic query intent",
        "pass" if geo_intent else "unknown",
        ", ".join(cities + regions) or ("Local modifier detected." if has_local else "Target market supplied by user."),
        "keyword" if geo_intent else "user_input",
        20,
    ))

    if target_region == "GLOBAL":
        target_status = "not_applicable"
        target_detail = "No specific target market selected."
    elif target_region in regions:
        target_status = "pass"
        target_detail = "Keyword location matches the selected target market."
    elif regions:
        target_status = "fail"
        target_detail = "Keyword location conflicts with the selected target market."
    else:
        target_status = "unknown"
        target_detail = "Selected market is not explicit in the query."
    checks.append(_check("target_market_alignment", "Target-market alignment", target_status, target_detail, "user_input", 15))

    needs_local_page = scope == "local"
    has_schema = bool(page_signals.get("has_local_schema"))
    has_address = bool(page_signals.get("addresses") or page_signals.get("service_areas"))
    page_available = bool(page_signals)
    checks.append(_check(
        "local_business_schema",
        "Local business structured data",
        ("pass" if has_schema else "fail") if needs_local_page and page_available else ("unknown" if needs_local_page else "not_applicable"),
        "LocalBusiness/Place schema detected." if has_schema else "No verified local-business schema detected.",
        "page",
        15,
    ))
    checks.append(_check(
        "address_or_service_area",
        "Visible address or service area",
        ("pass" if has_address else "fail") if needs_local_page and page_available else ("unknown" if needs_local_page else "not_applicable"),
        "Address or service-area evidence detected." if has_address else "No address or service-area evidence detected.",
        "page",
        15,
    ))

    language = (page_signals.get("language") or page_signals.get("og_locale") or "").lower()
    language_prefix = re.split(r"[-_]", language)[0] if language else ""
    locale_status = "not_applicable"
    if target_region != "GLOBAL":
        if not page_available:
            locale_status = "unknown"
        elif language_prefix and language_prefix in REGION_LANGUAGE_PREFIXES.get(target_region, set()):
            locale_status = "pass"
        else:
            locale_status = "fail"
    checks.append(_check(
        "page_locale",
        "Page language/locale supports target market",
        locale_status,
        language or "No language or locale metadata detected.",
        "page",
        10,
    ))

    needs_alternates = scope in {"regional", "international"} and target_region != "GLOBAL"
    hreflang = page_signals.get("hreflang") or []
    checks.append(_check(
        "hreflang",
        "Regional alternate annotations",
        ("pass" if hreflang else "fail") if needs_alternates and page_available else ("unknown" if needs_alternates else "not_applicable"),
        f"{len(hreflang)} hreflang annotation(s) detected." if hreflang else "No hreflang annotations detected.",
        "page",
        10,
    ))

    valid_volumes = {}
    for region, volume in regional_volume_data.items():
        try:
            valid_volumes[str(region)] = int(volume)
        except (TypeError, ValueError):
            continue
    checks.append(_check(
        "regional_demand",
        "Measured regional demand",
        "pass" if valid_volumes else "unknown",
        f"Measured demand available for {len(valid_volumes)} market(s)." if valid_volumes else "No regional keyword-provider data available.",
        "keyword_provider",
        10,
    ))

    live_checked = bool(serp_data.get("data_source"))
    local_pack = "local_pack" in (serp_data.get("serp_features") or [])
    checks.append(_check(
        "local_serp_pack",
        "Observed local SERP composition",
        ("pass" if local_pack else "fail") if live_checked and needs_local_page else ("unknown" if needs_local_page else "not_applicable"),
        "Local pack observed." if local_pack else ("Live SERP checked without a local pack." if live_checked else "Live SERP not checked."),
        "serpapi",
        15,
    ))

    recommendations = []
    for item in checks:
        if item["status"] not in {"fail", "unknown"}:
            continue
        if item["id"] == "local_business_schema":
            recommendations.append("Add valid LocalBusiness and PostalAddress JSON-LD that matches visible page content.")
        elif item["id"] == "address_or_service_area":
            recommendations.append("Show the real business address or service area consistently on the page.")
        elif item["id"] == "page_locale":
            recommendations.append("Declare the page language and locale for the selected market.")
        elif item["id"] == "hreflang":
            recommendations.append("Add reciprocal hreflang annotations when equivalent regional pages exist.")
        elif item["id"] == "regional_demand":
            recommendations.append("Regional demand is unavailable; do not infer exact local search volume.")

    status = "observed" if live_checked or valid_volumes else ("page_observed" if page_available else "insufficient_evidence")
    return GeoData(
        primary_scope=scope,
        detected_locations=cities,
        detected_regions=regions,
        has_local_modifier=has_local,
        geo_score=_coverage_score(checks),
        search_volume_by_region=valid_volumes,
        target_region=target_region,
        target_region_label=REGION_LABELS.get(target_region, target_region),
        confidence=_confidence(checks, live_checked),
        data_status=status,
        applicability="applicable",
        checks=checks,
        evidence=_legacy_evidence(checks),
        provider_sources=_provider_names(valid_volumes, serp_data),
        recommendations=list(dict.fromkeys(recommendations))[:5],
    )


def _aeo_format_hints(keyword_lower: str) -> Tuple[List[str], List[str]]:
    suggested = []
    matched = []
    tokens = keyword_lower.split()
    for format_name, patterns in AEO_FORMAT_HINTS.items():
        for pattern in patterns:
            hit = pattern in keyword_lower if " " in pattern else pattern in tokens
            if hit:
                suggested.append(format_name)
                matched.append(pattern)
                break
    return list(dict.fromkeys(suggested)), matched


def _source_domains(values: List) -> List[str]:
    domains = []
    for item in values or []:
        if isinstance(item, dict):
            domain = item.get("domain")
            link = item.get("link") or item.get("url")
            if not domain and link:
                domain = urlparse(link).netloc
        else:
            domain = urlparse(str(item)).netloc or str(item)
        if domain:
            domains.append(domain.lower().removeprefix("www."))
    return sorted(set(domains))


def analyze_aeo(
    keyword: str,
    page_signals: Optional[Dict] = None,
    page_text: str = "",
    serp_data: Optional[Dict] = None,
    page_url: str = "",
) -> AEOSignals:
    if not keyword:
        return AEOSignals()

    page_signals = page_signals or {}
    serp_data = serp_data or {}
    keyword_lower = keyword.lower().strip()
    formats, format_hits = _aeo_format_hints(keyword_lower)
    query_suitable = bool(
        keyword_lower.split()
        and (
            keyword_lower.split()[0] in AEO_QUESTION_STARTERS
            or formats
            or len(_tokens(keyword)) >= 3
        )
    )
    page_available = bool(page_text.strip() or page_signals)
    checks = [
        _check(
            "answerable_query",
            "Query has a clear answer intent",
            "pass" if query_suitable else "fail",
            ", ".join(formats) if formats else "Query intent inferred from its wording.",
            "keyword",
            15,
        )
    ]

    coverage = _overlap(keyword, page_text)
    checks.append(_check(
        "query_topic_coverage",
        "Page covers the query topic",
        ("pass" if coverage >= 0.6 else "fail") if page_text.strip() else "unknown",
        f"{round(coverage * 100)}% of meaningful query terms found on the page." if page_text.strip() else "Page text unavailable.",
        "page",
        20,
    ))

    aligned_pair = None
    for pair in page_signals.get("question_answer_pairs") or []:
        question_overlap = _overlap(keyword, pair.get("question", ""))
        answer_overlap = _overlap(keyword, pair.get("answer", ""))
        word_count = int(pair.get("answer_word_count") or len(pair.get("answer", "").split()))
        if max(question_overlap, answer_overlap) >= 0.5 and 20 <= word_count <= 120:
            aligned_pair = pair
            break
    if not aligned_pair:
        for answer in page_signals.get("concise_answers") or []:
            if _overlap(keyword, answer) >= 0.6:
                aligned_pair = {"answer": answer, "answer_word_count": len(answer.split())}
                break
    checks.append(_check(
        "direct_answer",
        "Relevant concise answer passage",
        ("pass" if aligned_pair else "fail") if page_available else "unknown",
        (
            f"Relevant answer passage detected ({aligned_pair.get('answer_word_count')} words)."
            if aligned_pair else "No query-aligned 20-120 word answer passage detected."
        ),
        "page",
        25,
    ))

    list_count = int(page_signals.get("ordered_lists") or 0) + int(page_signals.get("unordered_lists") or 0)
    structured = bool(list_count or page_signals.get("tables"))
    structure_needed = bool(set(formats).intersection({"list", "tutorial", "comparison"}))
    checks.append(_check(
        "answer_structure",
        "Answer format matches query intent",
        ("pass" if structured else "fail") if structure_needed and page_available else ("not_applicable" if not structure_needed else "unknown"),
        f"{list_count} list(s), {page_signals.get('tables', 0)} table(s)." if structured else "No supporting list or table detected.",
        "page",
        10,
    ))

    has_identity = bool(page_signals.get("author") or page_signals.get("publisher"))
    checks.append(_check(
        "source_identity",
        "Author or publisher identity",
        ("pass" if has_identity else "fail") if page_available else "unknown",
        "Author or publisher metadata detected." if has_identity else "No author or publisher identity detected.",
        "page",
        10,
    ))

    citations = page_signals.get("external_citations") or []
    checks.append(_check(
        "primary_sources",
        "External supporting sources",
        ("pass" if citations else "fail") if page_available else "unknown",
        f"{len(citations)} external source link(s) detected." if citations else "No external supporting sources detected.",
        "page",
        10,
    ))

    has_date = bool(page_signals.get("modified_at") or page_signals.get("published_at"))
    checks.append(_check(
        "date_metadata",
        "Published or modified date",
        ("pass" if has_date else "fail") if page_available else "unknown",
        "Date metadata detected." if has_date else "No published or modified date detected.",
        "page",
        5,
    ))

    schema_types = set(page_signals.get("schema_types") or [])
    relevant_schema = schema_types.intersection({"FAQPage", "HowTo", "Article", "NewsArticle", "WebPage"})
    schema_valid = bool(relevant_schema and int(page_signals.get("invalid_json_ld_blocks") or 0) == 0)
    checks.append(_check(
        "supported_structured_data",
        "Valid, content-supported structured data",
        ("pass" if schema_valid else "fail") if page_available else "unknown",
        ", ".join(sorted(relevant_schema)) if relevant_schema else "No relevant valid JSON-LD type detected.",
        "page",
        5,
    ))

    ai_domains = _source_domains(serp_data.get("ai_overview_sources") or [])
    answer_domains = _source_domains(serp_data.get("answer_sources") or [])
    page_domain = urlparse(page_url).netloc.lower().removeprefix("www.")
    organic_positions = [
        item.get("position")
        for item in serp_data.get("organic_results") or []
        if item.get("domain", "").lower().removeprefix("www.") == page_domain
    ]
    ai_cited = bool(page_domain and page_domain in ai_domains)
    answer_cited = bool(page_domain and page_domain in answer_domains)
    live_checked = bool(serp_data.get("data_source"))
    observed_visibility = {
        "checked": live_checked,
        "has_ai_overview": bool(serp_data.get("has_ai_overview")),
        "has_featured_snippet": bool(serp_data.get("has_featured_snippet")),
        "has_people_also_ask": bool(serp_data.get("has_people_also_ask")),
        "target_domain_cited": ai_cited,
        "target_domain_in_answer_box": answer_cited,
        "target_domain_organic_position": min(organic_positions) if organic_positions else None,
        "source_domains": ai_domains,
        "answer_source_domains": answer_domains,
    }

    score = _coverage_score(checks)
    direct_answer_pass = any(item["id"] == "direct_answer" and item["status"] == "pass" for item in checks)
    topic_pass = any(item["id"] == "query_topic_coverage" and item["status"] == "pass" for item in checks)
    ai_friendly = bool(score >= 60 and direct_answer_pass and topic_pass)

    if not page_available:
        readiness = "Insufficient page evidence"
        likelihood = "insufficient_evidence"
    elif score >= 75:
        readiness = "Strong evidence coverage"
        likelihood = "high"
    elif score >= 50:
        readiness = "Partial evidence coverage"
        likelihood = "medium"
    else:
        readiness = "Weak evidence coverage"
        likelihood = "low"

    recommendations = []
    for item in checks:
        if item["status"] not in {"fail", "unknown"}:
            continue
        actions = {
            "query_topic_coverage": "Create or strengthen a page section that directly covers this query.",
            "direct_answer": "Add a concise, query-specific answer immediately below a matching heading.",
            "answer_structure": "Use a visible list, comparison table, or ordered steps when the query calls for it.",
            "source_identity": "Expose a real author or publisher with relevant expertise.",
            "primary_sources": "Cite authoritative primary sources for factual claims.",
            "date_metadata": "Expose valid published or modified date metadata.",
            "supported_structured_data": "Add valid JSON-LD only for structured content that is visible on the page.",
        }
        if item["id"] in actions:
            recommendations.append(actions[item["id"]])

    return AEOSignals(
        score=score,
        ai_friendly=ai_friendly,
        query_suitable=query_suitable,
        suggested_formats=formats,
        matched_patterns=format_hits,
        answer_extraction_likelihood=likelihood,
        readiness_label=readiness,
        confidence=_confidence(checks, live_checked),
        score_type="evidence_coverage_with_live_serp" if live_checked else "evidence_coverage",
        data_status="observed" if live_checked else ("page_observed" if page_available else "insufficient_evidence"),
        checks=checks,
        evidence=_legacy_evidence(checks),
        recommendations=list(dict.fromkeys(recommendations))[:5],
        observed_visibility=observed_visibility,
        provider_sources=_provider_names({}, serp_data),
    )


def analyze_geo_aeo(
    keyword: str,
    page_topic: str = "",
    regional_volume_data: Optional[Dict[str, int]] = None,
    page_signals: Optional[Dict] = None,
    page_text: str = "",
    target_region: str = "GLOBAL",
    serp_data: Optional[Dict] = None,
    page_url: str = "",
) -> Dict:
    geo = analyze_geo(
        keyword,
        regional_volume_data=regional_volume_data,
        target_region=target_region,
        page_signals=page_signals,
        serp_data=serp_data,
    )
    aeo = analyze_aeo(
        keyword,
        page_signals=page_signals,
        page_text=page_text,
        serp_data=serp_data,
        page_url=page_url,
    )
    geo_dict = geo.as_dict()
    geo_dict["regions"] = geo_dict["detected_regions"]
    return {"geo_data": geo_dict, "aeo_signals": aeo.as_dict()}


def analyze_keywords_batch(
    keywords: List[str],
    regional_volume_data: Optional[Dict[str, Dict[str, int]]] = None,
    page_signals: Optional[Dict] = None,
    page_text: str = "",
    target_region: str = "GLOBAL",
    serp_data_by_keyword: Optional[Dict[str, Dict]] = None,
    page_url: str = "",
) -> List[Dict]:
    regional_volume_data = regional_volume_data or {}
    serp_data_by_keyword = serp_data_by_keyword or {}
    return [
        {
            "keyword": keyword,
            **analyze_geo_aeo(
                keyword,
                regional_volume_data=regional_volume_data.get(keyword, {}),
                page_signals=page_signals,
                page_text=page_text,
                target_region=target_region,
                serp_data=serp_data_by_keyword.get(keyword, {}),
                page_url=page_url,
            ),
        }
        for keyword in keywords or []
        if keyword
    ]