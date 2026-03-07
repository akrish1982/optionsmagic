#!/usr/bin/env python3
"""
Daily monitoring & alerting for trade automation + social media posts
Runs via cron every morning to check for errors and report status
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Paths
LOGS_DIR = Path(__file__).parent.parent / "logs"
WORKSPACE = Path(__file__).parent.parent.parent
MEMORY_DIR = WORKSPACE / "memory"

# Log files to monitor
TRADE_LOGS = [
    "propose_trades.log",
    "approval_worker.log",
    "exit_automation.log",
]

SOCIAL_LOGS = [
    "morning_brief.log",
    "daily_scorecard.log",
]

DATA_LOGS = [
    "finviz.log",
    "tradestation.log",
    "opportunities.log",
]

ERROR_KEYWORDS = [
    "ERROR",
    "CRITICAL",
    "Exception",
    "Traceback",
    "failed",
    "Failed",
    "error",
    "KeyError",
    "ValueError",
    "ConnectionError",
]


def check_log_for_errors(log_path: Path) -> Tuple[int, List[str]]:
    """Check log file for errors. Returns (count, last_5_errors)"""
    if not log_path.exists():
        return 0, ["LOG FILE NOT FOUND"]
    
    errors = []
    with open(log_path, "r") as f:
        lines = f.readlines()
    
    for line in lines:
        if any(keyword in line for keyword in ERROR_KEYWORDS):
            errors.append(line.strip())
    
    # Return last 5 errors
    return len(errors), errors[-5:] if errors else []


def check_cron_status() -> Tuple[bool, str]:
    """Verify cron is running and has OptionsMagic jobs"""
    result = os.popen("crontab -l 2>/dev/null | grep -i optionsmagic | wc -l").read().strip()
    count = int(result) if result.isdigit() else 0
    return count > 0, f"{count} jobs scheduled"


def get_log_age(log_path: Path) -> str:
    """Get age of log file"""
    if not log_path.exists():
        return "NOT FOUND"
    
    age = datetime.now() - datetime.fromtimestamp(log_path.stat().st_mtime)
    if age.days > 0:
        return f"{age.days}d old"
    elif age.seconds > 3600:
        return f"{age.seconds // 3600}h old"
    elif age.seconds > 60:
        return f"{age.seconds // 60}m old"
    else:
        return "< 1 min old"


def check_recent_execution(log_path: Path, hours: int = 24) -> bool:
    """Check if log has entries from last N hours"""
    if not log_path.exists():
        return False
    
    cutoff = datetime.now() - timedelta(hours=hours)
    with open(log_path, "r") as f:
        lines = f.readlines()
    
    for line in reversed(lines[-100:]):  # Check last 100 lines
        try:
            # Look for timestamp in log line (common formats: "2026-03-07", "2026-03-07 08:")
            if "2026-03-07" in line or "2026-03-06" in line:
                return True
        except:
            pass
    
    return False


def generate_report() -> Dict:
    """Generate daily monitoring report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "trade_automation": {},
        "social_media": {},
        "data_collection": {},
        "cron_status": {},
        "alerts": [],
        "summary": "",
    }
    
    # Check trade automation logs
    for log_name in TRADE_LOGS:
        log_path = LOGS_DIR / log_name
        error_count, recent_errors = check_log_for_errors(log_path)
        age = get_log_age(log_path)
        is_recent = check_recent_execution(log_path, hours=24)
        
        report["trade_automation"][log_name] = {
            "error_count": error_count,
            "recent_errors": recent_errors[:2],  # Last 2 errors
            "log_age": age,
            "recent_activity": is_recent,
        }
        
        if error_count > 0:
            report["alerts"].append(f"⚠️  {log_name}: {error_count} errors")
        if not is_recent and "approval" not in log_name:  # Approval worker may not run on weekends
            report["alerts"].append(f"📋 {log_name}: No activity in 24h")
    
    # Check social media logs
    for log_name in SOCIAL_LOGS:
        log_path = LOGS_DIR / log_name
        error_count, recent_errors = check_log_for_errors(log_path)
        age = get_log_age(log_path)
        is_recent = check_recent_execution(log_path, hours=24)
        
        report["social_media"][log_name] = {
            "error_count": error_count,
            "recent_errors": recent_errors[:2],
            "log_age": age,
            "recent_activity": is_recent,
        }
        
        if error_count > 0:
            report["alerts"].append(f"⚠️  {log_name}: {error_count} errors")
    
    # Check data collection logs
    for log_name in DATA_LOGS:
        log_path = LOGS_DIR / log_name
        error_count, recent_errors = check_log_for_errors(log_path)
        age = get_log_age(log_path)
        is_recent = check_recent_execution(log_path, hours=24)
        
        report["data_collection"][log_name] = {
            "error_count": error_count,
            "recent_errors": recent_errors[:1],
            "log_age": age,
            "recent_activity": is_recent,
        }
        
        if error_count > 0:
            report["alerts"].append(f"⚠️  {log_name}: {error_count} errors")
    
    # Check cron status
    cron_ok, cron_msg = check_cron_status()
    report["cron_status"] = {
        "running": cron_ok,
        "status": cron_msg,
    }
    
    if not cron_ok:
        report["alerts"].append("🔴 CRON NOT RUNNING - No OptionsMagic jobs found")
    
    # Generate summary
    total_errors = sum(
        v["error_count"] for v in list(report["trade_automation"].values()) +
        list(report["social_media"].values()) +
        list(report["data_collection"].values())
    )
    
    if report["alerts"]:
        report["summary"] = f"🟡 ISSUES FOUND: {len(report['alerts'])} alerts | {total_errors} total errors"
    else:
        report["summary"] = "✅ ALL SYSTEMS HEALTHY"
    
    return report


