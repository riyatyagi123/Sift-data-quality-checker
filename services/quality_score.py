def get_issue_severity(rule_type: str) -> str:
    """Maps validation rule violations to their respective severity levels."""
    severities = {
        'mandatory': 'CRITICAL',
        'duplicates': 'ERROR',
        'phone': 'ERROR',
        'email': 'ERROR',
        'date': 'ERROR',
        'numeric': 'ERROR',
        'negative_amount': 'ERROR',
        'currency': 'WARNING',
        'payment_mode': 'WARNING',
        'unknown_country': 'WARNING',
        'date_before_2000': 'WARNING',
        'future_date': 'INFO'
    }
    return severities.get(rule_type, 'ERROR')

def classify_quality_rating(score: float) -> str:
    """Categorizes the quality score into standard qualitative tiers."""
    if score >= 95.0:
        return "Excellent"
    elif score >= 85.0:
        return "Good"
    elif score >= 70.0:
        return "Average"
    else:
        return "Poor"

def calculate_overall_score(completeness: float, validity: float, uniqueness: float) -> float:
    """Calculates the weighted overall quality score (30/50/20)."""
    score = 0.3 * completeness + 0.5 * validity + 0.2 * uniqueness
    return round(score, 1)
