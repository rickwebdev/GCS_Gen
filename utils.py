"""
Utility functions for the Lead Finder system.
"""

import re
import time
from urllib.parse import urlparse, urljoin, urlunparse
from typing import List, Optional, Set, Tuple
import config
import requests
from bs4 import BeautifulSoup
import warnings

# Suppress BeautifulSoup warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# Regex patterns for outdated site detection
RE_JQ_OLD = re.compile(r"jquery-1\.\d+(\.\d+)?\.min\.js", re.I)
RE_BOOTSTRAP3 = re.compile(r"bootstrap/3\.\d+|bootstrap\.min\.css", re.I)
RE_COPYRIGHT = re.compile(r"(?:©|&copy;)\s*(\d{4})")
RE_NYC_TERMS = re.compile(r"\b(?:NYC|New York|Manhattan|SoHo|Tribeca|LES|UES|West Village|Brooklyn|Williamsburg)\b", re.I)


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


def calculate_lead_score(lead_data: dict) -> Tuple[int, str]:
    """
    Calculate lead score based on outdated site indicators and technical debt.
    
    Args:
        lead_data: Lead data dictionary with enhanced outdated site indicators
        
    Returns:
        Tuple of (score, tier)
    """
    score = 0
    
    # Performance scoring (desktop-first)
    if lead_data.get('psi_perf_desktop') and lead_data['psi_perf_desktop'] <= 60:
        score += 25
    if lead_data.get('ttfb_ms') and lead_data['ttfb_ms'] >= 1200:
        score += 15
    if lead_data.get('lcp_ms') and lead_data['lcp_ms'] >= 4000:
        score += 15
    
    # Security/modern web indicators
    if lead_data.get('mixed_content') or lead_data.get('http_only'):
        score += 15
    if lead_data.get('no_hsts'):
        score += 5
    
    # Builder/Stack debt (highest ROI)
    if lead_data.get('builder') == 'Divi':
        score += 20
    elif lead_data.get('builder') in ['Elementor', 'WPBakery']:
        score += 12
    if lead_data.get('old_jquery'):
        score += 10
    if lead_data.get('bootstrap_v3'):
        score += 6
    
    # Basic SEO/Accessibility
    if lead_data.get('missing_title'):
        score += 8
    if lead_data.get('missing_meta_desc'):
        score += 6
    if lead_data.get('missing_schema'):
        score += 5
    if lead_data.get('accessibility_poor'):
        score += 8
    
    # Content/UX red flags
    if lead_data.get('copyright_outdated'):
        score += 6
    if lead_data.get('broken_links_count', 0) >= 2:
        score += 10
    
    # NYC relevance bonus
    score += lead_data.get('nyc_bonus', 0)
    
    # Cap score between 0 and 100
    score = max(0, min(100, score))
    
    # Determine tier based on new scoring
    if score >= 70:
        tier = "A"  # Human review ASAP
    elif score >= 50:
        tier = "B"  # Queue for review
    else:
        tier = "C"  # Low priority
    
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


