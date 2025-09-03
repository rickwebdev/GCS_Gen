"""
Web crawler for probing websites and extracting information.
"""

import re
import time
import asyncio
import aiohttp
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import config
from models import CrawlResult, DomainProbe
from utils import rate_limit_delay, extract_domain


class WebCrawler:
    """Asynchronous web crawler for probing websites."""
    
    def __init__(self, max_concurrent: int = 5, timeout: int = 10):
        """
        Initialize the crawler.
        
        Args:
            max_concurrent: Maximum concurrent requests
            timeout: Request timeout in seconds
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def __aenter__(self):
        """Async context manager entry."""
        timeout_config = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=config.FETCH['connect'],
            sock_read=config.FETCH['read']
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout_config,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; LeadFinder/1.0; +https://example.com/bot)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def probe_domain(self, root_url: str) -> DomainProbe:
        """
        Probe a domain by crawling multiple paths.
        
        Args:
            root_url: Root URL of the domain
            
        Returns:
            DomainProbe with results
        """
        start_time = time.time()
        domain = extract_domain(root_url)
        
        probe = DomainProbe(
            domain=domain,
            root_url=root_url
        )
        
        # Create tasks for all probe paths
        tasks = []
        for path in config.PROBE_PATHS:
            url = urljoin(root_url, path)
            task = self._crawl_page(url)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                probe.errors.append(str(result))
            elif isinstance(result, CrawlResult):
                probe.pages.append(result)
                if result.status_code < 400:
                    probe.successful_pages += 1
                probe.total_pages += 1
        
        probe.probe_time_ms = (time.time() - start_time) * 1000
        
        return probe
    
    async def _crawl_page(self, url: str) -> CrawlResult:
        """
        Crawl a single page.
        
        Args:
            url: URL to crawl
            
        Returns:
            CrawlResult with page information
        """
        async with self.semaphore:
            start_time = time.time()
            
            try:
                async with self.session.get(url, allow_redirects=True) as response:
                    content = await response.text()
                    
                    # Check content size
                    if len(content) > config.FETCH['max_bytes']:
                        content = content[:config.FETCH['max_bytes']]
                    
                    load_time = (time.time() - start_time) * 1000
                    
                    return CrawlResult(
                        url=url,
                        status_code=response.status,
                        content=content,
                        content_type=response.headers.get('content-type', ''),
                        size_bytes=len(content),
                        load_time_ms=load_time
                    )
                    
            except asyncio.TimeoutError:
                return CrawlResult(
                    url=url,
                    status_code=0,
                    error="timeout",
                    load_time_ms=(time.time() - start_time) * 1000
                )
            except Exception as e:
                return CrawlResult(
                    url=url,
                    status_code=0,
                    error=str(e),
                    load_time_ms=(time.time() - start_time) * 1000
                )
    
    def extract_technical_info(self, pages: List[CrawlResult]) -> Dict:
        """
        Extract technical information from crawled pages.
        
        Args:
            pages: List of crawled pages
            
        Returns:
            Dictionary with technical information
        """
        tech_info = {
            'cms': None,
            'wp_version': None,
            'jquery_version': None,
            'php_banner': False,
            'readme_accessible': False,
            'wp_json_accessible': False
        }
        
        for page in pages:
            if not page.content or page.status_code >= 400:
                continue
                
            content = page.content.lower()
            
            # Check for WordPress
            if 'wordpress' in content or 'wp-content' in content:
                tech_info['cms'] = 'WordPress'
                
                # Extract WordPress version
                wp_version_match = re.search(
                    r'name=["\']generator["\'][^>]*content=["\'][^"\']*wordpress\s*([\d\.]+)',
                    page.content,
                    re.IGNORECASE
                )
                if wp_version_match:
                    tech_info['wp_version'] = wp_version_match.group(1)
                
                # Check for jQuery version
                jquery_match = re.search(
                    r'jquery(\.min)?\.js\?ver=(\d+\.\d+)',
                    page.content,
                    re.IGNORECASE
                )
                if jquery_match:
                    tech_info['jquery_version'] = jquery_match.group(2)
            
            # Check for PHP errors
            if any(error in content for error in ['warning:', 'deprecated:', 'fatal error:', 'parse error:']):
                tech_info['php_banner'] = True
            
            # Check for readme accessibility
            if 'readme.html' in page.url and page.status_code == 200:
                tech_info['readme_accessible'] = True
            
            # Check for wp-json accessibility
            if 'wp-json' in page.url and page.status_code == 200:
                tech_info['wp_json_accessible'] = True
        
        return tech_info
    
    def extract_security_info(self, pages: List[CrawlResult]) -> Dict:
        """
        Extract security information from crawled pages.
        
        Args:
            pages: List of crawled pages
            
        Returns:
            Dictionary with security information
        """
        security_info = {
            'https': True,
            'mixed_content': False,
            'hsts': False,
            'insecure_assets': []
        }
        
        for page in pages:
            if not page.content or page.status_code >= 400:
                continue
            
            # Check if page is HTTPS
            if page.url.startswith('http://'):
                security_info['https'] = False
            
            # Check for mixed content
            if 'https://' in page.url:
                http_assets = re.findall(r'src=["\']http://[^"\']+["\']', page.content)
                http_assets.extend(re.findall(r'href=["\']http://[^"\']+["\']', page.content))
                
                if http_assets:
                    security_info['mixed_content'] = True
                    security_info['insecure_assets'].extend(http_assets[:5])  # Limit to first 5
        
        return security_info
    
    def extract_seo_info(self, pages: List[CrawlResult]) -> Dict:
        """
        Extract SEO information from crawled pages.
        
        Args:
            pages: List of crawled pages
            
        Returns:
            Dictionary with SEO information
        """
        seo_info = {
            'title_missing': False,
            'meta_desc_missing': False,
            'robots_noindex': False,
            'canonical': False,
            'multiple_h1': False,
            'thin_content': False
        }
        
        for page in pages:
            if not page.content or page.status_code >= 400:
                continue
            
            soup = BeautifulSoup(page.content, 'html.parser')
            
            # Check title
            title = soup.find('title')
            if not title or not title.get_text().strip():
                seo_info['title_missing'] = True
            
            # Check meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if not meta_desc or not meta_desc.get('content', '').strip():
                seo_info['meta_desc_missing'] = True
            
            # Check robots
            robots = soup.find('meta', attrs={'name': 'robots'})
            if robots and 'noindex' in robots.get('content', '').lower():
                seo_info['robots_noindex'] = True
            
            # Check canonical
            canonical = soup.find('link', attrs={'rel': 'canonical'})
            if canonical:
                seo_info['canonical'] = True
            
            # Check H1 tags
            h1_tags = soup.find_all('h1')
            if len(h1_tags) > 1:
                seo_info['multiple_h1'] = True
            
            # Check content length
            text_content = soup.get_text()
            if len(text_content.strip()) < 100:  # Very thin content
                seo_info['thin_content'] = True
        
        return seo_info
    
    def extract_errors(self, pages: List[CrawlResult]) -> List[str]:
        """
        Extract error messages from crawled pages.
        
        Args:
            pages: List of crawled pages
            
        Returns:
            List of error messages found
        """
        errors = []
        
        for page in pages:
            if not page.content or page.status_code >= 400:
                continue
            
            content = page.content
            
            # Check for WordPress critical errors
            for pattern in config.REGEX_PATTERNS['wp_critical']:
                if re.search(pattern, content, re.IGNORECASE):
                    errors.append(f"WordPress critical error: {pattern}")
            
            # Check for PHP errors
            for pattern in config.REGEX_PATTERNS['php_errors']:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:3]:  # Limit to first 3 matches
                    errors.append(f"PHP error: {match}")
        
        return errors
    
    def detect_hacked_signals(self, pages: List[CrawlResult]) -> List[str]:
        """
        Detect signs of hacked or compromised websites with confidence scores.
        
        Args:
            pages: List of crawled pages
            
        Returns:
            List of hacked signals found
        """
        signals = []
        
        for page in pages:
            if not page.content or page.status_code >= 400:
                continue
            
            content = page.content.lower()
            
            # Check for high-confidence spam patterns (100% confidence)
            high_confidence_spam = self._check_spam_patterns(content, config.REGEX_PATTERNS['high_confidence_spam'], confidence=100)
            if high_confidence_spam:
                signals.extend(high_confidence_spam)
            
            # Check for medium-confidence spam patterns (60% confidence from config)
            medium_confidence_spam = self._check_spam_patterns(content, config.REGEX_PATTERNS['medium_confidence_spam'], confidence=60)
            if medium_confidence_spam:
                signals.extend(medium_confidence_spam)
            
            # Check for low-confidence spam patterns (20% confidence from config)
            low_confidence_spam = self._check_spam_patterns(content, config.REGEX_PATTERNS['low_confidence_spam'], confidence=20)
            if low_confidence_spam:
                signals.extend(low_confidence_spam)
            
            # Check for suspicious paths in URL
            suspicious_paths = [
                '/wp-content/uploads/', '/cache/', '/tmp/', '/backup/',
                '/wp-backup/', '/shell.php', '/old/', '/wp-admin.php'
            ]
            
            for path in suspicious_paths:
                if path in page.url.lower():
                    signals.append(f"Suspicious path: {path}")
            
            # Check for hidden spam content
            if self._detect_hidden_spam(content):
                signals.append("Hidden spam content detected (100% confidence)")
        
        return signals
    
    def _check_spam_patterns(self, content: str, patterns: list, confidence: int) -> list:
        """Check for spam patterns with confidence scoring."""
        spam_signals = []
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    unique_matches = set(matches)
                    
                    # Different thresholds based on confidence level
                    if confidence == 100:  # High confidence
                        if len(unique_matches) >= 1:  # Single match is enough
                            spam_signals.append(f"Spam content ({confidence}% confidence): {pattern}")
                    elif confidence == 60:  # Medium confidence (updated from 70)
                        if len(unique_matches) >= 2:  # Need 2+ matches
                            spam_signals.append(f"Spam content ({confidence}% confidence): {pattern}")
                    elif confidence == 20:  # Low confidence (updated from 30)
                        if len(unique_matches) >= 3:  # Need 3+ matches
                            spam_signals.append(f"Spam content ({confidence}% confidence): {pattern}")
                            
            except re.error as e:
                print(f"⚠️  Invalid regex pattern: {pattern} - {e}")
                continue
        
        return spam_signals
    
    def calculate_spam_confidence(self, signals: list) -> dict:
        """Calculate overall spam confidence score and recommendation."""
        high_confidence_count = sum(1 for signal in signals if "100% confidence" in signal)
        medium_confidence_count = sum(1 for signal in signals if "60% confidence" in signal)
        low_confidence_count = sum(1 for signal in signals if "20% confidence" in signal)
        
        # Calculate weighted confidence score
        total_confidence = (high_confidence_count * 100) + (medium_confidence_count * 60) + (low_confidence_count * 20)
        total_signals = high_confidence_count + medium_confidence_count + low_confidence_count
        
        if total_signals == 0:
            avg_confidence = 0
        else:
            avg_confidence = total_confidence / total_signals
        
        # Determine recommendation
        if avg_confidence >= 90:  # Increased from 80
            recommendation = "REJECT - High confidence spam"
        elif avg_confidence >= 40:  # Reduced from 50
            recommendation = "REVIEW - Medium confidence, needs human review"
        elif avg_confidence >= 15:  # Reduced from 20
            recommendation = "ACCEPT - Low confidence, likely false positive"
        else:
            recommendation = "ACCEPT - No spam detected"
        
        return {
            'avg_confidence': avg_confidence,
            'high_confidence_count': high_confidence_count,
            'medium_confidence_count': medium_confidence_count,
            'low_confidence_count': low_confidence_count,
            'total_signals': total_signals,
            'recommendation': recommendation
        }
    
    def _is_legitimate_business_content(self, content: str) -> bool:
        """Check if content contains legitimate business terms that shouldn't be flagged as spam."""
        legitimate_business_terms = [
            'dermatology', 'dermatologist', 'medspa', 'medical spa', 'aesthetics',
            'cosmetic', 'plastic surgery', 'salon', 'hair salon', 'nail salon',
            'beauty salon', 'spa', 'wellness', 'fitness', 'yoga', 'pilates',
            'dental', 'dentist', 'orthodontist', 'law firm', 'attorney', 'lawyer',
            'legal', 'practice', 'clinic', 'medical', 'health', 'care',
            'appointment', 'consultation', 'treatment', 'service', 'professional'
        ]
        
        # Count legitimate business terms
        business_term_count = 0
        for term in legitimate_business_terms:
            if term in content:
                business_term_count += 1
        
        # If content has multiple legitimate business terms, it's likely not spam
        return business_term_count >= 2
    
    def _detect_hidden_spam(self, content: str) -> bool:
        """Detect hidden spam content using CSS and HTML patterns."""
        # Check for display:none or visibility:hidden with spam keywords
        hidden_patterns = [
            r'<div[^>]*style\s*=\s*["\'][^"\']*display\s*:\s*none[^"\']*["\'][^>]*>.*?(?:viagra|cialis|casino|porn|forex)',
            r'<span[^>]*style\s*=\s*["\'][^"\']*visibility\s*:\s*hidden[^"\']*["\'][^>]*>.*?(?:viagra|cialis|casino|porn|forex)',
            r'<div[^>]*class\s*=\s*["\'][^"\']*hidden[^"\']*["\'][^>]*>.*?(?:viagra|cialis|casino|porn|forex)'
        ]
        
        for pattern in hidden_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    def extract_contact_info(self, pages: List[CrawlResult]) -> Dict:
        """
        Extract contact information from crawled pages.
        
        Args:
            pages: List of crawled pages
            
        Returns:
            Dictionary with contact information
        """
        contact_info = {
            'phone': None,
            'email': None,
            'form': False,
            'address': None,
            'business_hours': None
        }
        
        for page in pages:
            if not page.content or page.status_code >= 400:
                continue
            
            content = page.content
            
            # Extract phone numbers
            phone_patterns = [
                r'tel:([+\d\s\-\(\)]+)',
                r'phone[:\s]+([+\d\s\-\(\)]+)',
                r'call[:\s]+([+\d\s\-\(\)]+)'
            ]
            
            for pattern in phone_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match and not contact_info['phone']:
                    contact_info['phone'] = match.group(1).strip()
                    break
            
            # Extract email addresses
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            email_match = re.search(email_pattern, content)
            if email_match and not contact_info['email']:
                contact_info['email'] = email_match.group(0)
            
            # Check for contact forms
            if re.search(r'<form[^>]*>', content, re.IGNORECASE):
                contact_info['form'] = True
            
            # Extract address information
            address_patterns = [
                r'address[:\s]+([^<>\n]+)',
                r'location[:\s]+([^<>\n]+)',
                r'[0-9]+\s+[a-zA-Z\s]+(?:street|st|avenue|ave|road|rd|drive|dr)',
            ]
            
            for pattern in address_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match and not contact_info['address']:
                    contact_info['address'] = match.group(1).strip()
                    break
        
        return contact_info


async def probe_domains(domains: List[str], max_concurrent: int = 5) -> List[DomainProbe]:
    """
    Probe multiple domains concurrently.
    
    Args:
        domains: List of domain URLs to probe
        max_concurrent: Maximum concurrent probes
        
    Returns:
        List of DomainProbe results
    """
    async with WebCrawler(max_concurrent) as crawler:
        tasks = [crawler.probe_domain(domain) for domain in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"Error probing domain: {result}")
            else:
                valid_results.append(result)
        
        return valid_results 