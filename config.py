"""
Configuration constants for the Lead Finder system.
"""

# Host exclusions for SERP gating
EXCLUDES_HOST = [
    "yelp", "facebook", "instagram", "linkedin", "opentable", "resy",
    "tockhq", "google", "archive.org", "github", "tripadvisor", "zomato",
    "grubhub", "doordash", "uber", "lyft"
]

# TLD exclusions
EXCLUDES_TLD = [".edu", ".gov", ".ac.", ".mil", ".int"]

# File extension exclusions
EXCLUDES_EXT = [".pdf", ".xml", ".txt", ".gz", ".zip", ".rar", ".doc", ".docx"]

# Path exclusions
EXCLUDES_PATH = [
    "sitemap", "/feed", "/tag/", "/category/", "/author/", "nav.php", "go.php",
    "/20/", "/2023/", "/2022/", "/2021/", "/2020/"
]

# Fetch configuration
FETCH = {
    "connect": 5,           # seconds
    "read": 10,             # seconds
    "max_bytes": 1_500_000, # 1.5MB
    "per_host_rps": 1,      # requests per second per host
    "global_rps": 5,        # global requests per second
    "max_per_domain": 6,    # max requests per domain
    "max_concurrent": 5     # max concurrent domain probes
}

# PageSpeed Insights thresholds
PSI_THRESH = {
    "perf_bad": 50,         # Performance score threshold
    "lcp_bad": 10_000,      # LCP threshold in ms
    "cls_bad": 0.25,        # CLS threshold
    "ttfb_bad": 800         # TTFB threshold in ms
}

# Scoring thresholds
SCORE_MIN = 40              # Minimum score to save
TIER_A_MIN = 80             # Tier A minimum score
TIER_B_MIN = 60             # Tier B minimum score

# WordPress version thresholds
WP_VERSION_BAD = "5.8"      # WordPress versions below this are considered outdated
JQUERY_VERSION_BAD = "2.0"  # jQuery versions below this are considered outdated

# Probe paths for each domain
PROBE_PATHS = [
    "/", "/about", "/contact", "/services", "/blog", 
    "/wp-content/", "/readme.html", "/feed", "/wp-json/"
]

# Google Custom Search Engine configuration
CSE_CONFIG = {
    "results_per_page": 10,
    "max_pages": 2,
    "junk_ratio_threshold": 0.4  # Stop paginating if 40%+ results are junk
}

# Regex patterns for detection
REGEX_PATTERNS = {
    "wp_critical": [
        r"There has been a critical error on this website",
        r"Error establishing a database connection",
        r"Briefly unavailable for scheduled maintenance"
    ],
    "php_errors": [
        r"(?:Warning|Deprecated|Notice|Fatal error):",
        r"Parse error:",
        r"Fatal error:"
    ],
    "pharma_spam": [
        r"\b(viagra|cialis|levitra|tramadol|casino|porn|poker|forex)\b",
        r"[\u3040-\u30ff\u4e00-\u9faf]"  # Hiragana/Katakana/CJK
    ],
    "wp_version": [
        r'name=["\']generator["\'][^>]*content=["\'][^"\']*WordPress\s*([\d\.]+)',
        r'jquery(\.min)?\.js\?ver=(\d+\.\d+)'
    ],
    "seo_issues": [
        r"<title>\s*</title>",
        r'<meta\s+name=["\']description["\']\s*content=["\']\s*["\']',
        r'<meta\s+name=["\']robots["\']\s*content=["\'][^"\']*noindex'
    ],
    "mixed_content": [
        r'src=["\']http://[^"\']+["\']',
        r'href=["\']http://[^"\']+["\']'
    ]
} 