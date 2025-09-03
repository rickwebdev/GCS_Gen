#!/usr/bin/env python3
"""
Performance monitoring script for the Lead Finder system.
"""

import os
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
import config


class PerformanceMonitor:
    """Monitor system performance and API usage."""
    
    def __init__(self):
        self.start_time = time.time()
        self.api_calls = {
            'pagespeed': 0,
            'google_cse': 0,
            'crawler': 0
        }
        self.errors = {
            'pagespeed': [],
            'google_cse': [],
            'crawler': []
        }
        self.performance_metrics = {
            'domains_processed': 0,
            'leads_generated': 0,
            'domains_rejected': 0,
            'avg_processing_time': 0
        }
    
    def log_api_call(self, service: str, success: bool = True, error: str = None):
        """Log an API call."""
        self.api_calls[service] += 1
        
        if not success and error:
            self.errors[service].append({
                'timestamp': datetime.now().isoformat(),
                'error': error
            })
    
    def log_performance_metric(self, metric: str, value: Any):
        """Log a performance metric."""
        if metric in self.performance_metrics:
            self.performance_metrics[metric] = value
    
    def get_api_quota_status(self) -> Dict[str, Any]:
        """Check API quota status."""
        status = {}
        
        # Check Google API quota (approximate)
        if os.getenv('GOOGLE_API_KEY'):
            # This is a rough estimate - actual quota checking requires API calls
            status['google_api'] = {
                'quota_remaining': 'Unknown (requires API call)',
                'quota_reset': 'Daily at midnight UTC',
                'recommendation': 'Monitor usage in Google Cloud Console'
            }
        
        return status
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a comprehensive performance summary."""
        runtime = time.time() - self.start_time
        
        summary = {
            'runtime_seconds': runtime,
            'runtime_formatted': str(timedelta(seconds=int(runtime))),
            'api_calls': self.api_calls,
            'errors': self.errors,
            'performance_metrics': self.performance_metrics,
            'efficiency_metrics': self._calculate_efficiency_metrics(runtime),
            'recommendations': self._generate_recommendations()
        }
        
        return summary
    
    def _calculate_efficiency_metrics(self, runtime: float) -> Dict[str, Any]:
        """Calculate efficiency metrics."""
        domains_per_minute = (self.performance_metrics['domains_processed'] / runtime) * 60
        leads_per_minute = (self.performance_metrics['leads_generated'] / runtime) * 60
        success_rate = 0
        
        if self.performance_metrics['domains_processed'] > 0:
            success_rate = (self.performance_metrics['leads_generated'] / 
                          self.performance_metrics['domains_processed']) * 100
        
        return {
            'domains_per_minute': round(domains_per_minute, 2),
            'leads_per_minute': round(leads_per_minute, 2),
            'success_rate_percent': round(success_rate, 1),
            'avg_time_per_domain': round(runtime / max(1, self.performance_metrics['domains_processed']), 2)
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        # Check error rates
        total_errors = sum(len(errors) for errors in self.errors.values())
        if total_errors > 10:
            recommendations.append("High error rate detected. Check API keys and network connectivity.")
        
        # Check API call distribution
        if self.api_calls['pagespeed'] > 100:
            recommendations.append("High PageSpeed API usage. Consider adding more API keys.")
        
        # Check success rate
        if self.performance_metrics['domains_processed'] > 0:
            success_rate = (self.performance_metrics['leads_generated'] / 
                          self.performance_metrics['domains_processed']) * 100
            if success_rate < 30:
                recommendations.append("Low success rate. Review validation criteria and spam detection.")
        
        # Check processing speed
        if self.performance_metrics['domains_processed'] > 0:
            time_per_domain = time.time() - self.start_time / self.performance_metrics['domains_processed']
            if time_per_domain > 60:
                recommendations.append("Slow processing detected. Consider increasing concurrency limits.")
        
        if not recommendations:
            recommendations.append("Performance looks good! No immediate improvements needed.")
        
        return recommendations
    
    def save_report(self, filename: str = None) -> str:
        """Save performance report to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reports/performance_report_{timestamp}.json"
        elif not filename.startswith('reports/'):
            filename = f"reports/{filename}"
        
        # Ensure reports directory exists
        os.makedirs('reports', exist_ok=True)
        
        # Save report
        report = self.get_performance_summary()
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Performance report saved to: {filename}")
        return filename
    
    def print_summary(self):
        """Print a formatted performance summary."""
        summary = self.get_performance_summary()
        
        print("\n" + "="*60)
        print("PERFORMANCE MONITORING SUMMARY")
        print("="*60)
        
        print(f"Runtime: {summary['runtime_formatted']}")
        print(f"Domains Processed: {summary['performance_metrics']['domains_processed']}")
        print(f"Leads Generated: {summary['performance_metrics']['leads_generated']}")
        print(f"Success Rate: {summary['efficiency_metrics']['success_rate_percent']}%")
        
        print(f"\nAPI Calls:")
        for service, count in summary['api_calls'].items():
            print(f"  {service.title()}: {count}")
        
        print(f"\nEfficiency Metrics:")
        print(f"  Domains/minute: {summary['efficiency_metrics']['domains_per_minute']}")
        print(f"  Leads/minute: {summary['efficiency_metrics']['leads_per_minute']}")
        print(f"  Avg time/domain: {summary['efficiency_metrics']['avg_time_per_domain']}s")
        
        if summary['errors']:
            print(f"\nErrors:")
            for service, errors in summary['errors'].items():
                if errors:
                    print(f"  {service.title()}: {len(errors)} errors")
        
        print(f"\nRecommendations:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")
        
        print("="*60)


# Global monitor instance
monitor = PerformanceMonitor()


def get_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return monitor


if __name__ == "__main__":
    # Example usage
    monitor.log_api_call('pagespeed', success=True)
    monitor.log_api_call('google_cse', success=False, error='Rate limit exceeded')
    monitor.log_performance_metric('domains_processed', 50)
    monitor.log_performance_metric('leads_generated', 25)
    
    monitor.print_summary()
    monitor.save_report() 