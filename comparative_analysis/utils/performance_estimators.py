def estimate_page_speed(load_time):
    """Estimate page speed category based on load time"""
    
    if load_time < 1.0:
        return 'Fast'
    elif load_time < 2.5:
        return 'Average'
    elif load_time < 4.0:
        return 'Slow'
    else:
        return 'Very Slow'


def estimate_core_web_vitals(extracted_data):
    """Estimate Core Web Vitals (simplified)"""
    
    load_time = extracted_data.get('load_time', 0)
    
    # LCP (Largest Contentful Paint) - rough estimate
    lcp_estimate = load_time * 1.5
    lcp_rating = 'good' if lcp_estimate < 2.5 else ('needs improvement' if lcp_estimate < 4.0 else 'poor')
    
    # FID (First Input Delay) - assume good for static pages
    fid_estimate = 50  # milliseconds
    fid_rating = 'good'
    
    # CLS (Cumulative Layout Shift) - would need real measurement
    cls_estimate = 0.1
    cls_rating = 'good'
    
    return {
        'lcp': {
            'value': round(lcp_estimate, 2),
            'rating': lcp_rating,
            'unit': 'seconds'
        },
        'fid': {
            'value': fid_estimate,
            'rating': fid_rating,
            'unit': 'milliseconds'
        },
        'cls': {
            'value': cls_estimate,
            'rating': cls_rating,
            'unit': 'score'
        },
        'note': 'Estimated values - use real CrUX data for accuracy'
    }


def estimate_time_to_interactive(load_time, script_count=0):
    """Estimate Time to Interactive"""
    
    # Simplified estimation
    tti = load_time + (script_count * 0.1)
    
    return round(tti, 2)