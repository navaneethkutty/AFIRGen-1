#!/usr/bin/env python3
"""
Bug Triage and Tracking System for Bedrock Migration

Manages bug discovery, prioritization, and tracking during E2E testing.

Priority Levels:
- P0 (Critical): System crashes, data loss, security vulnerabilities
- P1 (High): Major functionality broken, performance degradation >50%
- P2 (Medium): Minor functionality issues, performance degradation <50%
- P3 (Low): Cosmetic issues, minor improvements

Status:
- Open: Bug discovered, not yet assigned
- In Progress: Bug being investigated/fixed
- Fixed: Fix implemented, awaiting verification
- Verified: Fix verified in staging
- Closed: Fix deployed to production
- Deferred: Documented for future sprint
"""

import json
import time
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


class Priority(Enum):
    """Bug priority levels"""
    P0 = "Critical"
    P1 = "High"
    P2 = "Medium"
    P3 = "Low"


class Status(Enum):
    """Bug status"""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    FIXED = "Fixed"
    VERIFIED = "Verified"
    CLOSED = "Closed"
    DEFERRED = "Deferred"


@dataclass
class Bug:
    """Bug report"""
    id: str
    title: str
    description: str
    priority: str
    status: str
    component: str  # e.g., "Transcribe", "Bedrock", "Vector DB"
    discovered_date: str
    discovered_by: str
    assigned_to: str = None
    fixed_date: str = None
    verified_date: str = None
    regression_test: str = None  # Path to regression test
    notes: List[str] = None
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []


@dataclass
class BugReport:
    """Complete bug triage report"""
    timestamp: str
    total_bugs: int
    p0_bugs: List[Bug]
    p1_bugs: List[Bug]
    p2_bugs: List[Bug]
    p3_bugs: List[Bug]
    open_critical: int  # P0 + P1
    fixed_critical: int
    verified_critical: int
    deferred_bugs: int
    summary: Dict[str, Any]


