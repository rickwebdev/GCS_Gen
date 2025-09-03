"""
Google Custom Search Engine client for finding website prospects.
"""

import os
import time
from typing import List, Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config
from models import SearchResult, SearchQuery
from utils import is_junk_url, rate_limit_delay


class GoogleCSEClient:
    """Client for Google Custom Search Engine API."""
    
    def __init__(self, api_key: str, cse_id: str):
        """
        Initialize the Google CSE client.
        
        Args:
            api_key: Google API key
            cse_id: Custom Search Engine ID
        """
        self.api_key = api_key
        self.cse_id = cse_id
        self.service = build('customsearch', 'v1', developerKey=api_key)
        
    def search(self, query: str, region: Optional[str] = None, 
               max_pages: int = None) -> List[SearchResult]:
        """
        Perform a search using Google CSE.
        
        Args:
            query: Search query string
            region: Geographic region (e.g., 'us', 'uk', 'ca')
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of search results
        """
        if max_pages is None:
            max_pages = config.CSE_CONFIG['max_pages']
            
        results = []
        junk_count = 0
        total_count = 0
        
        try:
            for page in range(max_pages):
                start_index = (page * config.CSE_CONFIG['results_per_page']) + 1
                
                # Build search parameters
                search_params = {
                    'q': query,
                    'cx': self.cse_id,
                    'start': start_index,
                    'num': config.CSE_CONFIG['results_per_page']
                }
                
                if region:
                    search_params['gl'] = region
                
                # Perform search
                search_results = self.service.cse().list(**search_params).execute()
                
                if 'items' not in search_results:
                    break
                
                page_results = []
                for item in search_results['items']:
                    total_count += 1
                    
                    # Check if result is junk
                    is_junk = is_junk_url(item['link'])
                    if is_junk:
                        junk_count += 1
                    
                    result = SearchResult(
                        title=item.get('title', ''),
                        link=item['link'],
                        snippet=item.get('snippet', ''),
                        display_link=item.get('displayLink', ''),
                        is_junk=is_junk,
                        rejection_reason='junk_url' if is_junk else None
                    )
                    
                    page_results.append(result)
                
                results.extend(page_results)
                
                # Check junk ratio and stop if too high
                if total_count > 0:
                    junk_ratio = junk_count / total_count
                    if junk_ratio >= config.CSE_CONFIG['junk_ratio_threshold']:
                        print(f"Stopping pagination due to high junk ratio: {junk_ratio:.2f}")
                        break
                
                # Rate limiting
                rate_limit_delay(1.0 / config.FETCH['global_rps'])
                
        except HttpError as e:
            print(f"Google CSE API error: {e}")
        except Exception as e:
            print(f"Unexpected error during search: {e}")
        
        return results


class QueryManager:
    """Manages search queries for different categories."""
    
    def __init__(self):
        """Initialize with predefined query sets."""
        self.queries = self._build_queries()
    
    def _build_queries(self) -> List[SearchQuery]:
        """Build the predefined search query sets."""
        queries = [
            # Core "owner-site" discovery (any niche)
            SearchQuery(
                query='(inurl:contact OR inurl:about OR inurl:services OR inurl:menu) '
                      '(site:.com OR site:.net OR site:.org OR site:.biz OR site:.nyc) '
                      '("tel:" OR "schema.org" OR "json-ld" OR "addressLocality" OR "Powered by WordPress") '
                      '-site:yelp.* -site:facebook.com -site:instagram.com -site:linkedin.com -site:twitter.com '
                      '-site:opentable.* -site:resy.* -site:wix.com -site:squarespace.com -site:google.com '
                      '-filetype:pdf -filetype:xml -filetype:txt -inurl:sitemap -inurl:feed -inurl:tag -inurl:category',
                description="Core owner site discovery - finds business websites with contact info",
                category="core"
            ),
            
            # Hacked-looking dorks (owner domains likely affected)
            SearchQuery(
                query='("viagra" OR "cialis" OR "オンラインカジノ" OR "카지노") '
                      '(inurl:/blog/ OR inurl:/wp-content/ OR inurl:/news/) '
                      '-site:reddit.com -site:twitter.com -site:facebook.com',
                description="Hacked sites with pharma/casino spam",
                category="hacked"
            ),
            
            SearchQuery(
                query='site:.com ("viagra" OR "casino") ("Powered by WordPress" OR inurl:wp-content) -site:yelp.*',
                description="WordPress sites with spam content",
                category="hacked"
            ),
            
            SearchQuery(
                query='("There has been a critical error on this website." OR "Error establishing a database connection") '
                      '(site:.com OR site:.net) -wordpress.org',
                description="Sites with critical WordPress errors",
                category="hacked"
            ),
            
            # Outdated WordPress / visible version
            SearchQuery(
                query='inurl:readme.html "WordPress" -wordpress.org',
                description="WordPress sites with accessible readme files",
                category="outdated_wp"
            ),
            
            SearchQuery(
                query='inurl:/wp-includes/js/jquery/jquery.js?ver=1. -site:wordpress.org',
                description="WordPress sites with old jQuery versions",
                category="outdated_wp"
            ),
            
            SearchQuery(
                query='intitle:"Powered by WordPress" (inurl:about OR inurl:contact) -wordpress.org',
                description="WordPress sites with visible generator info",
                category="outdated_wp"
            ),
            
            # Performance/SEO fishing
            SearchQuery(
                query='("Powered by WordPress" OR "Theme by") (inurl:portfolio OR inurl:services) '
                      '("tel:" OR address) -site:themeforest.net -site:wordpress.org',
                description="Business WordPress sites for performance analysis",
                category="performance"
            ),
            
            # Local business focus
            SearchQuery(
                query='("restaurant" OR "dentist" OR "lawyer" OR "plumber" OR "electrician") '
                      '("tel:" OR "address" OR "hours") ("Powered by WordPress" OR inurl:wp-content) '
                      '-site:yelp.* -site:facebook.com -site:instagram.com',
                description="Local business WordPress sites",
                category="local_business"
            ),
            
            # Contractor/Service business focus
            SearchQuery(
                query='("contractor" OR "construction" OR "renovation" OR "repair") '
                      '("contact us" OR "get quote" OR "free estimate") '
                      '("Powered by WordPress" OR inurl:wp-content) -site:homeadvisor.com -site:angie.com',
                description="Contractor and service business sites",
                category="contractors"
            ),
            
            # Healthcare focus
            SearchQuery(
                query='("doctor" OR "physician" OR "clinic" OR "medical") '
                      '("appointment" OR "contact" OR "hours") '
                      '("Powered by WordPress" OR inurl:wp-content) -site:healthgrades.com -site:zocdoc.com',
                description="Healthcare provider websites",
                category="healthcare"
            )
        ]
        
        return queries
    
    def get_queries_by_category(self, category: str) -> List[SearchQuery]:
        """Get queries by category."""
        return [q for q in self.queries if q.category == category]
    
    def get_all_queries(self) -> List[SearchQuery]:
        """Get all available queries."""
        return self.queries
    
    def add_custom_query(self, query: str, description: str, category: str) -> None:
        """Add a custom search query."""
        self.queries.append(SearchQuery(
            query=query,
            description=description,
            category=category
        ))


def create_cse_client() -> GoogleCSEClient:
    """Create a Google CSE client from environment variables."""
    api_key = os.getenv('GOOGLE_API_KEY')
    cse_id = os.getenv('GOOGLE_CSE_ID')
    
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    if not cse_id:
        raise ValueError("GOOGLE_CSE_ID environment variable is required")
    
    return GoogleCSEClient(api_key, cse_id) 