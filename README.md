# Lead Finder: Broken/Outdated Website Prospects

A powerful, automated system for finding websites that need fixing - whether they're hacked, broken, outdated, slow, or SEO-messy. Perfect for web developers, agencies, and consultants looking for new clients.

## 🎯 What It Finds

### A. Hacked / Compromised Sites
- **Pharma/Japanese keyword spam** in titles/snippets ("viagra", "cialis", "カジノ")
- **Cloaked spam pages** indexed in search results
- **Suspicious paths** like `/wp-content/uploads/.../cache/` with HTML, `/shell.php`
- **Auto-generated landing pages** with casino/essay/forex content
- **Suspicious anchors/footers** with viagra, casino, .ru link farms

### B. Outdated Stack / Visible Errors
- **WordPress version strings** in meta tags, readme.html, feed generators
- **PHP error banners** (Warning:, Deprecated:, Fatal error:)
- **Critical WordPress errors** ("There has been a critical error on this website")
- **Old jQuery versions** (jQuery 1.x) causing console notices
- **Plain HTTP, mixed content, expired TLS**

### C. Performance/UX Issues
- **PageSpeed scores < 50**
- **Core Web Vitals** (LCP > 10s, CLS > 0.25, TTFB > 800ms)
- **Large uncompressed images, render-blocking resources**
- **No image lazy-loading**

### D. SEO Red Flags
- **noindex on main pages**, robots.txt blocking all
- **Missing/empty titles and meta descriptions**
- **Multiple H1s, bad canonicals, 404-heavy navigation**
- **Thin doorway pages**

### E. Site Health Issues
- **Broken navigation** (4xx errors)
- **Missing favicon/logo, placeholder themes**
- **Under-construction pages left live**
- **Contactability gaps** (no phone/address/form)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Google APIs