def analyze_html_for_outdated_sites(html_content: str, url: str, soup: BeautifulSoup = None) -> dict:
    """
    Analyze HTML content for outdated site indicators.
    
    Args:
        html_content: Raw HTML content
        url: URL being analyzed
        soup: Pre-parsed BeautifulSoup object (optional)
        
    Returns:
        Dictionary with outdated site indicators
    """
    if soup is None:
        soup = BeautifulSoup(html_content, 'html.parser')
    
    analysis = {
        'builder': None,
        'old_jquery': False,
        'bootstrap_v3': False,
        'http_only': not url.startswith('https://'),
        'mixed_content': False,
        'no_hsts': True,  # Assume missing unless found
        'missing_title': False,
        'missing_meta_desc': False,
        'missing_og': False,
        'missing_schema': False,
        'accessibility_poor': False,
        'copyright_outdated': False,
        'broken_links_count': 0,
        'nyc_bonus': 0
    }
    
    # Normalize HTML content safely
    html_lower = html_content.lower()
    
    # 1. Builder/Stack fingerprints
    if any(term in html_lower for term in ['wp-content/themes/divi', 'et_divi', 'divi_builder', 'et-core']):
        analysis['builder'] = 'Divi'
    elif any(term in html_lower for term in ['elementor-', 'elementor.min.js', 'elementor-frontend']):
        analysis['builder'] = 'Elementor'
    elif any(term in html_lower for term in ['js_composer', 'wpb_']):
        analysis['builder'] = 'WPBakery'
    elif any(term in html_lower for term in ['fusion-', 'avada-']):
        analysis['builder'] = 'Avada'
    elif any(term in html_lower for term in ['flatsome', 'ux-']):
        analysis['builder'] = 'Flatsome'
    
    # 2. Old jQuery detection
    if RE_JQ_OLD.search(html_content):
        analysis['old_jquery'] = True
    
    # 3. Bootstrap v3 detection
    if RE_BOOTSTRAP3.search(html_content):
        analysis['bootstrap_v3'] = True
    
    # 4. Mixed content check
    if url.startswith('https://') and 'http://' in html_content:
        analysis['mixed_content'] = True
    
    # 5. HSTS check (would need response headers, but we'll check for security headers in HTML)
    if 'strict-transport-security' in html_lower or 'hsts' in html_lower:
        analysis['no_hsts'] = False
    
    # 6. SEO basics
    title_tag = soup.find('title')
    if not title_tag or not title_tag.get_text().strip():
        analysis['missing_title'] = True
    
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if not meta_desc or not meta_desc.get('content', '').strip():
        analysis['missing_meta_desc'] = True
    
    og_tags = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
    if not og_tags:
        analysis['missing_og'] = True
    
    schema_tags = soup.find_all('script', attrs={'type': 'application/ld+json'})
    if not schema_tags:
        analysis['missing_schema'] = True
    
    # 7. Accessibility check (alt text ratio)
    imgs = soup.find_all('img')
    if imgs:
        missing_alt = sum(1 for img in imgs if not img.get('alt') or img.get('alt').strip() == '')
        alt_ratio = (missing_alt / len(imgs)) * 100
        analysis['accessibility_poor'] = alt_ratio > 40
    
    # 8. Copyright year check
    copyright_match = RE_COPYRIGHT.search(html_content)
    if copyright_match:
        try:
            year = int(copyright_match.group(1))
            analysis['copyright_outdated'] = year < 2022
        except (ValueError, IndexError):
            pass
    
    # 9. NYC relevance bonus
    if RE_NYC_TERMS.search(html_content):
        analysis['nyc_bonus'] = 10
    
    # 10. Broken links sample (we'll implement this separately for performance)
    # For now, we'll set a placeholder and implement it in the main analysis flow
    
    return analysis

def check_broken_links_sample(domain: str, soup: BeautifulSoup, max_links: int = 10) -> int:
    """
    Check a sample of internal links for broken ones.
    
    Args:
        domain: Domain to check links for
        soup: BeautifulSoup object
        max_links: Maximum number of links to check
        
    Returns:
        Number of broken links found
    """
    try:
        # Find all links
        links = soup.find_all('a', href=True)
        
        # Filter for same-host links
        same_host_links = []
        for link in links:
            href = link.get('href', '')
            if href.startswith('/') or href.startswith(domain) or href.startswith(f'https://{domain}'):
                same_host_links.append(href)
        
        # Sample up to max_links
        sample = same_host_links[:max_links]
        
        broken_count = 0
        session = requests.Session()
        session.headers.update({'User-Agent': 'Lead-Finder/1.0'})
        
        for link in sample:
            try:
                # Normalize URL
                if link.startswith('/'):
                    full_url = f"https://{domain}{link}"
                elif link.startswith('http'):
                    full_url = link
                else:
                    full_url = f"https://{domain}/{link}"
                
                response = session.head(full_url, allow_redirects=True, timeout=6)
                if response.status_code >= 400:
                    broken_count += 1
                    
            except Exception:
                broken_count += 1
                
        return broken_count
        
    except Exception:
        return 0 
# Enhanced JavaScript and resource loading error detection
RE_THEMEPUNCH = re.compile(r"jquery\.themepunch|revolution.*slider", re.I)
RE_FOUC_ERRORS = re.compile(r"layout.*forced.*before.*loaded|flash.*unstyled.*content|fouc", re.I)
RE_JQUERY_OLD = re.compile(r"jquery.*1\.\d+|jquery.*2\.\d+", re.I)
RE_CONSOLE_ERRORS = re.compile(r"console\.(error|warn)|\.min\.js.*error", re.I)
RE_OUTDATED_PLUGINS = re.compile(r"(revolution|slider|themepunch|visual.*composer|js.*composer)", re.I)

