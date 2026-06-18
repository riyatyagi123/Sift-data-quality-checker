import json
import logging

logger = logging.getLogger(__name__)

def generate_validation_summary(results: dict) -> str:
    """Formats validation results into a human-readable text report."""
    summary = []
    summary.append("="*40)
    summary.append("SIFT DATA VALIDATOR - QUALITY REPORT")
    summary.append("="*40)
    summary.append(f"Total Records: {results.get('total_records')}")
    summary.append(f"Valid Records: {results.get('valid_records')}")
    summary.append(f"Invalid Records: {results.get('invalid_records')}")
    summary.append(f"Success Rate: {results.get('success_rate')}%")
    summary.append("-"*40)
    
    rule_status = results.get('rule_status', {})
    affected = results.get('affected_rows', {})
    for check, status in rule_status.items():
        summary.append(f"{check.upper()} Check: {status} ({affected.get(check, 0)} affected rows)")
        
    summary.append("="*40)
    return "\n".join(summary)
