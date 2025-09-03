"""
PageSpeed Insights integration for performance analysis.
"""

import os
import time
import json
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import config
from models import PSIResults
from utils import rate_limit_delay


class PageSpeedInsights:
    """Client for Google PageSpeed Insights API."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the PageSpeed Insights client.
        
        Args:
            api_key: Google API key (optional, can use env var)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key is required for PageSpeed Insights")
        
        self.base_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 24 * 60 * 60  # 24 hours in seconds
    
    def analyze_url(self, url: str, strategy: str = 'mobile', 
                   category: str = 'performance') -> Optional[PSIResults]:
        """
        Analyze a URL using PageSpeed Insights.
        
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
        
        try:
            # Build request parameters
            params = {
                'url': url,
                'key': self.api_key,
                'strategy': strategy,
                'category': category,
                'utm_source': 'lead-finder'
            }
            
            # Make request
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            psi_results = self._parse_psi_response(data)
            
            # Cache results
            self.cache[cache_key] = (psi_results, time.time())
            
            # Rate limiting
            rate_limit_delay(1.0 / config.FETCH['global_rps'])
            
            return psi_results
            
        except requests.exceptions.RequestException as e:
            print(f"PageSpeed Insights request failed for {url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error analyzing {url}: {e}")
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