class BugTracker:
    """Bug tracking and triage system"""
    
    def __init__(self, bugs_file: str = "bugs.json"):
        self.bugs_file = Path(bugs_file)
        self.bugs: List[Bug] = []
        self.load_bugs()
    
    def load_bugs(self):
        """Load bugs from JSON file"""
        if self.bugs_file.exists():
            with open(self.bugs_file, 'r') as f:
                data = json.load(f)
                self.bugs = [Bug(**bug) for bug in data]
    
    def save_bugs(self):
        """Save bugs to JSON file"""
        with open(self.bugs_file, 'w') as f:
            json.dump([asdict(bug) for bug in self.bugs], f, indent=2)
    
    def add_bug(self, title: str, description: str, priority: Priority,
                component: str, discovered_by: str) -> Bug:
        """Add new bug"""
        bug_id = f"BUG-{len(self.bugs) + 1:04d}"
        
        bug = Bug(
            id=bug_id,
            title=title,
            description=description,
            priority=priority.value,
            status=Status.OPEN.value,
            component=component,
            discovered_date=time.strftime("%Y-%m-%d %H:%M:%S"),
            discovered_by=discovered_by
        )
        
        self.bugs.append(bug)
        self.save_bugs()
        
        print(f"Created bug: {bug_id} - {title} [{priority.value}]")
        return bug
    
    def update_bug(self, bug_id: str, **kwargs):
        """Update bug fields"""
        bug = self.get_bug(bug_id)
        if not bug:
            print(f"Bug {bug_id} not found")
            return
        
        for key, value in kwargs.items():
            if hasattr(bug, key):
                setattr(bug, key, value)
        
        self.save_bugs()
        print(f"Updated bug: {bug_id}")
    
    def get_bug(self, bug_id: str) -> Bug:
        """Get bug by ID"""
        for bug in self.bugs:
            if bug.id == bug_id:
                return bug
        return None
    
    def assign_bug(self, bug_id: str, assignee: str):
        """Assign bug to developer"""
        self.update_bug(bug_id, assigned_to=assignee, status=Status.IN_PROGRESS.value)
    
    def mark_fixed(self, bug_id: str, regression_test: str = None):
        """Mark bug as fixed"""
        updates = {
            "status": Status.FIXED.value,
            "fixed_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        if regression_test:
            updates["regression_test"] = regression_test
        
        self.update_bug(bug_id, **updates)
    
    def mark_verified(self, bug_id: str):
        """Mark bug as verified"""
        self.update_bug(
            bug_id,
            status=Status.VERIFIED.value,
            verified_date=time.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def mark_deferred(self, bug_id: str, reason: str):
        """Mark bug as deferred"""
        bug = self.get_bug(bug_id)
        if bug:
            bug.notes.append(f"Deferred: {reason}")
            self.update_bug(bug_id, status=Status.DEFERRED.value)
    
    def add_note(self, bug_id: str, note: str):
        """Add note to bug"""
        bug = self.get_bug(bug_id)
        if bug:
            bug.notes.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {note}")
            self.save_bugs()
    
    def get_bugs_by_priority(self, priority: Priority) -> List[Bug]:
        """Get all bugs of specific priority"""
        return [bug for bug in self.bugs if bug.priority == priority.value]
    
    def get_bugs_by_status(self, status: Status) -> List[Bug]:
        """Get all bugs with specific status"""
        return [bug for bug in self.bugs if bug.status == status.value]
    
    def get_critical_bugs(self) -> List[Bug]:
        """Get all P0 and P1 bugs"""
        return [bug for bug in self.bugs if bug.priority in [Priority.P0.value, Priority.P1.value]]
    
    def generate_report(self) -> BugReport:
        """Generate bug triage report"""
        p0_bugs = self.get_bugs_by_priority(Priority.P0)
        p1_bugs = self.get_bugs_by_priority(Priority.P1)
        p2_bugs = self.get_bugs_by_priority(Priority.P2)
        p3_bugs = self.get_bugs_by_priority(Priority.P3)
        
        critical_bugs = p0_bugs + p1_bugs
        open_critical = sum(1 for bug in critical_bugs if bug.status == Status.OPEN.value)
        fixed_critical = sum(1 for bug in critical_bugs if bug.status == Status.FIXED.value)
        verified_critical = sum(1 for bug in critical_bugs if bug.status == Status.VERIFIED.value)
        deferred_bugs = len(self.get_bugs_by_status(Status.DEFERRED))
        
        summary = {
            "total_bugs": len(self.bugs),
            "by_priority": {
                "P0": len(p0_bugs),
                "P1": len(p1_bugs),
                "P2": len(p2_bugs),
                "P3": len(p3_bugs)
            },
            "by_status": {
                "Open": len(self.get_bugs_by_status(Status.OPEN)),
                "In Progress": len(self.get_bugs_by_status(Status.IN_PROGRESS)),
                "Fixed": len(self.get_bugs_by_status(Status.FIXED)),
                "Verified": len(self.get_bugs_by_status(Status.VERIFIED)),
                "Closed": len(self.get_bugs_by_status(Status.CLOSED)),
                "Deferred": deferred_bugs
            },
            "critical_bugs": {
                "total": len(critical_bugs),
                "open": open_critical,
                "fixed": fixed_critical,
                "verified": verified_critical
            }
        }
        
        report = BugReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            total_bugs=len(self.bugs),
            p0_bugs=p0_bugs,
            p1_bugs=p1_bugs,
            p2_bugs=p2_bugs,
            p3_bugs=p3_bugs,
            open_critical=open_critical,
            fixed_critical=fixed_critical,
            verified_critical=verified_critical,
            deferred_bugs=deferred_bugs,
            summary=summary
        )
        
        return report
    
    def print_report(self, report: BugReport):
        """Print bug triage report"""
        print()
        print("=" * 60)
        print("BUG TRIAGE REPORT")
        print("=" * 60)
        print(f"Timestamp: {report.timestamp}")
        print()
        
        print("Summary:")
        print("-" * 60)
        print(f"Total Bugs:         {report.total_bugs}")
        print()
        print("By Priority:")
        for priority, count in report.summary["by_priority"].items():
            print(f"  {priority}:              {count}")
        print()
        print("By Status:")
        for status, count in report.summary["by_status"].items():
            print(f"  {status:15} {count}")
        print()
        print("Critical Bugs (P0 + P1):")
        print(f"  Total:          {report.summary['critical_bugs']['total']}")
        print(f"  Open:           {report.open_critical}")
        print(f"  Fixed:          {report.fixed_critical}")
        print(f"  Verified:       {report.verified_critical}")
        print()
        
        # Print P0 bugs
        if report.p0_bugs:
            print("P0 (Critical) Bugs:")
            print("-" * 60)
            for bug in report.p0_bugs:
                status_icon = "✓" if bug.status in [Status.VERIFIED.value, Status.CLOSED.value] else "✗"
                print(f"{status_icon} {bug.id}: {bug.title}")
                print(f"   Status: {bug.status} | Component: {bug.component}")
                print(f"   {bug.description[:100]}...")
                if bug.regression_test:
                    print(f"   Regression Test: {bug.regression_test}")
                print()
        
        # Print P1 bugs
        if report.p1_bugs:
            print("P1 (High) Bugs:")
            print("-" * 60)
            for bug in report.p1_bugs:
                status_icon = "✓" if bug.status in [Status.VERIFIED.value, Status.CLOSED.value] else "✗"
                print(f"{status_icon} {bug.id}: {bug.title}")
                print(f"   Status: {bug.status} | Component: {bug.component}")
                print(f"   {bug.description[:100]}...")
                if bug.regression_test:
                    print(f"   Regression Test: {bug.regression_test}")
                print()
        
        # Print deferred bugs
        if report.deferred_bugs > 0:
            print(f"Deferred Bugs: {report.deferred_bugs}")
            print("-" * 60)
            deferred = self.get_bugs_by_status(Status.DEFERRED)
            for bug in deferred:
                print(f"  {bug.id}: {bug.title} [{bug.priority}]")
            print()
        
        print("=" * 60)
        if report.open_critical == 0:
            print("✓ All critical bugs (P0/P1) are fixed and verified")
        else:
            print(f"✗ {report.open_critical} critical bugs still open")
        print("=" * 60)
    
    def save_report(self, report: BugReport, output_path: str = "bug_triage_report.json"):
        """Save report to JSON file"""
        report_dict = {
            "timestamp": report.timestamp,
            "total_bugs": report.total_bugs,
            "p0_bugs": [asdict(bug) for bug in report.p0_bugs],
            "p1_bugs": [asdict(bug) for bug in report.p1_bugs],
            "p2_bugs": [asdict(bug) for bug in report.p2_bugs],
            "p3_bugs": [asdict(bug) for bug in report.p3_bugs],
            "open_critical": report.open_critical,
            "fixed_critical": report.fixed_critical,
            "verified_critical": report.verified_critical,
            "deferred_bugs": report.deferred_bugs,
            "summary": report.summary
        }
        
        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Bug triage and tracking system")
    parser.add_argument("--bugs-file", default="bugs.json", help="Bugs database file")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add bug command
    add_parser = subparsers.add_parser("add", help="Add new bug")
    add_parser.add_argument("--title", required=True, help="Bug title")
    add_parser.add_argument("--description", required=True, help="Bug description")
    add_parser.add_argument("--priority", required=True, choices=["P0", "P1", "P2", "P3"],
                           help="Bug priority")
    add_parser.add_argument("--component", required=True, help="Component name")
    add_parser.add_argument("--discovered-by", required=True, help="Discoverer name")
    
    # Update bug command
    update_parser = subparsers.add_parser("update", help="Update bug")
    update_parser.add_argument("--id", required=True, help="Bug ID")
    update_parser.add_argument("--status", choices=["Open", "In Progress", "Fixed", "Verified", "Closed", "Deferred"],
                              help="New status")
    update_parser.add_argument("--assigned-to", help="Assignee name")
    update_parser.add_argument("--regression-test", help="Path to regression test")
    
    # Report command
    subparsers.add_parser("report", help="Generate bug report")
    
    args = parser.parse_args()
    
    tracker = BugTracker(args.bugs_file)
    
    if args.command == "add":
        priority = Priority[args.priority]
        tracker.add_bug(
            title=args.title,
            description=args.description,
            priority=priority,
            component=args.component,
            discovered_by=args.discovered_by
        )
    
    elif args.command == "update":
        updates = {}
        if args.status:
            updates["status"] = args.status
        if args.assigned_to:
            updates["assigned_to"] = args.assigned_to
        if args.regression_test:
            updates["regression_test"] = args.regression_test
        
        tracker.update_bug(args.id, **updates)
    
    elif args.command == "report":
        report = tracker.generate_report()
        tracker.print_report(report)
        tracker.save_report(report)
        
        # Exit with error if critical bugs are open
        sys.exit(0 if report.open_critical == 0 else 1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
