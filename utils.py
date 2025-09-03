"""
Utility functions for the Lead Finder system.
"""

import re
import time
from urllib.parse import urlparse, urljoin, urlunparse
from typing import List, Optional, Set, Tuple
import config


def extract_domain(url: str) -> str:
    """Extract the root domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except Exception:
        return url.lower()


def is_junk_url(url: str) -> bool:
    """Check if a URL should be excluded as junk."""
    url_lower = url.lower()
    
    # Check host exclusions
    for host in config.EXCLUDES_HOST:
        if host in url_lower:
            return True
    
    # Check TLD exclusions
    for tld in config.EXCLUDES_TLD:
        if tld in url_lower:
            return True
    
    # Check file extensions
    for ext in config.EXCLUDES_EXT:
        if url_lower.endswith(ext):
            return True
    
    # Check path exclusions
    for path in config.EXCLUDES_PATH:
        if path in url_lower:
            return True
    
    return False


def canonicalize_url(url: str) -> str:
    """Convert URL to canonical form."""
    try:
        parsed = urlparse(url)
        
        # Ensure scheme
        if not parsed.scheme:
            parsed = parsed._replace(scheme='https')
        
        # Remove www. from netloc
        if parsed.netloc.startswith('www.'):
            parsed = parsed._replace(netloc=parsed.netloc[4:])
        
        # Remove trailing slash from path (except root)
        if parsed.path != '/' and parsed.path.endswith('/'):
            parsed = parsed._replace(path=parsed.path.rstrip('/'))
        
        # Remove query and fragment
        parsed = parsed._replace(query='', fragment='')
        
        return urlunparse(parsed)
    except Exception:
        return url


def get_root_url(url: str) -> str:
    """Get the root URL for a domain."""
    try:
        parsed = urlparse(url)
        root_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Remove www. if present
        if root_url.startswith('https://www.'):
            root_url = root_url.replace('https://www.', 'https://')
        elif root_url.startswith('http://www.'):
            root_url = root_url.replace('http://www.', 'http://')
            
        return root_url
    except Exception:
        return url


def is_platform_subdomain(url: str) -> bool:
    """Check if URL is a platform subdomain."""
    platform_patterns = [
        r'\.wixsite\.com$',
        r'\.squarespace\.com$',
        r'\.shopify\.com$',
        r'\.weebly\.com$',
        r'\.wordpress\.com$',
        r'\.blogspot\.com$',
        r'\.tumblr\.com$',
        r'\.medium\.com$'
    ]
    
    domain = extract_domain(url)
    for pattern in platform_patterns:
        if re.search(pattern, domain):
            return True
    
    return False


def extract_brand_name(title: str, domain: str) -> str:
    """Extract brand name from title or domain."""
    if not title:
        return domain
    
    # Remove common suffixes
    suffixes = [
        ' - Home', ' | Home', ' - Welcome', ' | Welcome',
        ' - Official Site', ' | Official Site', ' - Official Website',
        ' | Official Website', ' - Website', ' | Website'
    ]
    
    brand = title
    for suffix in suffixes:
        if brand.endswith(suffix):
            brand = brand[:-len(suffix)]
            break
    
    # If title is too generic, use domain
    generic_titles = [
        'Home', 'Welcome', 'Official Site', 'Official Website',
        'Website', 'Site', 'Homepage'
    ]
    
    if brand.strip() in generic_titles:
        return domain
    
    return brand.strip()


def is_owner_site(content: str, domain: str) -> bool:
    """Determine if this is an owner-operated site."""
    content_lower = content.lower()
    domain_lower = domain.lower()
    
    # Strong signals of ownership
    ownership_signals = [
        # Contact information
        f"tel:", f"mailto:", f"contact@", f"info@", f"hello@",
        # Business information
        "about us", "our story", "company", "business", "services",
        # Local business indicators
        "address", "location", "hours", "appointment", "booking",
        # Brand indicators
        "logo", "brand", "mission", "vision", "values"
    ]
    
    # Check for ownership signals
    signal_count = 0
    for signal in ownership_signals:
        if signal in content_lower:
            signal_count += 1
    
    # Reject if it's clearly a directory/listing site
    directory_indicators = [
        "directory", "listing", "find", "search", "compare",
        "reviews", "ratings", "book now", "order online"
    ]
    
    directory_count = 0
    for indicator in directory_indicators:
        if indicator in content_lower:
            directory_count += 1
    
    # Must have more ownership signals than directory signals
    return signal_count > directory_count and signal_count >= 2


def calculate_score(lead_data: dict) -> Tuple[int, str]:
    """Calculate the lead score and tier."""
    score = 0
    
    # Check if this is SEO opportunity mode
    if lead_data.get('seo_opportunity') is not None:
        return calculate_seo_opportunity_score(lead_data)
    
    # Standard scoring logic
    
    # Ownership & basics
    if lead_data.get('owner_valid'):
        score += 25
    
    if lead_data.get('contact', {}).get('phone') or lead_data.get('contact', {}).get('form'):
        score += 5
    
    # Hacked / compromised
    if lead_data.get('hacked_signals'):
        score += 30
        if len(lead_data['hacked_signals']) >= 2:
            score += 10
    
    # Outdated / tech debt
    wp_version = lead_data.get('tech', {}).get('wp_version')
    if wp_version:
        try:
            from packaging import version
            if version.parse(wp_version) < version.parse(config.WP_VERSION_BAD):
                score += 15
        except:
            # If version parsing fails, assume it's old
            score += 15
    
    if lead_data.get('tech', {}).get('readme_accessible'):
        score += 15
    
    if lead_data.get('errors'):
        score += 10
    
    # Performance
    psi = lead_data.get('psi', {})
    if psi and psi.get('perf') and psi['perf'] < 50:
        score += 10
    
    if psi and psi.get('lcp_ms') and psi['lcp_ms'] > 10000:
        score += 5
    
    if psi and psi.get('cls') and psi['cls'] > 0.25:
        score += 5
    
    # SEO
    if (lead_data.get('seo', {}).get('robots_noindex') or 
        lead_data.get('seo', {}).get('title_missing') or
        lead_data.get('seo', {}).get('meta_desc_missing')):
        score += 10
    
    # Penalty for already good performance
    if psi and psi.get('perf') and psi['perf'] >= 80:
        score -= 10
    
    # Cap score between 0 and 100
    score = max(0, min(100, score))
    
    # Determine tier
    if score >= config.TIER_A_MIN:
        tier = "A"
    elif score >= config.TIER_B_MIN:
        tier = "B"
    elif score >= config.SCORE_MIN:
        tier = "C"
    else:
        tier = "D"
    
    return score, tier


def calculate_seo_opportunity_score(lead_data: dict) -> Tuple[int, str]:
    """Calculate SEO opportunity score for near-win leads."""
    score = 0
    
    # Base score from rank position (lower rank = higher score)
    best_rank = lead_data.get('best_rank', 50)
    if best_rank <= 20:
        score += 30  # Very close to page 1
    elif best_rank <= 30:
        score += 20  # Close to page 1
    elif best_rank <= 40:
        score += 10  # Still in opportunity range
    
    # On-page SEO issues (high impact)
    if lead_data.get('seo', {}).get('title_missing'):
        score += 25
    if lead_data.get('seo', {}).get('meta_desc_missing'):
        score += 20
    if lead_data.get('seo', {}).get('robots_noindex'):
        score += 30
    if lead_data.get('seo', {}).get('multiple_h1'):
        score += 15
    if lead_data.get('seo', {}).get('thin_content'):
        score += 20
    
    # Technical issues (medium impact)
    if lead_data.get('tech', {}).get('wp_version'):
        try:
            from packaging import version
            if version.parse(lead_data['tech']['wp_version']) < version.parse(config.WP_VERSION_BAD):
                score += 15
        except:
            score += 15
    
    if lead_data.get('tech', {}).get('readme_accessible'):
        score += 20
    
    # Performance issues (medium impact)
    psi = lead_data.get('psi', {})
    if psi and psi.get('perf') and psi['perf'] < 50:
        score += 20
    elif psi and psi.get('perf') and psi['perf'] < 70:
        score += 10
    
    # Security issues (low impact for SEO)
    if lead_data.get('security', {}).get('https') == False:
        score += 10
    if lead_data.get('security', {}).get('mixed_content'):
        score += 5
    
    # Contact information (business validation)
    if lead_data.get('contact', {}).get('phone') or lead_data.get('contact', {}).get('form'):
        score += 10
    
    # Cap score between 0 and 100
    score = max(0, min(100, score))
    
    # Determine tier
    if score >= 80:
        tier = "A"
    elif score >= 60:
        tier = "B"
    elif score >= 40:
        tier = "C"
    else:
        tier = "D"
    
    return score, tier


def rate_limit_delay(requests_per_second: float = 1.0) -> None:
    """Simple rate limiting delay."""
    time.sleep(1.0 / requests_per_second)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations."""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    return filename 