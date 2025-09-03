#!/usr/bin/env python3
"""
Demo script showing how to use the Lead Finder system programmatically.
"""

import asyncio
import json
from datetime import datetime
from lead_finder import LeadFinder
from google_cse import QueryManager


async def demo_basic_usage():
    """Demonstrate basic usage of the Lead Finder."""
    print("🚀 Lead Finder Demo - Basic Usage")
    print("=" * 50)
    
    # Create Lead Finder instance
    finder = LeadFinder()
    
    # Find leads with specific parameters
    print("Finding leads...")
    leads = await finder.find_leads(
        categories=['core', 'hacked'],  # Focus on core and hacked sites
        regions=['us'],                  # Target US market
        max_leads=5                      # Limit to 5 leads for demo
    )
    
    print(f"\n✅ Found {len(leads)} leads!")
    
    # Display results
    for i, lead in enumerate(leads, 1):
        print(f"\n{i}. {lead.domain}")
        print(f"   Brand: {lead.brand_name or 'Unknown'}")
        print(f"   Score: {lead.score}/100 (Tier {lead.tier})")
        print(f"   Owner Valid: {lead.owner_valid}")
        
        if lead.hacked_signals:
            print(f"   Issues: {', '.join(lead.hacked_signals[:2])}")
        
        if lead.tech.cms:
            print(f"   CMS: {lead.tech.cms}")
            if lead.tech.wp_version:
                print(f"   WordPress: {lead.tech.wp_version}")
    
    return leads


async def demo_query_management():
    """Demonstrate query management capabilities."""
    print("\n\n🔍 Query Management Demo")
    print("=" * 50)
    
    # Create query manager
    qm = QueryManager()
    
    # Show available queries
    all_queries = qm.get_all_queries()
    print(f"Total queries available: {len(all_queries)}")
    
    # Group by category
    categories = {}
    for query in all_queries:
        cat = query.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(query)
    
    print("\nQueries by category:")
    for category, queries in categories.items():
        print(f"  {category}: {len(queries)} queries")
    
    # Show some specific queries
    print("\nSample queries:")
    for category in ['hacked', 'outdated_wp']:
        queries = qm.get_queries_by_category(category)
        if queries:
            query = queries[0]
            print(f"  {category}: {query.description}")
            print(f"    Query: {query.query[:80]}...")
    
    # Add a custom query
    print("\nAdding custom query...")
    qm.add_custom_query(
        query='("local business" OR "small business") "contact us" ("Powered by WordPress" OR inurl:wp-content) -site:yelp.*',
        description="Local small businesses with WordPress",
        category="local_business"
    )
    
    custom_queries = qm.get_queries_by_category('local_business')
    print(f"Custom queries added: {len(custom_queries)}")


async def demo_lead_analysis():
    """Demonstrate lead analysis capabilities."""
    print("\n\n📊 Lead Analysis Demo")
    print("=" * 50)
    
    # Create a sample lead (simulating what would be found)
    sample_lead_data = {
        'domain': 'demo-example.com',
        'brand_name': 'Demo Business',
        'owner_valid': True,
        'platform_subdomain': False,
        'tech': {
            'cms': 'WordPress',
            'wp_version': '5.0',
            'jquery_version': '1.12',
            'php_banner': True,
            'readme_accessible': True
        },
        'security': {
            'https': False,
            'mixed_content': True,
            'hsts': False
        },
        'seo': {
            'title_missing': False,
            'meta_desc_missing': True,
            'robots_noindex': False,
            'canonical': False
        },
        'errors': [
            'PHP error: Warning:',
            'WordPress critical error: There has been a critical error on this website'
        ],
        'hacked_signals': [
            'Spam content: viagra',
            'Suspicious path: /cache/'
        ],
        'contact': {
            'phone': '+1-555-0123',
            'email': 'info@demo-example.com',
            'form': True
        },
        'evidence_urls': [
            'http://demo-example.com',
            'http://demo-example.com/about'
        ]
    }
    
    # Create Lead object
    from models import Lead
    lead = Lead(**sample_lead_data)
    
    # Analyze the lead
    print(f"Domain: {lead.domain}")
    print(f"Brand: {lead.brand_name}")
    print(f"Owner Valid: {lead.owner_valid}")
    print(f"Platform Subdomain: {lead.platform_subdomain}")
    
    print(f"\nTechnical Issues:")
    print(f"  CMS: {lead.tech.cms}")
    print(f"  WordPress Version: {lead.tech.wp_version}")
    print(f"  jQuery Version: {lead.tech.jquery_version}")
    print(f"  PHP Errors: {lead.tech.php_banner}")
    print(f"  Readme Accessible: {lead.tech.readme_accessible}")
    
    print(f"\nSecurity Issues:")
    print(f"  HTTPS: {lead.security.https}")
    print(f"  Mixed Content: {lead.security.mixed_content}")
    print(f"  HSTS: {lead.security.hsts}")
    
    print(f"\nSEO Issues:")
    print(f"  Title Missing: {lead.seo.title_missing}")
    print(f"  Meta Description Missing: {lead.seo.meta_desc_missing}")
    print(f"  Robots Noindex: {lead.seo.robots_noindex}")
    print(f"  Canonical: {lead.seo.canonical}")
    
    print(f"\nErrors Found:")
    for error in lead.errors:
        print(f"  - {error}")
    
    print(f"\nHacked Signals:")
    for signal in lead.hacked_signals:
        print(f"  - {signal}")
    
    print(f"\nContact Information:")
    print(f"  Phone: {lead.contact.phone}")
    print(f"  Email: {lead.contact.email}")
    print(f"  Form: {lead.contact.form}")
    
    print(f"\nEvidence URLs:")
    for url in lead.evidence_urls:
        print(f"  - {url}")


