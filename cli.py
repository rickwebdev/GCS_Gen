"""
Command-line interface for the Lead Finder system.
"""

import asyncio
import click
import json
from typing import List, Optional
from lead_finder import LeadFinder
from google_cse import QueryManager
import os
from datetime import datetime
import csv


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Lead Finder - Find broken/outdated websites that need fixing."""
    pass


@cli.command()
@click.option('--categories', '-c', multiple=True, 
              help='Query categories to use (core, hacked, outdated_wp, seo, performance, local_business, contractors, healthcare)')
@click.option('--regions', '-r', multiple=True, 
              help='Geographic regions to target (us, ca, uk, au, de, fr, etc.)')
@click.option('--max-leads', '-m', default=50, 
              help='Maximum number of leads to generate (default: 50)')
@click.option('--output', '-o', default=None, 
              help='Output filename for leads (default: auto-generated)')
@click.option('--save-rejected', is_flag=True, 
              help='Save rejected domains to a separate file')
@click.option('--seo-mode', is_flag=True, 
              help='Enable SEO Opportunity Mode for near-win leads (rank #11-40)')
@click.option('--areas', default='SoHo,Tribeca,UES,UWS,DUMBO,Brooklyn Heights,Williamsburg,Park Slope,Fort Greene', 
              help='Comma-separated list of NYC areas to target in SEO mode')
@click.option('--verticals', default='restaurant,dentist,pilates,interior designer,boutique hotel,florist,gallery', 
              help='Comma-separated list of business verticals to target in SEO mode')
@click.option('--rank-window', default='11-40', 
              help='SERP rank window for SEO mode (format: min-max, default: 11-40)')
@click.option('--seo-max-pages', default=4, 
              help='Maximum pages to search in SEO mode (default: 4)')
@click.option('--dry-run', is_flag=True, 
              help='Dry run mode - no file writes, stdout only')
def find(categories, regions, max_leads, output, save_rejected, seo_mode, areas, verticals, rank_window, seo_max_pages, dry_run):
    """Find leads using the Lead Finder system."""
    
    if not categories:
        categories = ['core', 'hacked', 'outdated_wp']
    
    if not regions:
        regions = ['us', 'ca', 'uk']
    
    # Parse SEO mode parameters
    if seo_mode:
        areas_list = [area.strip() for area in areas.split(',')]
        verticals_list = [vertical.strip() for vertical in verticals.split(',')]
        rank_min, rank_max = map(int, rank_window.split('-'))
        
        click.echo(f"🚀 Starting Lead Finder in SEO OPPORTUNITY MODE...")
        click.echo(f"🎯 Areas: {', '.join(areas_list)}")
        click.echo(f"🏢 Verticals: {', '.join(verticals_list)}")
        click.echo(f"📊 Rank Window: #{rank_min}-#{rank_max}")
        click.echo(f"📄 SEO Max Pages: {seo_max_pages}")
        click.echo(f"🔍 Dry Run: {'Yes' if dry_run else 'No'}")
    else:
        click.echo(f"Starting Lead Finder...")
        click.echo(f"Categories: {', '.join(categories)}")
        click.echo(f"Regions: {', '.join(regions)}")
        click.echo(f"Target leads: {max_leads}")
    
    async def run_finder():
        # API credentials should be set via environment variables or .env file
        # Check if credentials are available
        if not os.environ.get('GOOGLE_API_KEY') or not os.environ.get('GOOGLE_CSE_ID'):
            click.echo("❌ Error: GOOGLE_API_KEY and GOOGLE_CSE_ID must be set in environment variables or .env file")
            click.echo("💡 Create a .env file with your credentials:")
            click.echo("   GOOGLE_API_KEY=your_api_key_here")
            click.echo("   GOOGLE_CSE_ID=your_cse_id_here")
            raise click.Abort()
        
        finder = LeadFinder()
        
        try:
            if seo_mode:
                # SEO Opportunity Mode
                leads = await finder.find_seo_opportunities(
                    areas=areas_list,
                    verticals=verticals_list,
                    rank_min=rank_min,
                    rank_max=rank_max,
                    max_pages=seo_max_pages,
                    max_leads=max_leads
                )
            else:
                # Standard mode
                leads = await finder.find_leads(
                    categories=list(categories),
                    regions=list(regions),
                    max_leads=max_leads
                )
            
            if dry_run:
                # Dry run mode - just show results
                click.echo(f"\n🔍 DRY RUN COMPLETE - No files saved")
                click.echo(f"📊 Found {len(leads)} qualified leads")
                
                if leads:
                    click.echo("\n🏆 TOP 10 SEO OPPORTUNITY LEADS:")
                    click.echo("=" * 80)
                    click.echo(f"{'Domain':<30} {'Best Rank':<10} {'SEO Score':<10} {'Top Query':<20} {'Key Issues'}")
                    click.echo("-" * 80)
                    
                    for i, lead in enumerate(leads[:10], 1):
                        best_rank = getattr(lead, 'best_rank', 'N/A')
                        seo_opportunity = getattr(lead, 'seo_opportunity', 'N/A')
                        top_query = getattr(lead, 'top_query', 'N/A')[:18] + '...' if getattr(lead, 'top_query', 'N/A') else 'N/A'
                        key_issues = ', '.join(lead.hacked_signals[:2] + lead.errors[:1])[:30] + '...' if (lead.hacked_signals or lead.errors) else 'No issues'
                        
                        click.echo(f"{lead.domain:<30} {str(best_rank):<10} {str(seo_opportunity):<10} {top_query:<20} {key_issues}")
            else:
                # Normal mode - save files
                if output:
                    filename = finder.save_leads(output)
                else:
                    filename = finder.save_leads()
                
                click.echo(f"\n✅ Lead generation complete!")
                click.echo(f"📊 Found {len(leads)} qualified leads")
                click.echo(f"💾 Saved to: {filename}")
                
                # Save rejected domains if requested
                if save_rejected:
                    rejected_file = finder.save_rejected_domains()
                    click.echo(f"❌ Rejected domains saved to: {rejected_file}")
            
            # Show top leads
            if leads:
                click.echo("\n🏆 Top 5 leads:")
                for i, lead in enumerate(leads[:5]):
                    click.echo(f"  {i+1}. {lead.domain} - Score: {lead.score}, Tier: {lead.tier}")
                    if lead.brand_name:
                        click.echo(f"     Brand: {lead.brand_name}")
                    if lead.hacked_signals:
                        click.echo(f"     Issues: {', '.join(lead.hacked_signals[:2])}")
            
        except Exception as e:
            click.echo(f"❌ Error: {e}", err=True)
            raise click.Abort()
    
    asyncio.run(run_finder())


@cli.command()
def list_queries():
    """List all available search queries."""
    query_manager = QueryManager()
    queries = query_manager.get_all_queries()
    
    click.echo("Available search queries:\n")
    
    # Group by category
    categories = {}
    for query in queries:
        cat = query.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(query)
    
    for category, cat_queries in categories.items():
        click.echo(f"📁 {category.upper().replace('_', ' ')}:")
        for query in cat_queries:
            click.echo(f"  • {query.description}")
            click.echo(f"    Query: {query.query[:80]}...")
            click.echo()
    
    click.echo(f"Total queries: {len(queries)}")


@cli.command()
@click.option('--category', '-c', help='Filter by category')
def show_queries(category):
    """Show detailed information about search queries."""
    query_manager = QueryManager()
    
    if category:
        queries = query_manager.get_queries_by_category(category)
        if not queries:
            click.echo(f"No queries found for category: {category}")
            return
    else:
        queries = query_manager.get_all_queries()
    
    click.echo(f"Showing {len(queries)} queries:\n")
    
    for i, query in enumerate(queries, 1):
        click.echo(f"{i}. {query.description}")
        click.echo(f"   Category: {query.category}")
        click.echo(f"   Query: {query.query}")
        click.echo()


@cli.command()
@click.option('--input', '-i', required=True, help='Input leads JSON file')
@click.option('--output', '-o', help='Output CSV file (default: auto-generated)')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'summary']), 
              default='csv', help='Output format')
def export(input, output, format):
    """Export leads to different formats."""
    try:
        with open(input, 'r') as f:
            leads_data = json.load(f)
        
        if format == 'csv':
            export_to_csv(leads_data, output)
        elif format == 'json':
            export_to_json(leads_data, output)
        elif format == 'summary':
            export_summary(leads_data, output)
            
    except FileNotFoundError:
        click.echo(f"❌ File not found: {input}", err=True)
        raise click.Abort()
    except json.JSONDecodeError:
        click.echo(f"❌ Invalid JSON file: {input}", err=True)
        raise click.Abort()


def export_to_csv(leads, filename=None):
    """Export leads to CSV with enhanced PSI metrics and vertical categorization."""
    if not leads:
        print("No leads to export")
        return
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/leads_export_{timestamp}.csv"
    
    # Ensure reports directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Prepare data for CSV
    csv_data = []
    all_fieldnames = set([
        'domain', 'brand_name', 'vertical_tag', 'score', 'tier', 'phone', 'email', 'address',
        'cms', 'wp_version', 'performance_score', 'ttfb_ms', 'lcp_ms', 'cls', 'psi_status',
        'spam_confidence', 'performance_override', 'override_reason', 'technical_issues', 'seo_issues', 'pitch_hook'
    ])
    
    for lead in leads:
        # Handle both Lead objects and dictionaries
        if hasattr(lead, 'domain'):
            # Lead object
            row = {
                'domain': lead.domain,
                'brand_name': lead.brand_name or '',
                'vertical_tag': getattr(lead, 'vertical_tag', 'unknown'),
                'score': lead.score,
                'tier': lead.tier,
                'phone': lead.contact.phone if lead.contact and lead.contact.phone else '',
                'email': lead.contact.email if lead.contact and lead.contact.email else '',
                'address': lead.contact.address if lead.contact and lead.contact.address else '',
                'cms': lead.tech.cms if lead.tech and lead.tech.cms else '',
                'wp_version': lead.tech.wp_version if lead.tech and lead.tech.wp_version else '',
                'performance_score': lead.psi.perf if lead.psi and lead.psi.perf else '',
                'ttfb_ms': lead.psi.ttfb_ms if lead.psi and lead.psi.ttfb_ms else '',
                'lcp_ms': lead.psi.lcp_ms if lead.psi and lead.psi.lcp_ms else '',
                'cls': lead.psi.cls if lead.psi and lead.psi.cls else '',
                'psi_status': 'success' if lead.psi and lead.psi.perf else 'failed',
                'spam_confidence': getattr(lead, 'spam_confidence', ''),
                'performance_override': 'yes' if getattr(lead, 'performance_override_reason', None) else 'no',
                'override_reason': getattr(lead, 'performance_override_reason', ''),
                'technical_issues': len(lead.errors) if lead.errors else 0,
                'seo_issues': sum([
                    1 if lead.seo.title_missing else 0,
                    1 if lead.seo.meta_desc_missing else 0,
                    1 if lead.seo.robots_noindex else 0
                ]),
                'pitch_hook': generate_pitch_hook(lead)
            }
            
            # Flatten meta fields for CSV
            meta = getattr(lead, 'meta', {}) or {}
            for k, v in meta.items():
                meta_key = f'meta_{k}'
                row[meta_key] = v
                all_fieldnames.add(meta_key)
        else:
            # Dictionary
            row = {
                'domain': lead.get('domain', ''),
                'brand_name': lead.get('brand_name', ''),
                'vertical_tag': lead.get('vertical_tag', 'unknown'),
                'score': lead.get('score', 0),
                'tier': lead.get('tier', ''),
                'phone': lead.get('contact', {}).get('phone', '') if lead.get('contact') else '',
                'email': lead.get('contact', {}).get('email', '') if lead.get('contact') else '',
                'address': lead.get('contact', {}).get('address', '') if lead.get('contact') else '',
                'cms': lead.get('tech', {}).get('cms', '') if lead.get('tech') else '',
                'wp_version': lead.get('tech', {}).get('wp_version', '') if lead.get('tech') else '',
                'performance_score': lead.get('psi', {}).get('perf', '') if lead.get('psi') else '',
                'ttfb_ms': lead.get('psi', {}).get('ttfb_ms', '') if lead.get('psi') else '',
                'lcp_ms': lead.get('psi', {}).get('lcp_ms', '') if lead.get('psi') else '',
                'cls': lead.get('psi', {}).get('cls', '') if lead.get('psi') else '',
                'psi_status': 'success' if lead.get('psi', {}).get('perf') else 'failed',
                'spam_confidence': lead.get('spam_confidence', ''),
                'performance_override': 'yes' if lead.get('performance_override_reason') else 'no',
                'override_reason': lead.get('performance_override_reason', ''),
                'technical_issues': len(lead.get('errors', [])),
                'seo_issues': sum([
                    1 if lead.get('seo', {}).get('title_missing') else 0,
                    1 if lead.get('seo', {}).get('meta_desc_missing') else 0,
                    1 if lead.get('seo', {}).get('robots_noindex') else 0
                ]),
                'pitch_hook': generate_pitch_hook(lead)
            }
            
            # Flatten meta fields for CSV
            meta = lead.get('meta', {}) or {}
            for k, v in meta.items():
                meta_key = f'meta_{k}'
                row[meta_key] = v
                all_fieldnames.add(meta_key)
        
        csv_data.append(row)
    
    # Write to CSV
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = sorted(list(all_fieldnames))
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"✅ Exported {len(leads)} leads to CSV: {filename}")
    return filename

def export_dual_csv(leads, base_filename=None):
    """Export leads to two separate CSV files: primary (NYC + perf <= 60) and review (everything else)."""
    if not leads:
        print("No leads to export")
        return
    
    if base_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"reports/leads_{timestamp}"
    
    # Ensure reports directory exists
    os.makedirs(os.path.dirname(base_filename), exist_ok=True)
    
    # Separate leads into primary and review
    primary_leads = []
    review_leads = []
    
    for lead in leads:
        # Handle both Lead objects and dictionaries
        if hasattr(lead, 'domain'):
            # Lead object
            perf_score = lead.psi.perf if lead.psi and lead.psi.perf else 100
            is_nyc = any(neighborhood in (lead.brand_name or '').lower() for neighborhood in 
                        ['tribeca', 'soho', 'upper east side', 'west village', 'williamsburg', 'nyc', 'new york'])
            has_performance_override = getattr(lead, 'performance_override_reason', None) is not None
        else:
            # Dictionary
            perf_score = lead.get('psi', {}).get('perf', 100) if lead.get('psi') else 100
            brand_name = lead.get('brand_name', '').lower()
            is_nyc = any(neighborhood in brand_name for neighborhood in 
                        ['tribeca', 'soho', 'upper east side', 'west village', 'williamsburg', 'nyc', 'new york'])
            has_performance_override = lead.get('performance_override_reason') is not None
        
        # Primary leads: NYC + performance_score <= 60 OR any performance override
        if (is_nyc and perf_score <= 60) or has_performance_override:
            primary_leads.append(lead)
        else:
            review_leads.append(lead)
    
    # Export primary leads
    primary_filename = f"{base_filename}_primary.csv"
    if primary_leads:
        export_to_csv(primary_leads, primary_filename)
        print(f"🎯 Primary leads (NYC + perf <= 60): {len(primary_leads)}")
    else:
        print("⚠️  No primary leads found")
    
    # Export review leads
    review_filename = f"{base_filename}_review.csv"
    if review_leads:
        export_to_csv(review_leads, review_filename)
        print(f"📋 Review leads (everything else): {len(review_leads)}")
    else:
        print("⚠️  No review leads found")
    
    return primary_filename, review_filename

def generate_pitch_hook(lead):
    """Generate a pitch hook for quick actionability."""
    try:
        if hasattr(lead, 'psi') and lead.psi and lead.psi.perf:
            perf_score = lead.psi.perf
            if perf_score <= 45:
                return f"🚨 CRITICAL: Perf {perf_score}/100 - Complete overhaul needed!"
            elif perf_score <= 60:
                return f"🐌 Poor: Perf {perf_score}/100 - Speed optimization opportunity"
            elif perf_score <= 80:
                return f"⚠️  Moderate: Perf {perf_score}/100 - Room for improvement"
            else:
                return f"✅ Good: Perf {perf_score}/100 - Minor optimizations"
        else:
            return "No performance data"
    except:
        return "Error generating pitch hook"


def export_to_json(leads_data, output):
    """Export leads to JSON format."""
    if not output:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"reports/leads_export_{timestamp}.json"
    elif not output.startswith('reports/'):
        output = f"reports/{output}"
    
    with open(output, 'w') as f:
        json.dump(leads_data, f, indent=2, default=str)
    
    click.echo(f"✅ Exported {len(leads_data)} leads to JSON: {output}")


def export_summary(leads_data, output):
    """Export leads summary."""
    if not output:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"reports/leads_summary_{timestamp}.txt"
    elif not output.startswith('reports/'):
        output = f"reports/{output}"
    
    # Calculate statistics
    total_leads = len(leads_data)
    tier_counts = {}
    score_ranges = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}
    
    for lead in leads_data:
        tier = lead.get('tier', 'D')
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        score = lead.get('score', 0)
        if score <= 20:
            score_ranges['0-20'] += 1
        elif score <= 40:
            score_ranges['21-40'] += 1
        elif score <= 60:
            score_ranges['41-60'] += 1
        elif score <= 80:
            score_ranges['61-80'] += 1
        else:
            score_ranges['81-100'] += 1
    
    with open(output, 'w') as f:
        f.write("LEAD FINDER SUMMARY REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total leads: {total_leads}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("LEADS BY TIER:\n")
        f.write("-" * 20 + "\n")
        for tier in sorted(tier_counts.keys()):
            f.write(f"Tier {tier}: {tier_counts[tier]} ({tier_counts[tier]/total_leads*100:.1f}%)\n")
        
        f.write("\nLEADS BY SCORE RANGE:\n")
        f.write("-" * 25 + "\n")
        for range_name, count in score_ranges.items():
            f.write(f"{range_name}: {count} ({count/total_leads*100:.1f}%)\n")
        
        f.write("\nTOP 10 LEADS:\n")
        f.write("-" * 15 + "\n")
        sorted_leads = sorted(leads_data, key=lambda x: x.get('score', 0), reverse=True)
        for i, lead in enumerate(sorted_leads[:10], 1):
            f.write(f"{i}. {lead.get('domain', 'N/A')} - Score: {lead.get('score', 0)}, Tier: {lead.get('tier', 'N/A')}\n")
            if lead.get('brand_name'):
                f.write(f"   Brand: {lead['brand_name']}\n")
            if lead.get('hacked_signals'):
                f.write(f"   Issues: {', '.join(lead['hacked_signals'][:3])}\n")
            f.write("\n")
    
    click.echo(f"✅ Exported summary to: {output}")


@cli.command()
@click.option('--input', '-i', required=True, help='Input leads JSON file')
@click.option('--tier', '-t', help='Filter by tier (A, B, C, D)')
@click.option('--min-score', '-s', type=int, help='Minimum score filter')
@click.option('--max-score', '-S', type=int, help='Maximum score filter')
@click.option('--cms', help='Filter by CMS (e.g., WordPress)')
@click.option('--has-issues', is_flag=True, help='Only show leads with issues')
def filter(input, tier, min_score, max_score, cms, has_issues):
    """Filter and display leads."""
    try:
        with open(input, 'r') as f:
            leads_data = json.load(f)
        
        # Apply filters
        filtered_leads = leads_data
        
        if tier:
            filtered_leads = [l for l in filtered_leads if l.get('tier') == tier.upper()]
        
        if min_score is not None:
            filtered_leads = [l for l in filtered_leads if l.get('score', 0) >= min_score]
        
        if max_score is not None:
            filtered_leads = [l for l in filtered_leads if l.get('score', 0) <= max_score]
        
        if cms:
            filtered_leads = [l for l in filtered_leads if l.get('tech', {}).get('cms') == cms]
        
        if has_issues:
            filtered_leads = [l for l in filtered_leads if (
                l.get('hacked_signals') or 
                l.get('errors') or 
                l.get('seo', {}).get('title_missing') or
                l.get('seo', {}).get('meta_desc_missing')
            )]
        
        click.echo(f"Found {len(filtered_leads)} leads matching filters:\n")
        
        for i, lead in enumerate(filtered_leads, 1):
            click.echo(f"{i}. {lead.get('domain', 'N/A')}")
            click.echo(f"   Score: {lead.get('score', 0)}, Tier: {lead.get('tier', 'N/A')}")
            if lead.get('brand_name'):
                click.echo(f"   Brand: {lead['brand_name']}")
            if lead.get('hacked_signals'):
                click.echo(f"   Issues: {', '.join(lead['hacked_signals'][:3])}")
            click.echo()
            
    except FileNotFoundError:
        click.echo(f"❌ File not found: {input}", err=True)
        raise click.Abort()
    except json.JSONDecodeError:
        click.echo(f"❌ Invalid JSON file: {input}", err=True)
        raise click.Abort()


@cli.command()
def config():
    """Show current configuration."""
    import config
    
    click.echo("LEAD FINDER CONFIGURATION\n")
    click.echo("=" * 40 + "\n")
    
    click.echo("FETCH SETTINGS:")
    for key, value in config.FETCH.items():
        click.echo(f"  {key}: {value}")
    
    click.echo("\nPSI THRESHOLDS:")
    for key, value in config.PSI_THRESH.items():
        click.echo(f"  {key}: {value}")
    
    click.echo(f"\nSCORE MINIMUM: {config.SCORE_MIN}")
    click.echo(f"TIER A MINIMUM: {config.TIER_A_MIN}")
    click.echo(f"TIER B MINIMUM: {config.TIER_B_MIN}")
    
    click.echo(f"\nEXCLUDED HOSTS: {len(config.EXCLUDES_HOST)}")
    click.echo(f"EXCLUDED TLDs: {len(config.EXCLUDES_TLD)}")
    click.echo(f"EXCLUDED EXTENSIONS: {len(config.EXCLUDES_EXT)}")


if __name__ == '__main__':
    cli() 