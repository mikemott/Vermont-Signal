#!/usr/bin/env python3
"""
Check API costs and send alerts if thresholds exceeded

Usage:
    python scripts/check_budget.py

Exit codes:
    0 - Budget OK
    1 - Warning threshold exceeded
    2 - Critical threshold exceeded
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vermont_news_analyzer.modules.database import VermontSignalDatabase
from vermont_news_analyzer.config import CostConfig

# Budget thresholds from centralized config
DAILY_BUDGET = CostConfig.DAILY_BUDGET_CAP
MONTHLY_BUDGET = CostConfig.MONTHLY_BUDGET_CAP

# Alert thresholds
WARNING_THRESHOLD = 0.80  # 80%
CRITICAL_THRESHOLD = 0.90  # 90%


def get_costs(db):
    """Get daily and monthly costs from database"""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Today's cost
            cur.execute("""
                SELECT COALESCE(SUM(cost), 0) as total
                FROM api_costs
                WHERE DATE(timestamp) = CURRENT_DATE
            """)
            daily_cost = float(cur.fetchone()[0])

            # This month's cost
            cur.execute("""
                SELECT COALESCE(SUM(cost), 0) as total
                FROM api_costs
                WHERE DATE_TRUNC('month', timestamp) = DATE_TRUNC('month', CURRENT_DATE)
            """)
            monthly_cost = float(cur.fetchone()[0])

            # Get cost by provider (for details)
            cur.execute("""
                SELECT api_provider, SUM(cost) as total
                FROM api_costs
                WHERE DATE_TRUNC('month', timestamp) = DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY api_provider
                ORDER BY total DESC
            """)
            provider_costs = {row[0]: float(row[1]) for row in cur.fetchall()}

    return daily_cost, monthly_cost, provider_costs


def check_budgets():
    """Check budgets and return alert level"""
    try:
        db = VermontSignalDatabase()
        db.connect()

        daily_cost, monthly_cost, provider_costs = get_costs(db)

        db.disconnect()

    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return 2

    # Calculate percentages
    daily_pct = (daily_cost / DAILY_BUDGET) * 100 if DAILY_BUDGET > 0 else 0
    monthly_pct = (monthly_cost / MONTHLY_BUDGET) * 100 if MONTHLY_BUDGET > 0 else 0

    # Determine alert level
    alert_level = 0  # OK
    alerts = []

    # Check daily budget
    if daily_cost >= DAILY_BUDGET:
        alerts.append(f"🚨 DAILY BUDGET EXCEEDED: ${daily_cost:.2f} / ${DAILY_BUDGET:.2f} ({daily_pct:.1f}%)")
        alert_level = max(alert_level, 2)
    elif daily_cost >= DAILY_BUDGET * CRITICAL_THRESHOLD:
        alerts.append(f"🔴 Daily budget critical (>90%): ${daily_cost:.2f} / ${DAILY_BUDGET:.2f} ({daily_pct:.1f}%)")
        alert_level = max(alert_level, 2)
    elif daily_cost >= DAILY_BUDGET * WARNING_THRESHOLD:
        alerts.append(f"⚠️  Daily budget warning (>80%): ${daily_cost:.2f} / ${DAILY_BUDGET:.2f} ({daily_pct:.1f}%)")
        alert_level = max(alert_level, 1)

    # Check monthly budget
    if monthly_cost >= MONTHLY_BUDGET:
        alerts.append(f"🚨 MONTHLY BUDGET EXCEEDED: ${monthly_cost:.2f} / ${MONTHLY_BUDGET:.2f} ({monthly_pct:.1f}%)")
        alert_level = max(alert_level, 2)
    elif monthly_cost >= MONTHLY_BUDGET * CRITICAL_THRESHOLD:
        alerts.append(f"🔴 Monthly budget critical (>90%): ${monthly_cost:.2f} / ${MONTHLY_BUDGET:.2f} ({monthly_pct:.1f}%)")
        alert_level = max(alert_level, 2)
    elif monthly_cost >= MONTHLY_BUDGET * WARNING_THRESHOLD:
        alerts.append(f"⚠️  Monthly budget warning (>80%): ${monthly_cost:.2f} / ${MONTHLY_BUDGET:.2f} ({monthly_pct:.1f}%)")
        alert_level = max(alert_level, 1)

    # Output results
    if alerts:
        print("=" * 60)
        print("BUDGET ALERT")
        print("=" * 60)
        for alert in alerts:
            print(alert)
        print("")
        print("Cost Breakdown by Provider:")
        for provider, cost in provider_costs.items():
            pct = (cost / monthly_cost * 100) if monthly_cost > 0 else 0
            print(f"  {provider}: ${cost:.2f} ({pct:.1f}%)")
        print("=" * 60)
    else:
        print(f"✅ Budget OK")
        print(f"   Daily: ${daily_cost:.2f} / ${DAILY_BUDGET:.2f} ({daily_pct:.1f}%)")
        print(f"   Monthly: ${monthly_cost:.2f} / ${MONTHLY_BUDGET:.2f} ({monthly_pct:.1f}%)")
        if provider_costs:
            print(f"   Top provider: {max(provider_costs, key=provider_costs.get)} (${provider_costs[max(provider_costs, key=provider_costs.get)]:.2f})")

    return alert_level


if __name__ == "__main__":
    exit_code = check_budgets()
    sys.exit(exit_code)
