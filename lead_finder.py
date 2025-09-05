"""
Main Lead Finder orchestrator for finding and analyzing website prospects.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import config
from models import Lead, SearchResult, DomainProbe
from google_cse import GoogleCSEClient, QueryManager, create_cse_client
from crawler import WebCrawler, probe_domains
from pagespeed import PageSpeedInsights, create_psi_client, analyze_lead_performance
from utils import (
    extract_domain, canonicalize_url, get_root_url, is_platform_subdomain,
    is_owner_site, extract_brand_name, calculate_lead_score_enhanced, sanitize_filename
)
from bs4 import BeautifulSoup


class LeadFinder:
    """Main orchestrator for finding and analyzing website leads."""
    
    def __init__(self, google_api_key: str = None, google_cse_id: str = None):
        """
        Initialize the Lead Finder.
        
        Args:
            google_api_key: Google API key (optional, can use env var)
            google_cse_id: Google CSE ID (optional, can use env var)
        """
        self.cse_client = create_cse_client()
        
        # Use enhanced PSI client with multiple API key support
        try:
            self.psi_client = create_psi_client_from_env()
        except Exception as e:
            print(f"⚠️  Warning: Could not create enhanced PSI client: {e}")
            print("Falling back to basic PSI client...")
            self.psi_client = create_psi_client()
        
        self.query_manager = QueryManager()
        
        # Tracking
        self.processed_domains: Set[str] = set()
        self.leads: List[Lead] = []
        self.rejected_domains: Dict[str, str] = {}  # domain -> reason
        
        # Statistics
        self.stats = {
            'searches_performed': 0,
            'domains_found': 0,
            'domains_probed': 0,
            'leads_generated': 0,
            'domains_rejected': 0,
            'start_time': time.time()
        }
    
    async def find_leads(self, categories: List[str] = None, 
                        regions: List[str] = None, max_leads: int = 100) -> List[Lead]:
        """
        Main method to find leads.
        
        Args:
            categories: List of query categories to use
            regions: List of geographic regions
            max_leads: Maximum number of leads to generate
            
        Returns:
            List of Lead objects
        """
        print(f"Starting Lead Finder - targeting {max_leads} leads")
        print(f"Categories: {categories or 'all'}")
        print(f"Regions: {regions or 'global'}")
        
        # Get queries to run
        if categories:
            queries = []
            for category in categories:
                queries.extend(self.query_manager.get_queries_by_category(category))
        else:
            queries = self.query_manager.get_all_queries()
        
        print(f"Running {len(queries)} search queries...")
        
        # Process each query
        for query in queries:
            if len(self.leads) >= max_leads:
                print(f"Reached target of {max_leads} leads, stopping...")
                break
            
            print(f"\n--- Running query: {query.description} ---")
            await self._process_query(query, regions)
            
            # Rate limiting between queries
            await asyncio.sleep(2)
        
        # Final processing
        await self._finalize_leads()
        
        # Print summary
        self._print_summary()
        
        return self.leads
    
    async def find_seo_opportunities(self, areas: List[str], verticals: List[str], 
                                   rank_min: int, rank_max: int, max_pages: int = 4, 
                                   max_leads: int = 100) -> List[Lead]:
        """
        Find SEO opportunities in specific areas and verticals.
        
        Args:
            areas: List of NYC areas to target
            verticals: List of business verticals to target
            rank_min: Minimum SERP rank to consider
            rank_max: Maximum SERP rank to consider
            max_pages: Maximum pages to search per query
            max_leads: Maximum leads to generate
            
        Returns:
            List of Lead objects with SEO opportunity data
        """
        print(f"Starting SEO Opportunity Finder - targeting {max_leads} leads")
        print(f"Areas: {', '.join(areas)}")
        print(f"Verticals: {', '.join(verticals)}")
        print(f"Rank window: #{rank_min}-#{rank_max}")
        print(f"Max pages per query: {max_pages}")
        
        # Generate intent queries for each area x vertical combination
        queries = self._generate_seo_queries(areas, verticals)
        print(f"Generated {len(queries)} SEO opportunity queries")
        
        # Track domains and their best ranks
        domain_ranks = {}  # domain -> {best_rank, queries, serp_position}
        
        # Process each query
        for query in queries:
            if len(self.leads) >= max_leads:
                print(f"Reached target of {max_leads} leads, stopping...")
                break
            
            print(f"\n--- Running SEO query: {query['description']} ---")
            await self._process_seo_query(query, rank_min, rank_max, max_pages, domain_ranks)
            
            # Rate limiting between queries
            await asyncio.sleep(2)
        
        # Process domains that meet rank criteria
        await self._process_seo_domains(domain_ranks, max_leads)
        
        # Final processing
        await self._finalize_leads()
        
        # Print summary
        self._print_summary()
        
        return self.leads
    
    def _generate_seo_queries(self, areas: List[str], verticals: List[str]) -> List[Dict]:
        """Generate SEO opportunity queries for area x vertical combinations."""
        queries = []
        
        for area in areas:
            for vertical in verticals:
                # Create intent-based queries
                query_templates = [
                    f'"{area}" "{vertical}" "contact us" "hours" "menu"',
                    f'"{area}" "{vertical}" "reservations" "appointments" "services"',
                    f'"{area}" "{vertical}" "phone" "address" "location"',
                    f'"{area}" "{vertical}" "reviews" "best" "top"'
                ]
                
                for template in query_templates:
                    queries.append({
                        'query': template,
                        'description': f'{area} {vertical} - {template[:50]}...',
                        'area': area,
                        'vertical': vertical
                    })
        
        return queries
    
    async def _process_seo_query(self, query: Dict, rank_min: int, rank_max: int, 
                                max_pages: int, domain_ranks: Dict):
        """Process a single SEO opportunity query."""
        try:
            # Run search with extended pagination
            results = self.cse_client.search(query['query'], max_pages=max_pages)
            
            print(f"Found {len(results)} results")
            
            # Track domains and their positions
            for i, result in enumerate(results):
                if result.is_junk:
                    continue
                
                domain = extract_domain(result.link)
                serp_position = i + 1
                
                # Check if domain is in rank window
                if rank_min <= serp_position <= rank_max:
                    if domain not in domain_ranks:
                        domain_ranks[domain] = {
                            'best_rank': serp_position,
                            'queries': [query['description']],
                            'serp_positions': [serp_position],
                            'top_query': query['description']
                        }
                    else:
                        # Update best rank if this is better
                        if serp_position < domain_ranks[domain]['best_rank']:
                            domain_ranks[domain]['best_rank'] = serp_position
                            domain_ranks[domain]['top_query'] = query['description']
                        
                        domain_ranks[domain]['queries'].append(query['description'])
                        domain_ranks[domain]['serp_positions'].append(serp_position)
            
        except Exception as e:
            print(f"Error processing SEO query '{query['description']}': {e}")
    
    async def _process_seo_domains(self, domain_ranks: Dict, max_leads: int):
        """Process domains that meet SEO opportunity criteria."""
        print(f"\nProcessing {len(domain_ranks)} domains in rank window...")
        
        # Convert domains to URLs
        urls = []
        for domain in domain_ranks.keys():
            if not domain.startswith(('http://', 'https://')):
                urls.append(f"https://{domain}")
            else:
                urls.append(domain)
        
        # Probe domains concurrently
        probes = await probe_domains(urls, max_concurrent=config.FETCH['max_concurrent'])
        
        # Process each probe
        for probe in probes:
            if len(self.leads) >= max_leads:
                break
            
            await self._process_seo_domain_probe(probe, domain_ranks)
    
    async def _process_seo_domain_probe(self, probe: DomainProbe, domain_ranks: Dict):
        """Process a single SEO domain probe."""
        domain = probe.domain
        
        # Early exclusion check - skip previously scanned domains
        from config import PREVIOUSLY_SCANNED_DOMAINS
        if domain in PREVIOUSLY_SCANNED_DOMAINS:
            print(f"Skipping {domain}: previously scanned")
            self.stats['domains_rejected'] += 1
            return
        
        # Mark as processed
        self.processed_domains.add(domain)
        self.stats['domains_probed'] += 1
        
        print(f"Processing SEO domain: {domain}")
        
        try:
            # Extract information from probe (reuse existing logic)
            crawler = WebCrawler()
            
            tech_info = crawler.extract_technical_info(probe.pages)
            security_info = crawler.extract_security_info(probe.pages)
            seo_info = crawler.extract_seo_info(probe.pages)
            errors = crawler.extract_errors(probe.pages)
            hacked_signals = crawler.detect_hacked_signals(probe.pages)
            contact_info = crawler.extract_contact_info(probe.pages)
            
            # Determine ownership
            owner_valid = False
            platform_subdomain = is_platform_subdomain(probe.root_url)
            
            if not platform_subdomain:
                for page in probe.pages:
                    if page.content and page.status_code < 400:
                        if is_owner_site(page.content, domain):
                            owner_valid = True
                            break
            
            # Extract brand name
            brand_name = None
            for page in probe.pages:
                if page.content and page.status_code < 400:
                    soup = BeautifulSoup(page.content, 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        brand_name = extract_brand_name(title_tag.get_text(), domain)
                        break
            
            # Get rank information
            rank_data = domain_ranks.get(domain, {})
            best_rank = rank_data.get('best_rank', 50)
            top_query = rank_data.get('top_query', '')
            rank_queries = rank_data.get('queries', [])
            
            # Create lead data with SEO fields
            lead_data = {
                'domain': domain,
                'brand_name': brand_name,
                'owner_valid': owner_valid,
                'platform_subdomain': platform_subdomain,
                'tech': tech_info,
                'security': security_info,
                'seo': seo_info,
                'errors': errors,
                'hacked_signals': hacked_signals,
                'contact': contact_info,
                'evidence_urls': [p.url for p in probe.pages[:3] if p.status_code < 400],
                'best_rank': best_rank,
                'top_query': top_query,
                'rank_queries': rank_queries
            }
            
            # Validate lead
            if not self._validate_lead(lead_data):
                reason = "failed_validation"
                self.rejected_domains[domain] = reason
                self.stats['domains_rejected'] += 1
                print(f"Rejected {domain}: {reason}")
                return
            
            # Analyze performance with PageSpeed Insights
            if owner_valid:
                lead_data = await self._analyze_performance(lead_data)
            
            # Calculate SEO opportunity score
            score, tier = calculate_lead_score_enhanced(lead_data)
            lead_data['score'] = score
            lead_data['tier'] = tier
            lead_data['seo_opportunity'] = score
            
            # Create Lead object
            lead = Lead(**lead_data)
            
            # Add to leads if score is high enough OR if it's a critical performance issue
            if score >= config.SCORE_MIN or lead_data.get('critical_performance_issue', False):
                if lead_data.get('critical_performance_issue', False):
                    print(f"🚨 PERFORMANCE OVERRIDE: {domain} (Score: {score}, Tier: {tier}, Rank: #{best_rank}) - Critical performance issue, always saving!")
                self.leads.append(lead)
                self.stats['leads_generated'] += 1
                print(f"Added SEO lead: {domain} (Score: {score}, Tier: {tier}, Rank: #{best_rank})")
            else:
                reason = f"low_score_{score}"
                self.rejected_domains[domain] = reason
                self.stats['domains_rejected'] += 1
                print(f"Rejected {domain}: {reason}")
                
        except Exception as e:
            print(f"Error processing SEO domain {domain}: {e}")
            self.rejected_domains[domain] = f"processing_error: {str(e)}"
            self.stats['domains_rejected'] += 1
    
    async def _process_query(self, query: Any, regions: List[str] = None) -> None:
        """Process a single search query."""
        try:
            # Run search
            if regions:
                for region in regions:
                    if len(self.leads) >= 100:  # Check again
                        break
                    print(f"Searching in region: {region}")
                    results = self.cse_client.search(query.query, region=region)
                    await self._process_search_results(results, query)
            else:
                results = self.cse_client.search(query.query)
                await self._process_search_results(results, query)
                
        except Exception as e:
            print(f"Error processing query '{query.description}': {e}")
    
    async def _process_search_results(self, results: List[SearchResult], query: Any) -> None:
        """Process search results from Google CSE."""
        # Filter out junk results
        valid_results = [r for r in results if not r.is_junk]
        
        print(f"Found {len(results)} results, {len(valid_results)} valid")
        
        if not valid_results:
            return
        
        # Extract unique domains
        domains = set()
        for result in valid_results:
            domain = extract_domain(result.link)
            if domain not in self.processed_domains:
                domains.add(domain)
        
        print(f"Found {len(domains)} new domains to probe")
        
        # Probe domains
        if domains:
            await self._probe_domains(list(domains))
    
    async def _probe_domains(self, domains: List[str]) -> None:
        """Probe a list of domains with improved parallel processing."""
        # Convert domains to URLs
        urls = []
        for domain in domains:
            if not domain.startswith(('http://', 'https://')):
                urls.append(f"https://{domain}")
            else:
                urls.append(domain)
        
        print(f"Probing {len(urls)} domains...")
        
        # Increase concurrency for better performance
        max_concurrent = min(len(urls), config.FETCH['max_concurrent'] * 2)
        
        # Probe domains concurrently with improved error handling
        try:
            probes = await probe_domains(urls, max_concurrent=max_concurrent)
            
            # Process each probe with better error handling
            for probe in probes:
                if len(self.leads) >= 100:  # Check again
                    break
                
                try:
                    await self._process_domain_probe(probe)
                except Exception as e:
                    print(f"⚠️  Error processing probe for {probe.domain}: {e}")
                    self.rejected_domains[probe.domain] = f"probe_processing_error: {str(e)}"
                    self.stats['domains_rejected'] += 1
                    
        except Exception as e:
            print(f"⚠️  Error during domain probing: {e}")
            # Fall back to sequential processing
            print("Falling back to sequential processing...")
            for url in urls:
                try:
                    domain = extract_domain(url)
                    if len(self.leads) >= 100:
                        break
                    
                    # Create a simple probe
                    from models import DomainProbe, CrawlResult
                    simple_probe = DomainProbe(
                        domain=domain,
                        pages=[CrawlResult(url=url, status_code=0, content="")]
                    )
                    await self._process_domain_probe(simple_probe)
                    
                except Exception as probe_error:
                    print(f"⚠️  Error processing {url}: {probe_error}")
                    self.rejected_domains[extract_domain(url)] = f"fallback_error: {str(probe_error)}"
                    self.stats['domains_rejected'] += 1
    
    async def _process_domain_probe(self, probe: DomainProbe) -> None:
        """Process a single domain probe."""
        domain = probe.domain
        
        # Early exclusion check - skip previously scanned domains
        from config import PREVIOUSLY_SCANNED_DOMAINS
        if domain in PREVIOUSLY_SCANNED_DOMAINS:
            print(f"Skipping {domain}: previously scanned")
            self.stats['domains_rejected'] += 1
            return
        
        # Mark as processed
        self.processed_domains.add(domain)
        self.stats['domains_probed'] += 1
        
        print(f"Processing domain: {domain}")
        
        try:
            # Extract information from probe
            crawler = WebCrawler()
            
            # Extract technical info
            tech_info = crawler.extract_technical_info(probe.pages)
            
            # Extract security info
            security_info = crawler.extract_security_info(probe.pages)
            
            # Extract SEO info
            seo_info = crawler.extract_seo_info(probe.pages)
            
            # Extract errors
            errors = crawler.extract_errors(probe.pages)
            
            # Extract hacked signals
            hacked_signals = crawler.detect_hacked_signals(probe.pages)
            
            # Extract contact info
            contact_info = crawler.extract_contact_info(probe.pages)
            
            # Determine ownership
            owner_valid = False
            platform_subdomain = is_platform_subdomain(probe.root_url)
            
            if not platform_subdomain:
                # Check if it's an owner site
                for page in probe.pages:
                    if page.content and page.status_code < 400:
                        if is_owner_site(page.content, domain):
                            owner_valid = True
                            break
            
            # Extract brand name
            brand_name = None
            for page in probe.pages:
                if page.content and page.status_code < 400:
                    soup = BeautifulSoup(page.content, 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        brand_name = extract_brand_name(title_tag.get_text(), domain)
                        break
            
            # Create lead data
            lead_data = {
                'domain': domain,
                'brand_name': brand_name,
                'owner_valid': owner_valid,
                'platform_subdomain': platform_subdomain,
                'tech': tech_info,
                'security': security_info,
                'seo': seo_info,
                'errors': errors,
                'hacked_signals': hacked_signals,
                'contact': contact_info,
                'evidence_urls': [p.url for p in probe.pages[:3] if p.status_code < 400]
            }
            
            # 🚨 CRITICAL FIX: Analyze performance FIRST (before spam validation)
            # This ensures we capture PSI data even if spam filter fires
            if owner_valid:
                lead_data = await self._analyze_performance(lead_data)
            
            # 🆕 ENHANCED: Analyze HTML for outdated site indicators
            # This catches Divi/Elementor fingerprints, technical debt, and content freshness
            if owner_valid and probe.pages:
                try:
                    from utils import analyze_html_for_outdated_sites_enhanced, check_broken_links_sample
                    
                    # Get the main page content for analysis
                    main_page = None
                    for page in probe.pages:
                        if page.content and page.status_code < 400:
                            main_page = page
                            break
                    
                    if main_page:
                        # Analyze HTML for outdated indicators
                        html_analysis = analyze_html_for_outdated_sites_enhanced(
                            main_page.content, 
                            main_page.url
                        )
                        
                        # Check broken links sample
                        soup = BeautifulSoup(main_page.content, 'html.parser')
                        broken_links = check_broken_links_sample(domain, soup)
                        html_analysis['broken_links_count'] = broken_links
                        
                        # Merge analysis into lead data
                        for key, value in html_analysis.items():
                            lead_data[key] = value
                        
                        # Log key findings
                        if html_analysis.get('builder'):
                            print(f"🔧 Builder detected: {html_analysis['builder']}")
                        if html_analysis.get('old_jquery'):
                            print(f"⚠️  Old jQuery detected")
                        if html_analysis.get('mixed_content'):
                            print(f"⚠️  Mixed content detected")
                        if broken_links >= 2:
                            print(f"🔗 Broken links: {broken_links}")
                            
                except Exception as e:
                    print(f"Warning: HTML analysis failed for {domain}: {e}")
            
            # 🚨 CRITICAL FIX: Check for critical performance issues BEFORE spam validation
            # Sites with perf_score < 50 should ALWAYS go to human review
            critical_performance_issue = False
            performance_override_reason = None
            if lead_data.get('psi') and lead_data['psi'].get('perf'):
                perf_score = lead_data['psi']['perf']
                if perf_score <= 45:
                    critical_performance_issue = True
                    performance_override_reason = "perf_low"
                    print(f"🚨 CRITICAL: {domain} has performance score {perf_score}/100 - ALWAYS allowing through for human review!")
                elif perf_score <= 60:
                    print(f"⚠️  MODERATE: {domain} has performance score {perf_score}/100 - performance opportunity")
            
            # Add vertical categorization
            vertical_tag = self.categorize_business_vertical(lead_data)
            lead_data['vertical_tag'] = vertical_tag
            
            # Validate lead (but allow critical performance issues through)
            if not self._validate_lead(lead_data, critical_performance_issue, performance_override_reason):
                reason = "failed_validation"
                self.rejected_domains[domain] = reason
                self.stats['domains_rejected'] += 1
                print(f"Rejected {domain}: {reason}")
                return
            
            # Calculate score using enhanced outdated site detection
            score, tier = calculate_lead_score_enhanced(lead_data)
            lead_data['score'] = score
            lead_data['tier'] = tier
            
            # Create Lead object
            lead = Lead(**lead_data)
            
            # Add performance override reason if applicable
            if performance_override_reason:
                setattr(lead, 'performance_override_reason', performance_override_reason)
            
            # Add spam confidence for CSV export
            if lead_data.get('hacked_signals'):
                crawler = WebCrawler()
                spam_analysis = crawler.calculate_spam_confidence(lead_data['hacked_signals'])
                setattr(lead, 'spam_confidence', f"{spam_analysis['avg_confidence']:.1f}%")
            
            # Add to leads if score is high enough OR if it's a critical performance issue
            if score >= config.SCORE_MIN or critical_performance_issue:
                if critical_performance_issue:
                    print(f"🚨 PERFORMANCE OVERRIDE: {domain} (Score: {score}, Tier: {tier}) - Critical performance issue, always saving!")
                self.leads.append(lead)
                self.stats['leads_generated'] += 1
                print(f"Added lead: {domain} (Score: {score}, Tier: {tier})")
            else:
                reason = f"low_score_{score}"
                self.rejected_domains[domain] = reason
                self.stats['domains_rejected'] += 1
                print(f"Rejected {domain}: {reason}")
                
        except Exception as e:
            print(f"Error processing domain {domain}: {e}")
            self.rejected_domains[domain] = f"processing_error: {str(e)}"
            self.stats['domains_rejected'] += 1
    
    def _validate_lead(self, lead_data: Dict[str, Any], critical_performance_issue: bool = False, performance_override_reason: Optional[str] = None) -> bool:
        """Validate if a lead meets basic criteria."""
        # Must have a valid domain
        if not lead_data.get('domain'):
            return False
        
        # Filter out non-business domains (focus on .com, .net, .co, etc.)
        domain = lead_data.get('domain', '').lower()
        if any(domain.endswith(tld) for tld in ['.org', '.edu', '.gov', '.mil', '.int', '.ac']):
            return False
        
        # Filter out previously scanned domains
        from config import PREVIOUSLY_SCANNED_DOMAINS
        if domain in PREVIOUSLY_SCANNED_DOMAINS:
            return False
        
        # Must not be a platform subdomain
        if lead_data.get('platform_subdomain'):
            return False
        
        # Must have some content (at least one successful page)
        if not lead_data.get('evidence_urls'):
            return False
        
        # Allow leads with critical performance issues through
        if critical_performance_issue:
            print(f"✅ {lead_data.get('domain', 'unknown')}: Critical performance issue detected, allowing through for human review.")
            if performance_override_reason:
                print(f"   📊 Override reason: {performance_override_reason}")
            return True
        
        # Enhanced validation: CONFIDENCE-BASED SPAM DETECTION
        if lead_data.get('hacked_signals'):
            # Calculate spam confidence
            crawler = WebCrawler()
            spam_analysis = crawler.calculate_spam_confidence(lead_data['hacked_signals'])
            
            # Check if this is a legitimate business
            is_legitimate_business = False
            if lead_data.get('brand_name'):
                brand_lower = lead_data['brand_name'].lower()
                business_terms = [
                    # Medical & Wellness
                    'dermatology', 'medspa', 'salon', 'dental', 'spa', 'wellness', 'fitness', 'medical', 'aesthetics', 'cosmetic', 'plastic surgery',
                    'orthodontist', 'orthodontic', 'lasik', 'eye surgery', 'vision correction', 'ophthalmologist', 'optometrist', 'chiropractor', 'chiropractic',
                    # Legal & Professional Services
                    'law firm', 'attorney', 'law office', 'legal practice', 'lawyer', 'cpa', 'accountant', 'accounting firm', 'tax preparation', 'tax services',
                    # Hospitality & Food
                    'catering', 'catering company', 'event catering', 'restaurant', 'dining', 'fine dining', 'wine bar', 'cocktail bar', 'bar', 'hotel', 'boutique hotel', 'luxury hotel',
                    # Events & Venues
                    'event venue', 'wedding venue', 'party venue', 'venue', 'events',
                    # Retail & Luxury
                    'jeweler', 'jewelry store', 'fine jewelry', 'gallery', 'art gallery',
                    # Home Services
                    'remodeler', 'home remodeling', 'kitchen remodeling', 'bathroom remodeling', 'hvac', 'heating and cooling', 'air conditioning', 'roofing', 'roofing company', 'roof repair',
                    # Automotive
                    'auto repair', 'car repair', 'automotive service', 'dealership', 'car dealership', 'auto dealership',
                    # General Business
                    'clinic', 'specialist', 'practice', 'studio', 'center', 'group'
                ]
                if any(term in brand_lower for term in business_terms):
                    is_legitimate_business = True
            
            # CONFIDENCE-BASED VALIDATION
            avg_confidence = spam_analysis['avg_confidence']
            
            # 🚨 CRITICAL FIX: If this is a critical performance issue, ALWAYS allow through
            if critical_performance_issue:
                print(f"🚨 OVERRIDE: {lead_data.get('domain', 'unknown')}: Critical performance issue - bypassing spam filter for human review!")
                return True
            
            if avg_confidence >= 90:  # Increased from 80
                # High confidence spam - reject regardless of business type
                print(f"❌ Rejecting {lead_data.get('domain', 'unknown')}: High confidence spam ({avg_confidence:.1f}%)")
                return False
            elif avg_confidence >= 40:  # Reduced from 50
                # Medium confidence - review bucket for legitimate businesses
                if is_legitimate_business:
                    # Legitimate businesses with medium confidence get review
                    print(f"⚠️  {lead_data.get('domain', 'unknown')}: Medium spam confidence ({avg_confidence:.1f}%) - adding to review bucket")
                    return True
                else:
                    # Non-business sites with medium confidence get rejected
                    print(f"❌ Rejecting {lead_data.get('domain', 'unknown')}: Medium confidence spam ({avg_confidence:.1f}%) for non-business site")
                    return False
            elif avg_confidence >= 15:  # Reduced from 20
                # Low confidence - likely false positive, allow through
                print(f"✅ {lead_data.get('domain', 'unknown')}: Low spam confidence ({avg_confidence:.1f}%) - likely false positive")
                return True
            else:
                # No spam detected
                print(f"✅ {lead_data.get('domain', 'unknown')}: No spam detected")
                return True
        
        # Reject if hidden spam is detected (regardless of business type)
        if lead_data.get('hacked_signals'):
            if any('Hidden spam content detected (100% confidence)' in signal for signal in lead_data['hacked_signals']):
                print(f"❌ Rejecting {lead_data.get('domain', 'unknown')}: Hidden spam detected")
                return False
        
        return True

    def categorize_business_vertical(self, lead_data: Dict[str, Any]) -> str:
        """Categorize business into vertical for sorting and analysis."""
        if not lead_data.get('brand_name'):
            return "unknown"
        
        brand_lower = lead_data['brand_name'].lower()
        
        # Medical & Beauty
        medical_terms = ['dermatology', 'medspa', 'salon', 'dental', 'orthodontist', 'orthodontic', 'lasik', 'eye surgery', 'vision correction', 'ophthalmologist', 'optometrist', 'chiropractor', 'chiropractic', 'clinic', 'medical', 'aesthetics', 'cosmetic', 'plastic surgery', 'spa', 'wellness', 'fitness', 'beauty']
        if any(term in brand_lower for term in medical_terms):
            return "medical_beauty"
        
        # Restaurant & Hospitality
        hospitality_terms = ['restaurant', 'dining', 'fine dining', 'wine bar', 'cocktail bar', 'bar', 'hotel', 'boutique hotel', 'luxury hotel', 'catering', 'catering company', 'event catering', 'venue', 'events', 'wedding venue', 'party venue']
        if any(term in brand_lower for term in hospitality_terms):
            return "restaurant_hospitality"
        
        # Retail & Luxury
        retail_terms = ['jeweler', 'jewelry store', 'fine jewelry', 'gallery', 'art gallery', 'store', 'shop', 'boutique']
        if any(term in brand_lower for term in retail_terms):
            return "retail_luxury"
        
        # Home Services
        home_terms = ['remodeler', 'home remodeling', 'kitchen remodeling', 'bathroom remodeling', 'hvac', 'heating and cooling', 'air conditioning', 'roofing', 'roofing company', 'roof repair']
        if any(term in brand_lower for term in home_terms):
            return "home_services"
        
        # Automotive
        auto_terms = ['auto repair', 'car repair', 'automotive service', 'dealership', 'car dealership', 'auto dealership']
        if any(term in brand_lower for term in auto_terms):
            return "automotive"
        
        # Legal & Professional
        legal_terms = ['law firm', 'attorney', 'law office', 'legal practice', 'lawyer', 'cpa', 'accountant', 'accounting firm', 'tax preparation', 'tax services']
        if any(term in brand_lower for term in legal_terms):
            return "legal_professional"
        
        return "other"


    async def _analyze_performance(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance for a lead."""
        try:
            lead_data = analyze_lead_performance(lead_data, self.psi_client)
        except Exception as e:
            print(f"Error analyzing performance: {e}")
        
        return lead_data


    async def _finalize_leads(self) -> None:
        """Finalize lead processing."""
        # Sort leads by score (highest first)
        self.leads.sort(key=lambda x: x.score, reverse=True)
        
        # Update metadata
        for lead in self.leads:
            lead.last_checked = datetime.now()


    def _print_summary(self) -> None:
        """Print summary statistics."""
        runtime = time.time() - self.stats['start_time']
        
        print("\n" + "="*50)
        print("LEAD FINDER SUMMARY")
        print("="*50)
        print(f"Runtime: {runtime:.1f} seconds")
        print(f"Domains probed: {self.stats['domains_probed']}")
        print(f"Leads generated: {self.stats['leads_generated']}")
        print(f"Domains rejected: {self.stats['domains_rejected']}")
        
        # Tier breakdown
        tier_counts = {}
        for lead in self.leads:
            tier = lead.tier
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        print("\nLeads by tier:")
        for tier in sorted(tier_counts.keys()):
            print(f"  Tier {tier}: {tier_counts[tier]}")
        
        print("\nTop 5 leads:")
        for i, lead in enumerate(self.leads[:5]):
            print(f"  {i+1}. {lead.domain} - Score: {lead.score}, Tier: {lead.tier}")


    def save_leads(self, filename: str = None) -> str:
        """Save leads to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reports/leads_{timestamp}.json"
        elif not filename.startswith('reports/'):
            filename = f"reports/{filename}"
        
        # Convert leads to dictionaries
        leads_data = [lead.dict() for lead in self.leads]
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(leads_data, f, indent=2, default=str)
        
        print(f"Saved {len(self.leads)} leads to {filename}")
        return filename


    def save_rejected_domains(self, filename: str = None) -> str:
        """Save rejected domains to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reports/rejected_domains_{timestamp}.json"
        elif not filename.startswith('reports/'):
            filename = f"reports/{filename}"
        
        with open(filename, 'w') as f:
            json.dump(self.rejected_domains, f, indent=2)
        
        print(f"Saved {len(self.rejected_domains)} rejected domains to {filename}")
        return filename


    def get_leads_by_tier(self, tier: str) -> List[Lead]:
        """Get leads by tier."""
        return [lead for lead in self.leads if lead.tier == tier]


    def get_leads_by_score_range(self, min_score: int, max_score: int) -> List[Lead]:
        """Get leads within a score range."""
        return [lead for lead in self.leads if min_score <= lead.score <= max_score]


async def main():
    """Main function for running the Lead Finder."""
    # Create Lead Finder instance
    finder = LeadFinder()
    
    # Define search parameters
    categories = ['core', 'hacked', 'outdated_wp']  # Focus on these categories
    regions = ['us', 'ca', 'uk']  # Target these regions
    max_leads = 50  # Target number of leads
    
    try:
        # Find leads
        leads = await finder.find_leads(
            categories=categories,
            regions=regions,
            max_leads=max_leads
        )
        
        # Save results
        finder.save_leads()
        finder.save_rejected_domains()
        
        print(f"\nLead generation complete! Found {len(leads)} qualified leads.")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 