async def demo_export_functionality():
    """Demonstrate export and filtering capabilities."""
    print("\n\n💾 Export Functionality Demo")
    print("=" * 50)
    
    # Create sample leads for export demo
    sample_leads = []
    
    for i in range(3):
        lead_data = {
            'domain': f'demo{i+1}-example.com',
            'brand_name': f'Demo Business {i+1}',
            'owner_valid': True,
            'platform_subdomain': False,
            'tech': {
                'cms': 'WordPress',
                'wp_version': f'5.{i}',
                'jquery_version': f'1.{10+i}',
                'php_banner': i % 2 == 0,
                'readme_accessible': i % 2 == 1
            },
            'security': {
                'https': i % 2 == 0,
                'mixed_content': i % 2 == 1,
                'hsts': False
            },
            'seo': {
                'title_missing': i % 2 == 1,
                'meta_desc_missing': i % 2 == 0,
                'robots_noindex': False,
                'canonical': i % 2 == 0
            },
            'errors': [f'Error {i+1}'] if i % 2 == 0 else [],
            'hacked_signals': [f'Signal {i+1}'] if i % 2 == 1 else [],
            'contact': {
                'phone': f'+1-555-{1000+i:04d}',
                'email': f'info@demo{i+1}-example.com',
                'form': True
            },
            'evidence_urls': [f'http://demo{i+1}-example.com'],
            'score': 60 + (i * 10),
            'tier': ['C', 'B', 'A'][i]
        }
        
        from models import Lead
        lead = Lead(**lead_data)
        sample_leads.append(lead)
    
    # Save leads to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"demo_leads_{timestamp}.json"
    
    with open(filename, 'w') as f:
        leads_data = [lead.dict() for lead in sample_leads]
        json.dump(leads_data, f, indent=2, default=str)
    
    print(f"✅ Saved {len(sample_leads)} demo leads to {filename}")
    
    # Demonstrate filtering
    print(f"\nFiltering leads by tier...")
    tier_a_leads = [lead for lead in sample_leads if lead.tier == 'A']
    tier_b_leads = [lead for lead in sample_leads if lead.tier == 'B']
    tier_c_leads = [lead for lead in sample_leads if lead.tier == 'C']
    
    print(f"  Tier A: {len(tier_a_leads)} leads")
    print(f"  Tier B: {len(tier_b_leads)} leads")
    print(f"  Tier C: {len(tier_c_leads)} leads")
    
    # Show high-scoring leads
    high_score_leads = [lead for lead in sample_leads if lead.score >= 70]
    print(f"\nHigh-scoring leads (≥70): {len(high_score_leads)}")
    
    for lead in high_score_leads:
        print(f"  {lead.domain}: {lead.score}/100 (Tier {lead.tier})")
    
    return filename


async def main():
    """Run all demos."""
    print("🎯 Lead Finder System Demo")
    print("=" * 60)
    print("This demo shows the key capabilities of the Lead Finder system.")
    print("Note: Some features require Google API keys to work fully.")
    print()
    
    try:
        # Run demos
        await demo_query_management()
        await demo_lead_analysis()
        await demo_export_functionality()
        
        # Note about full functionality
        print("\n" + "=" * 60)
        print("📝 Demo Complete!")
        print("=" * 60)
        print("To use the full system:")
        print("1. Set up Google API keys (see README.md)")
        print("2. Run: python cli.py find")
        print("3. Or use programmatically: python demo.py")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("This is likely due to missing API keys or configuration.")
        print("Check the README.md for setup instructions.")


if __name__ == "__main__":
    asyncio.run(main()) 