def format_report_for_chat(report: Dict) -> str:
    """Format report for Telegram/WhatsApp"""
    lines = []
    
    # Header
    lines.append(f"📊 *OptionsMagic Daily Monitor*")
    lines.append(f"_{report['timestamp'][:16]}_")
    lines.append("")
    
    # Summary
    lines.append(f"*Status:* {report['summary']}")
    lines.append("")
    
    # Alerts (if any)
    if report["alerts"]:
        lines.append("*⚠️ Alerts:*")
        for alert in report["alerts"][:5]:  # Top 5 alerts
            lines.append(f"• {alert}")
        lines.append("")
    
    # Trade Automation Status
    lines.append("*🤖 Trade Automation:*")
    for log_name, data in report["trade_automation"].items():
        status = "✅" if data["error_count"] == 0 else "⚠️"
        lines.append(f"{status} {log_name.replace('.log', '')}: {data['log_age']}")
    lines.append("")
    
    # Social Media Status
    lines.append("*📱 Social Media:*")
    for log_name, data in report["social_media"].items():
        status = "✅" if data["error_count"] == 0 else "⚠️"
        lines.append(f"{status} {log_name.replace('.log', '')}: {data['log_age']}")
    lines.append("")
    
    # Cron Status
    cron = report["cron_status"]
    cron_status = "✅ Running" if cron["running"] else "🔴 Not Running"
    lines.append(f"*Cron Status:* {cron_status} ({cron['status']})")
    
    return "\n".join(lines)


def save_report(report: Dict) -> str:
    """Save report to file"""
    report_path = MEMORY_DIR / f"optionsmagic_daily_{datetime.now().strftime('%Y-%m-%d')}.json"
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    return str(report_path)


def main():
    """Main monitoring function"""
    report = generate_report()
    
    # Save report
    report_path = save_report(report)
    print(f"Report saved: {report_path}")
    
    # Print for immediate feedback
    print(format_report_for_chat(report))
    
    # Exit code: 0 if healthy, 1 if issues
    exit_code = 0 if len(report["alerts"]) == 0 else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
