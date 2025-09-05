"""
Configuration constants for the Lead Finder system.
"""

# Host exclusions for SERP gating
EXCLUDES_HOST = [
    "yelp", "facebook", "instagram", "linkedin", "opentable", "resy",
    "tockhq", "google", "archive.org", "github", "tripadvisor", "zomato",
    "grubhub", "doordash", "uber", "lyft"
]

# TLD exclusions - focus on business domains only
EXCLUDES_TLD = [".edu", ".gov", ".ac.", ".mil", ".int", ".org"]

# File extension exclusions
EXCLUDES_EXT = [".pdf", ".xml", ".txt", ".gz", ".zip", ".rar", ".doc", ".docx"]

# Path exclusions
EXCLUDES_PATH = [
    "sitemap", "/feed", "/tag/", "/category/", "/author/", "nav.php", "go.php",
    "/20/", "/2023/", "/2022/", "/2021/", "/2020/"
]

# Previously scanned domains - exclude to avoid re-analysis
PREVIOUSLY_SCANNED_DOMAINS = [
    # Derm / Medspa / Health
    "springstderm.com", "tribecaskincenter.com", "thedermspecs.com", "peninsuladermatologyva.com",
    "dermatologycenterofwilliamsburg.com", "skinlab-nyc.com", "schweigerderm.com", "triparkderm.com",
    "pschr.com", "sinyderm.com", "pariserderm.com", "weiserskin.com", "couturemedspa.com",
    "evolvemedspa.com", "the-mspa.com", "brooklyn-dermatology.com", "newbloomderm.com",
    
    # Spas / Salons / Wellness
    "soho-hawaii.com", "soho-wellness.com", "williamsburgsaltspa.com", "abathhouse.com",
    "tribecasalon.com", "havenspa.nyc", "blissspa.com", "sohonailsspachesterfield.com",
    "sohobubblespanyc.com", "sohosalons.com", "aestheticswall.com", "artisticnailwilliamsburg.com",
    "williamsburgbeautyspa.com", "damianwestsalon.com", "sohonailsandlashes.com", "shampooavenueb.com",
    "thesisleyspa.com", "tokuyamasalon.com", "romanksalon.com",
    
    # Restaurants / Hospitality
    "lapecorabianca.com", "onewhitestreetnyc.com", "tamarindtribeca.com", "charliebirdnyc.com",
    "dellasnyc.com", "fatcanarywilliamsburg.com", "leyacawilliamsburg.org", "foodforthoughtrestaurant.com",
    "themanner.com", "juliettebk.com", "walkerhotels.com", "thegreenwichhotel.com",
    "rosewoodhotels.com", "thedominickhotel.com", "spa.cowshed.com", "fabioscalia.com",
    "laicale.com", "lilianewyork.com", "estelanyc.com", "delfriscosgrille.com",
    "thecornerstoresoho.com", "gknyc.com", "perrinenyc.com", "brooklyndiner.com",
    "frenchettenyc.com", "stoutnyc.com", "serendipity3.com", "villardnyc.com",
    "oceanarestaurant.com", "philippechow.com", "palmanyc.com", "sundayinbrooklyn.com",
    "junoonnyc.com", "theseafiregrill.com", "frankiesspuntino.com", "loringplacenyc.com",
    "freemansrestaurant.com", "redroosterharlem.com", "rivercafe.com", "rubirosanyc.com",
    "mastrosrestaurants.com", "robertnyc.com", "lecoucou.com", "brunosofbrooklyn.com",
    "casamononyc.com",
    
    # Other
    "berrets.com", "visitwilliamsburg.com", "sohorochesterhills.com", "williamsburgwinery.com",
    "sohohome.com", "pera-soho.com", "norr11.com", "everbody.com", "chambers.nyc",
    "tribecalawsuitloans.com", "tribecaspa.nyc", "beaire.com", "koolinashops.com",
    "williamsburglawgroup.com", "columbiadoctors.org", "grsm.com", "skytalegroup.com",
    "joossefamilyorthodontics.com", "nyc-cpa.com", "thenycalliance.org", "osc.ny.gov"
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
        r"\b(viagra|cialis|levitra|tramadol|sildenafil|tadalafil)\b",
        r"[\u3040-\u30ff\u4e00-\u9faf]"  # Hiragana/Katakana/CJK
    ],
    "high_confidence_spam": [
        # DEFINITE SPAM - 100% confidence (only the most obvious and unambiguous)
        r"\b(viagra|cialis|levitra|tramadol|sildenafil|tadalafil)\b",
        r"\b(casino|poker|slot|betting|gambling|lottery|roulette|blackjack)\b",
        r"\b(porn|sex|adult|xxx|nude|escort|hooker)\b",
        r"\b(forex|binary|trading|investment|loan|credit|make money fast|get rich quick)\b",
        # Only flag obvious spam comments and meta tags
        r"<!--\s*(?:viagra|cialis|casino|porn|forex)\s*-->",
        r'<meta\s+name\s*=\s*["\']keywords["\'][^>]*content\s*=\s*["\'][^"\']*(?:viagra|cialis|casino|porn|forex)[^"\']*["\']'
    ],
    "medium_confidence_spam": [
        # SUSPICIOUS - 60% confidence (reduced from 70%)
        # Made more conservative to reduce false positives
        r"\b(buy\s+now|cheap|discount|offer|limited\s+time|act\s+now|don't\s+miss)\b",
        # Only flag obvious spam links, not legitimate business content
        r"<a[^>]*href\s*=\s*['\"][^'\"]*(?:casino|porn|viagra|cialis)[^'\"]*['\"][^>]*>"
    ],
    "low_confidence_spam": [
        # WEAK INDICATORS - 20% confidence (reduced from 30%)
        r"\b(seo|optimization|ranking)\b.*\b(seo|optimization|ranking)\b",
        r"\b(click here|learn more|read more)\b"
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