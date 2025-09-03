"""
PageSpeed Insights integration for performance analysis.
"""

import os
import time
import json
import requests
import random
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import config
from models import PSIResults
from utils import rate_limit_delay


class PageSpeedInsights:
    """Client for Google PageSpeed Insights API."""
    
    def __init__(self, api_keys: List[str] = None):
        """
        Initialize the PageSpeed Insights client.
        
        Args:
            api_keys: List of Google API keys (optional, can use env var)
        """
        if api_keys:
            self.api_keys = api_keys
        else:
            # Support multiple API keys from environment
            api_key = os.getenv('GOOGLE_API_KEY')
            if api_key:
                self.api_keys = [api_key]
            else:
                # Try to get multiple keys from environment
                self.api_keys = []
                for i in range(1, 6):  # Support up to 5 API keys
                    key = os.getenv(f'GOOGLE_API_KEY_{i}')
                    if key:
                        self.api_keys.append(key)
                
                if not self.api_keys:
                    raise ValueError("At least one Google API key is required for PageSpeed Insights")
        
        self.current_key_index = 0
        self.base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 24 * 60 * 60  # 24 hours in seconds
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 2.0  # Base delay in seconds
        self.max_delay = 60.0  # Maximum delay in seconds
        
        # API quota tracking
        self.quota_errors = 0
        self.last_quota_reset = time.time()
    
    def _get_next_api_key(self) -> str:
        """Get the next API key in rotation."""
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if a request should be retried."""
        if attempt >= self.max_retries:
            return False
        
        # Retry on network errors and server errors
        if isinstance(error, requests.exceptions.RequestException):
            return True
        
        # Retry on HTTP 5xx errors
        if hasattr(error, 'response') and error.response:
            if error.response.status_code >= 500:
                return True
            # Retry on rate limiting (429) and some 4xx errors
            if error.response.status_code in [429, 408, 413]:
                return True
        
        return False
    
    def _calculate_delay(self, attempt: int, error: Exception = None) -> float:
        """Calculate delay for exponential backoff with jitter."""
        # Exponential backoff
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, 0.1 * delay)
        delay += jitter
        
        # Special handling for rate limiting
        if hasattr(error, 'response') and error.response and error.response.status_code == 429:
            # Wait longer for rate limiting
            delay = max(delay, 30.0)
        
        return delay
    
    def _handle_quota_error(self, error: Exception):
        """Handle API quota errors."""
        self.quota_errors += 1
        current_time = time.time()
        
        # If we've hit multiple quota errors, wait longer
        if self.quota_errors >= 3:
            wait_time = min(300, self.quota_errors * 60)  # 5-15 minutes
            print(f"⚠️  Multiple quota errors detected. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            self.quota_errors = 0
            self.last_quota_reset = current_time
        
        # Reset quota errors after 1 hour
        if current_time - self.last_quota_reset > 3600:
            self.quota_errors = 0
            self.last_quota_reset = current_time
    
    def analyze_url(self, url: str, strategy: str = 'mobile', 
                   category: str = 'performance') -> Optional[PSIResults]:
        """
        Analyze a URL using PageSpeed Insights with retry logic.
        
        Args:
            url: URL to analyze
            strategy: 'mobile' or 'desktop'
            category: Analysis category (performance, accessibility, best-practices, seo)
            
        Returns:
            PSIResults object or None if analysis fails
        """
        # Check cache first
        cache_key = f"{url}_{strategy}_{category}"
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                print(f"Using cached PSI results for {url}")
                return cached_result
        
        # Try with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                # Get API key for this attempt
                api_key = self._get_next_api_key()
                
                # Build request parameters
                params = {
                    'url': url,
                    'key': api_key,
                    'strategy': strategy,
                    'category': category,
                    'utm_source': 'lead-finder'
                }
                
                # Make request with adaptive timeout
                timeout = min(30 + (attempt * 10), 60)  # Increase timeout with each retry
                response = requests.get(
                    self.base_url, 
                    params=params, 
                    timeout=timeout,
                    headers={'User-Agent': 'Lead-Finder/1.0'}
                )
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                psi_results = self._parse_psi_response(data)
                
                # Cache results
                self.cache[cache_key] = (psi_results, time.time())
                
                # Reset quota errors on success
                self.quota_errors = 0
                
                # Rate limiting
                rate_limit_delay(1.0 / config.FETCH['global_rps'])
                
                return psi_results
                
            except requests.exceptions.RequestException as e:
                print(f"PageSpeed Insights request failed for {url} (attempt {attempt + 1}): {e}")
                
                # Check if we should retry
                if self._should_retry(e, attempt):
                    delay = self._calculate_delay(attempt, e)
                    print(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    break
                    
            except Exception as e:
                print(f"Unexpected error analyzing {url}: {e}")
                break
        
        # If we get here, all retries failed
        print(f"Failed to analyze {url} after {self.max_retries + 1} attempts")
        return None
    
    def _parse_psi_response(self, data: Dict[str, Any]) -> PSIResults:
        """
        Parse PageSpeed Insights API response.
        
        Args:
            data: Raw API response data
            
        Returns:
            Parsed PSIResults object
        """
        try:
            # Extract lighthouse results
            lighthouse = data.get('lighthouseResult', {})
            categories = lighthouse.get('categories', {})
            
            # Extract category scores
            performance = categories.get('performance', {}).get('score')
            seo = categories.get('seo', {}).get('score')
            accessibility = categories.get('accessibility', {}).get('score')
            best_practices = categories.get('best-practices', {}).get('score')
            
            # Convert scores to percentages
            if performance is not None:
                performance = int(performance * 100)
            if seo is not None:
                seo = int(seo * 100)
            if accessibility is not None:
                accessibility = int(accessibility * 100)
            if best_practices is not None:
                best_practices = int(best_practices * 100)
            
            # Extract Core Web Vitals
            audits = lighthouse.get('audits', {})
            
            # Largest Contentful Paint (LCP)
            lcp_audit = audits.get('largest-contentful-paint', {})
            lcp_ms = None
            if lcp_audit and 'numericValue' in lcp_audit:
                lcp_ms = int(lcp_audit['numericValue'])
            
            # Cumulative Layout Shift (CLS)
            cls_audit = audits.get('cumulative-layout-shift', {})
            cls = None
            if cls_audit and 'numericValue' in cls_audit:
                cls = cls_audit['numericValue']
            
            # First Input Delay (FID)
            fid_audit = audits.get('max-potential-fid', {})
            fid_ms = None
            if fid_audit and 'numericValue' in fid_audit:
                fid_ms = int(fid_audit['numericValue'])
            
            # First Contentful Paint (FCP)
            fcp_audit = audits.get('first-contentful-paint', {})
            fcp_ms = None
            if fcp_audit and 'numericValue' in fcp_audit:
                fcp_ms = int(fcp_audit['numericValue'])
            
            # Speed Index
            si_audit = audits.get('speed-index', {})
            si = None
            if si_audit and 'numericValue' in si_audit:
                si = int(si_audit['numericValue'])
            
            # Time to First Byte (TTFB) - from loading experience
            loading_experience = data.get('loadingExperience', {})
            ttfb_ms = None
            if loading_experience:
                metrics = loading_experience.get('metrics', {})
                ttfb_metric = metrics.get('FIRST_CONTENTFUL_PAINT_MS', {})
                if ttfb_metric and 'percentile' in ttfb_metric:
                    ttfb_ms = int(ttfb_metric['percentile'])
            
            return PSIResults(
                perf=performance,
                seo=seo,
                accessibility=accessibility,
                best_practices=best_practices,
                lcp_ms=lcp_ms,
                cls=cls,
                ttfb_ms=ttfb_ms,
                fcp_ms=fcp_ms,
                fid_ms=fid_ms,
                si=si
            )
            
        except Exception as e:
            print(f"Error parsing PSI response: {e}")
            return PSIResults()
    
    def get_performance_summary(self, psi_results: PSIResults) -> Dict[str, Any]:
        """
        Get a summary of performance issues.
        
        Args:
            psi_results: PSI results to analyze
            
        Returns:
            Dictionary with performance summary
        """
        summary = {
            'issues': [],
            'critical': False,
            'score': 'unknown'
        }
        
        if psi_results.perf is not None:
            if psi_results.perf < 50:
                summary['score'] = 'poor'
                summary['critical'] = True
                summary['issues'].append(f"Performance score: {psi_results.perf}/100 (critical)")
            elif psi_results.perf < 80:
                summary['score'] = 'needs_improvement'
                summary['issues'].append(f"Performance score: {psi_results.perf}/100 (needs improvement)")
            else:
                summary['score'] = 'good'
        
        # Check Core Web Vitals
        if psi_results.lcp_ms and psi_results.lcp_ms > config.PSI_THRESH['lcp_bad']:
            summary['issues'].append(f"LCP: {psi_results.lcp_ms}ms (should be < {config.PSI_THRESH['lcp_bad']}ms)")
            summary['critical'] = True
        
        if psi_results.cls and psi_results.cls > config.PSI_THRESH['cls_bad']:
            summary['issues'].append(f"CLS: {psi_results.cls:.3f} (should be < {config.PSI_THRESH['cls_bad']})")
            summary['critical'] = True
        
        if psi_results.ttfb_ms and psi_results.ttfb_ms > config.PSI_THRESH['ttfb_bad']:
            summary['issues'].append(f"TTFB: {psi_results.ttfb_ms}ms (should be < {config.PSI_THRESH['ttfb_bad']}ms)")
        
        return summary
    
    def analyze_multiple_urls(self, urls: list, strategy: str = 'mobile') -> Dict[str, PSIResults]:
        """
        Analyze multiple URLs concurrently.
        
        Args:
            urls: List of URLs to analyze
            strategy: Analysis strategy
            
        Returns:
            Dictionary mapping URLs to PSI results
        """
        results = {}
        
        for url in urls:
            print(f"Analyzing {url} with PageSpeed Insights...")
            result = self.analyze_url(url, strategy)
            if result:
                results[url] = result
            
            # Rate limiting between requests
            time.sleep(1)
        
        return results
    
    def save_cache_to_file(self, filename: str) -> None:
        """Save cache to a JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.cache, f, indent=2)
            print(f"Cache saved to {filename}")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def load_cache_from_file(self, filename: str) -> None:
        """Load cache from a JSON file."""
        try:
            with open(filename, 'r') as f:
                self.cache = json.load(f)
            print(f"Cache loaded from {filename}")
        except Exception as e:
            print(f"Error loading cache: {e}")