1. **Get Google API Key:**
   - Go to [Google Cloud Console](https://console.developers.google.com/)
   - Create a new project or select existing
   - Enable "Custom Search API" and "PageSpeed Insights API"
   - Create credentials (API Key)

2. **Create Custom Search Engine:**
   - Go to [Google Programmable Search Engine](https://programmablesearchengine.google.com/)
   - Create a new search engine
   - Get your Search Engine ID

3. **Configure Environment:**
   ```bash
   cp env.example .env
   # Edit .env with your actual API keys
   ```

### 3. Run Lead Finder

```bash
# Find leads with default settings
python cli.py find

# Target specific categories and regions
python cli.py find -c core -c hacked -r us -r ca -m 25

# Export results to CSV
python cli.py export -i leads_20241201_143022.json -f csv
```

## 🎯 SEO Opportunity Mode (NEW!)

**Find high-quality, near-win leads** that are ranking #11-40 in expensive NYC neighborhoods. Perfect for businesses that need SEO help to break into page 1.

### Quick SEO Mode
```bash
# Find restaurant opportunities in SoHo/Tribeca (rank #11-30)
python cli.py find --seo-mode \
  --areas "SoHo,Tribeca" \
  --verticals "restaurant" \
  --rank-window "11-30" \
  --seo-max-pages 4 \
  --dry-run

# Find healthcare leads in Williamsburg (rank #15-35)
python cli.py find --seo-mode \
  --areas "Williamsburg,Park Slope" \
  --verticals "dentist,pilates,interior designer" \
  --rank-window "15-35" \
  --max-leads 20
```

### SEO Mode Features
- **🎯 Rank Targeting**: Only finds sites in your specified SERP range
- **🏙️ Area Focus**: Targets specific NYC neighborhoods
- **🏢 Vertical Targeting**: Focuses on specific business types
- **📊 Extended Pagination**: Searches up to 4 pages (vs. 2 in standard mode)
- **🔍 Smart Filtering**: Excludes aggregators/platforms automatically
- **📈 Opportunity Scoring**: Special scoring for near-win potential
- **💾 Enhanced Export**: Includes rank data, top queries, and SEO scores

### SEO Opportunity Scoring
- **Rank Position**: Lower rank = higher score (closer to page 1)
- **On-Page Issues**: Missing titles, meta descriptions, noindex tags
- **Technical Problems**: Outdated WordPress, accessible readme files
- **Performance**: PageSpeed Insights scores
- **Business Validation**: Contact information, ownership verification

## 📊 Scoring System

### Tier A (80-100): Urgent/Problematic
- **Hacked signals** (30 points)
- **Multiple hacked signals** (+10 points)
- **Outdated WordPress** (+15 points)
- **PHP errors** (+10 points)
- **Poor performance** (+10 points)

### Tier B (60-79): Clear Wins
- **Moderate issues** that need attention
- **Good business potential**

### Tier C (40-59): Mild Issues
- **Minor problems** that can be upsold
- **Lower priority but still valuable**

### Tier D (<40): Ignore
- **Already well-optimized** or **not business sites**

## 🔧 Configuration

### Core Settings (`config.py`)

```python
# Fetch limits
FETCH = {
    "connect": 5,           # seconds
    "read": 10,             # seconds
    "max_bytes": 1_500_000, # 1.5MB
    "per_host_rps": 1,      # requests per second per host
    "global_rps": 5,        # global requests per second
    "max_per_domain": 6     # max requests per domain
}

# PageSpeed Insights thresholds
PSI_THRESH = {
    "perf_bad": 50,         # Performance score threshold
    "lcp_bad": 10_000,      # LCP threshold in ms
    "cls_bad": 0.25,        # CLS threshold
    "ttfb_bad": 800         # TTFB threshold in ms
}
```

### Search Queries

The system comes with **pre-built query sets** for different categories:

- **Core**: General business website discovery
- **Hacked**: Sites with spam/hacking indicators
- **Outdated WP**: Old WordPress installations
- **Performance**: Sites needing speed optimization
- **Local Business**: Restaurants, dentists, contractors
- **Healthcare**: Medical practices, clinics
- **Contractors**: Construction, renovation services

## 📋 CLI Commands

### Find Leads
```bash
# Basic lead generation
python cli.py find

# Target specific categories
python cli.py find -c hacked -c outdated_wp

# Target specific regions
python cli.py find -r us -r ca -r uk

# Limit results
python cli.py find -m 25

# Save with custom filename
python cli.py find -o my_leads.json

# 🆕 SEO Opportunity Mode
python cli.py find --seo-mode \
  --areas "SoHo,Tribeca" \
  --verticals "restaurant" \
  --rank-window "11-30" \
  --seo-max-pages 4 \
  --dry-run
```

### List Available Queries
```bash
# Show all queries
python cli.py list-queries

# Show queries by category
python cli.py show-queries -c hacked
```

### Export Results
```bash
# Export to CSV
python cli.py export -i leads.json -f csv

# Export to JSON
python cli.py export -i leads.json -f json

# Generate summary report
python cli.py export -i leads.json -f summary
```

### Filter and Analyze
```bash
# Filter by tier
python cli.py filter -i leads.json -t A

# Filter by score range
python cli.py filter -i leads.json -s 60 -S 80

# Filter by CMS
python cli.py filter -i leads.json --cms WordPress

# Show only leads with issues
python cli.py filter -i leads.json --has-issues
```

### Configuration
```bash
# Show current configuration
python cli.py config
```

## 🏗️ Architecture

### Core Components

1. **Google CSE Client** (`google_cse.py`)
   - Manages search queries and results
   - Filters out junk URLs
   - Handles rate limiting

2. **Web Crawler** (`crawler.py`)
   - Asynchronous page crawling
   - Extracts technical, security, and SEO information
   - Identifies hacked signals and errors

3. **PageSpeed Insights** (`pagespeed.py`)
   - Performance analysis integration
   - Core Web Vitals extraction
   - Caching for efficiency

4. **Lead Finder** (`lead_finder.py`)
   - Main orchestrator
   - Coordinates all components
   - Manages lead scoring and validation

5. **CLI Interface** (`cli.py`)
   - Command-line interface
   - Export and filtering capabilities
   - User-friendly output

### Data Flow

```
Google CSE → URL Filtering → Domain Probing → Information Extraction → 
Performance Analysis → Scoring → Lead Generation → Export
```

## 📈 Output Schema

Each lead includes:

```json
{
  "domain": "example.com",
  "brand_name": "Example Business",
  "owner_valid": true,
  "platform_subdomain": false,
  "tech": {
    "cms": "WordPress",
    "wp_version": "5.1",
    "jquery_version": "1.12",
    "php_banner": true
  },
  "security": {
    "https": true,
    "mixed_content": false,
    "hsts": false
  },
  "seo": {
    "title_missing": false,
    "meta_desc_missing": true,
    "robots_noindex": true
  },
  "errors": ["PHP error: Warning:", "WordPress critical error"],
  "hacked_signals": ["Spam content: viagra", "Suspicious path: /cache/"],
  "psi": {
    "perf": 34,
    "seo": 78,
    "lcp_ms": 12345,
    "cls": 0.31
  },
  "contact": {
    "phone": "+1-555-0123",
    "email": "info@example.com",
    "form": true
  },
  "score": 85,
  "tier": "A",
  "evidence_urls": ["https://example.com", "https://example.com/about"],
  
  "🆕 SEO Opportunity Mode Fields:": "Only present when using --seo-mode",
  "best_rank": 15,
  "top_query": "SoHo restaurant - \"SoHo\" \"restaurant\" \"contact us\" \"hours\" \"menu\"...",
  "seo_opportunity": 85,
  "rank_queries": ["SoHo restaurant query 1", "SoHo restaurant query 2"]
}
```

## 🎯 Use Cases

### For Web Developers
- **Find new clients** with broken websites
- **Identify urgent issues** that need immediate attention
- **Build case studies** from before/after improvements

### For Agencies
- **Generate qualified leads** for website redesign services
- **Target specific industries** or geographic areas
- **Prioritize prospects** by urgency and potential value

### For Consultants
- **Discover opportunities** in your local market
- **Build prospect lists** for outreach campaigns
- **Analyze competition** and market gaps

### 🆕 For SEO Agencies (SEO Opportunity Mode)
- **Find near-win leads** ranking #11-40 in expensive neighborhoods
- **Target high-value clients** in luxury markets (SoHo, Tribeca, UES)
- **Identify quick wins** for businesses close to page 1
- **Build case studies** from rank improvements
- **Focus on local SEO** opportunities in specific areas

## ⚡ Performance & Rate Limits

- **5 requests/second** globally
- **1 request/second** per host
- **6 requests maximum** per domain
- **10-second timeouts** for page loads
- **1.5MB limit** per page to avoid memory issues

## 🔒 Safety & Ethics

- **Respects robots.txt** for HTML fetches
- **Non-intrusive** - only reads publicly accessible content
- **Rate-limited** to avoid overwhelming servers
- **PageSpeed Insights** uses Google's official API (ignores robots.txt)

## 🚨 Troubleshooting

### Common Issues

1. **"Google API key required"**
   - Check your `.env` file
   - Ensure APIs are enabled in Google Cloud Console

2. **"No results found"**
   - Verify your Custom Search Engine ID
   - Check if search queries are too restrictive

3. **"Rate limit exceeded"**
   - Reduce `max_concurrent` in config
   - Increase delays between requests

4. **"Memory issues"**
   - Reduce `max_bytes` in config
   - Process fewer domains at once

### Debug Mode

```bash
# Run with verbose output
python -u cli.py find -v

# Check configuration
python cli.py config
```

## 📚 Advanced Usage

### Custom Search Queries

```python
from google_cse import QueryManager

qm = QueryManager()
qm.add_custom_query(
    query='("plumber" OR "electrician") "contact us" ("Powered by WordPress" OR inurl:wp-content)',
    description="Local service contractors",
    category="contractors"
)
```

### Batch Processing

```python
from lead_finder import LeadFinder

# Process multiple regions
regions = ['us', 'ca', 'uk', 'au']
for region in regions:
    leads = await finder.find_leads(regions=[region], max_leads=25)
    # Process leads for this region
```

### Custom Scoring

Modify the scoring algorithm in `utils.py`:

```python
def calculate_score(lead_data: dict) -> Tuple[int, str]:
    score = 0
    
    # Your custom scoring logic here
    if lead_data.get('custom_metric'):
        score += 20
    
    return score, determine_tier(score)
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests** if applicable
5. **Submit a pull request**

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for **ethical lead generation only**. Use it to find legitimate business opportunities, not for spam or harassment. Always respect website owners' privacy and terms of service.

---

**Ready to find your next client?** 🚀

```bash
python cli.py find -c hacked -r us -m 25
``` 