def detect_javascript_errors(html_content: str) -> dict:
    """
    Detect JavaScript errors and outdated plugin indicators.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Dictionary with JavaScript error indicators
    """
    analysis = {
        'themepunch_detected': False,
        'fouc_issues': False,
        'old_jquery_detected': False,
        'console_errors': False,
        'outdated_plugins': [],
        'js_loading_issues': False
    }
    
    html_lower = html_content.lower()
    
    # 1. ThemePunch/Revolution Slider detection
    if RE_THEMEPUNCH.search(html_content):
        analysis['themepunch_detected'] = True
        analysis['outdated_plugins'].append('Revolution Slider')
    
    # 2. FOUC (Flash of Unstyled Content) issues
    if RE_FOUC_ERRORS.search(html_content):
        analysis['fouc_issues'] = True
        analysis['js_loading_issues'] = True
    
    # 3. Old jQuery detection (more comprehensive)
    if RE_JQUERY_OLD.search(html_content):
        analysis['old_jquery_detected'] = True
    
    # 4. Console error patterns
    if RE_CONSOLE_ERRORS.search(html_content):
        analysis['console_errors'] = True
    
    # 5. Outdated plugin detection
    plugin_matches = RE_OUTDATED_PLUGINS.findall(html_content)
    if plugin_matches:
        analysis['outdated_plugins'].extend(plugin_matches)
    
    # 6. JavaScript loading order issues
    if 'script' in html_lower and 'stylesheet' in html_lower:
        # Check if scripts are loaded before stylesheets
        script_pos = html_lower.find('<script')
        style_pos = html_lower.find('<link')
        if script_pos != -1 and style_pos != -1 and script_pos < style_pos:
            analysis['js_loading_issues'] = True
    
    return analysis

def analyze_html_for_outdated_sites_enhanced(html_content: str, url: str, soup: BeautifulSoup = None) -> dict:
    """
    Enhanced HTML analysis including JavaScript error detection.
    
    Args:
        html_content: Raw HTML content
        url: URL being analyzed
        soup: Pre-parsed BeautifulSoup object (optional)
        
    Returns:
        Dictionary with comprehensive outdated site indicators
    """
    # Get base analysis
    analysis = analyze_html_for_outdated_sites(html_content, url, soup)
    
    # Add JavaScript error detection
    js_analysis = detect_javascript_errors(html_content)
    
    # Merge JavaScript analysis
    analysis.update(js_analysis)
    
    # Calculate additional score based on JavaScript issues
    js_score_bonus = 0
    if js_analysis['themepunch_detected']:
        js_score_bonus += 15  # High value - Revolution Slider is a red flag
    if js_analysis['fouc_issues']:
        js_score_bonus += 10  # Performance issue
    if js_analysis['old_jquery_detected']:
        js_score_bonus += 8   # Security/performance issue
    if js_analysis['console_errors']:
        js_score_bonus += 5   # Quality issue
    if js_analysis['js_loading_issues']:
        js_score_bonus += 6   # Performance issue
    
    analysis['js_score_bonus'] = js_score_bonus
    
    return analysis

def calculate_lead_score_enhanced(lead_data: dict) -> Tuple[int, str]:
    """
    Enhanced lead scoring including JavaScript error detection.
    
    Args:
        lead_data: Lead data dictionary with enhanced outdated site indicators
        
    Returns:
        Tuple of (score, tier)
    """
    score = 0
    
    # Performance scoring (desktop-first)
    if lead_data.get('psi_perf_desktop') and lead_data['psi_perf_desktop'] <= 60:
        score += 25
    if lead_data.get('ttfb_ms') and lead_data['ttfb_ms'] >= 1200:
        score += 15
    if lead_data.get('lcp_ms') and lead_data['lcp_ms'] >= 4000:
        score += 15
    
    # Security/modern web indicators
    if lead_data.get('mixed_content') or lead_data.get('http_only'):
        score += 15
    if lead_data.get('no_hsts'):
        score += 5
    
    # Builder/Stack debt (highest ROI)
    if lead_data.get('builder') == 'Divi':
        score += 20
    elif lead_data.get('builder') in ['Elementor', 'WPBakery']:
        score += 12
    if lead_data.get('old_jquery'):
        score += 10
    if lead_data.get('bootstrap_v3'):
        score += 6
    
    # JavaScript error detection (NEW!)
    if lead_data.get('themepunch_detected'):
        score += 15  # Revolution Slider is a major red flag
    if lead_data.get('fouc_issues'):
        score += 10  # Flash of unstyled content
    if lead_data.get('old_jquery_detected'):
        score += 8   # Old jQuery versions
    if lead_data.get('console_errors'):
        score += 5   # Console errors
    if lead_data.get('js_loading_issues'):
        score += 6   # JavaScript loading order issues
    
    # Basic SEO/Accessibility
    if lead_data.get('missing_title'):
        score += 8
    if lead_data.get('missing_meta_desc'):
        score += 6
    if lead_data.get('missing_schema'):
        score += 5
    if lead_data.get('accessibility_poor'):
        score += 8
    
    # Content/UX red flags
    if lead_data.get('copyright_outdated'):
        score += 6
    if lead_data.get('broken_links_count', 0) >= 2:
        score += 10
    
    # NYC relevance bonus
    score += lead_data.get('nyc_bonus', 0)
    
    # Cap score between 0 and 100
    score = max(0, min(100, score))
    
    # Determine tier based on enhanced scoring
    if score >= 70:
        tier = "A"  # Human review ASAP
    elif score >= 50:
        tier = "B"  # Queue for review
    else:
        tier = "C"  # Low priority
    
    return score, tier