def create_psi_client() -> PageSpeedInsights:
    """Create a PageSpeed Insights client."""
    return PageSpeedInsights()


def create_psi_client_with_keys(api_keys: List[str]) -> PageSpeedInsights:
    """Create a PageSpeed Insights client with specific API keys."""
    return PageSpeedInsights(api_keys=api_keys)


def create_psi_client_from_env() -> PageSpeedInsights:
    """Create a PageSpeed Insights client from environment variables."""
    # Try to get multiple API keys
    api_keys = []
    
    # Primary key
    primary_key = os.getenv('GOOGLE_API_KEY')
    if primary_key:
        api_keys.append(primary_key)
    
    # Additional keys
    for i in range(1, 6):
        key = os.getenv(f'GOOGLE_API_KEY_{i}')
        if key and key not in api_keys:
            api_keys.append(key)
    
    if not api_keys:
        raise ValueError("No Google API keys found in environment variables")
    
    print(f"🔑 Using {len(api_keys)} API key(s) for PageSpeed Insights")
    return PageSpeedInsights(api_keys=api_keys)


def analyze_lead_performance(lead_data: Dict[str, Any], psi_client: PageSpeedInsights) -> Dict[str, Any]:
    """
    Analyze performance for a lead and update the data.
    
    Args:
        lead_data: Lead data dictionary
        psi_client: PageSpeed Insights client
        
    Returns:
        Updated lead data with PSI results
    """
    url = lead_data.get('domain')
    if not url:
        return lead_data
    
    # Ensure URL has scheme
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    try:
        # Analyze with PageSpeed Insights
        psi_results = psi_client.analyze_url(url)
        
        if psi_results:
            lead_data['psi'] = psi_results.dict()
            
            # Get performance summary
            performance_summary = psi_client.get_performance_summary(psi_results)
            lead_data['performance_summary'] = performance_summary
            
            print(f"Performance analysis for {url}: {performance_summary['score']}")
            
        else:
            print(f"Failed to analyze performance for {url}")
            
    except Exception as e:
        print(f"Error analyzing performance for {url}: {e}")
    
    return lead_data 