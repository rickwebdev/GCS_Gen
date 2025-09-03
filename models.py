"""
Data models for the Lead Finder system.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TechInfo(BaseModel):
    """Technical information about the website."""
    cms: Optional[str] = None
    wp_version: Optional[str] = None
    jquery_version: Optional[str] = None
    php_banner: bool = False
    readme_accessible: bool = False
    wp_json_accessible: bool = False


class SecurityInfo(BaseModel):
    """Security and HTTPS information."""
    https: bool = True
    mixed_content: bool = False
    hsts: bool = False
    insecure_assets: List[str] = Field(default_factory=list)


class SEOInfo(BaseModel):
    """SEO-related information."""
    title_missing: bool = False
    meta_desc_missing: bool = False
    robots_noindex: bool = False
    canonical: bool = False
    multiple_h1: bool = False
    thin_content: bool = False


class PSIResults(BaseModel):
    """PageSpeed Insights results."""
    perf: Optional[int] = None
    seo: Optional[int] = None
    accessibility: Optional[int] = None
    best_practices: Optional[int] = None
    lcp_ms: Optional[int] = None
    cls: Optional[float] = None
    ttfb_ms: Optional[int] = None
    fcp_ms: Optional[int] = None
    fid_ms: Optional[int] = None
    si: Optional[int] = None


class ContactInfo(BaseModel):
    """Contact information found on the website."""
    phone: Optional[str] = None
    email: Optional[str] = None
    form: bool = False
    address: Optional[str] = None
    business_hours: Optional[str] = None


class Lead(BaseModel):
    """Complete lead information for a website."""
    domain: str
    brand_name: Optional[str] = None
    owner_valid: bool = False
    platform_subdomain: bool = False
    
    # Technical details
    tech: TechInfo = Field(default_factory=TechInfo)
    security: SecurityInfo = Field(default_factory=SecurityInfo)
    seo: SEOInfo = Field(default_factory=SEOInfo)
    
    # Issues found
    errors: List[str] = Field(default_factory=list)
    hacked_signals: List[str] = Field(default_factory=list)
    
    # Performance data
    psi: Optional[PSIResults] = None
    
    # Contact information
    contact: ContactInfo = Field(default_factory=ContactInfo)
    
    # Scoring
    score: int = 0
    tier: str = "D"
    
    # Evidence
    evidence_urls: List[str] = Field(default_factory=list)
    
    # SEO Opportunity Mode fields (optional)
    best_rank: Optional[int] = None
    top_query: Optional[str] = None
    seo_opportunity: Optional[int] = None
    rank_queries: List[str] = Field(default_factory=list)
    
    # NEW: Performance override and spam analysis fields
    performance_override_reason: Optional[str] = None
    spam_confidence: Optional[str] = None
    vertical_tag: Optional[str] = None
    
    # NEW: Catch-all meta dict for future fields (logger-friendly)
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.now)
    last_checked: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchResult(BaseModel):
    """Individual search result from Google CSE."""
    title: str
    link: str
    snippet: str
    display_link: str
    is_junk: bool = False
    rejection_reason: Optional[str] = None


class SearchQuery(BaseModel):
    """Search query configuration."""
    query: str
    description: str
    category: str  # 'core', 'hacked', 'outdated_wp', 'seo', 'performance'


class CrawlResult(BaseModel):
    """Result of crawling a single page."""
    url: str
    status_code: int
    content: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: int = 0
    load_time_ms: float = 0.0
    error: Optional[str] = None


class DomainProbe(BaseModel):
    """Complete probe results for a domain."""
    domain: str
    root_url: str
    pages: List[CrawlResult] = Field(default_factory=list)
    total_pages: int = 0
    successful_pages: int = 0
    errors: List[str] = Field(default_factory=list)
    probe_time_ms: float = 0.0 