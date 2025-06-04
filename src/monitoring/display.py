"""
Display Formatting for AQEA Distributed Extractor Status

Formats status information into human-readable tables and displays.
"""

import time
from typing import Dict, Any, List
from datetime import datetime, timedelta


def format_status_table(status_data: Dict[str, Any]) -> str:
    """Format comprehensive status data into a readable table."""
    
    lines = []
    
    # Header
    lines.append("🎯 AQEA Distributed Extractor Status")
    lines.append("=" * 60)
    
    # Overview section
    overview = status_data.get('overview', {})
    lines.append(f"📋 Project: {overview.get('language', 'Unknown')} from {overview.get('source', 'Unknown')}")
    lines.append(f"⏱️  Runtime: {overview.get('runtime_hours', 0):.1f} hours")
    lines.append(f"🎲 Status: {overview.get('status', 'Unknown').title()}")
    
    if overview.get('started_at'):
        try:
            start_time = datetime.fromisoformat(overview['started_at'].replace('Z', '+00:00'))
            lines.append(f"🚀 Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            lines.append(f"🚀 Started: {overview.get('started_at')}")
    
    lines.append("")
    
    # Progress section
    progress = status_data.get('progress', {})
    progress_percent = progress.get('progress_percent', 0)
    processed = progress.get('total_processed_entries', 0)
    estimated = progress.get('total_estimated_entries', 0)
    current_rate = progress.get('current_rate_per_minute', 0)
    eta_hours = progress.get('eta_hours')
    
    lines.append("📈 Progress")
    lines.append("-" * 20)
    
    # Progress bar
    progress_bar = create_progress_bar(progress_percent, width=40)
    lines.append(f"Progress: {progress_bar} {progress_percent:.1f}%")
    lines.append(f"Entries:  {processed:,} / {estimated:,}")
    lines.append(f"Rate:     {current_rate:.1f} entries/min")
    
    if eta_hours:
        if eta_hours < 1:
            eta_str = f"{eta_hours * 60:.0f} minutes"
        elif eta_hours < 24:
            eta_str = f"{eta_hours:.1f} hours"
        else:
            eta_str = f"{eta_hours / 24:.1f} days"
        lines.append(f"ETA:      {eta_str}")
    
    lines.append("")
    
    # Workers section
    workers_data = status_data.get('workers', {})
    lines.append("👥 Workers")
    lines.append("-" * 20)
    lines.append(f"Total:    {workers_data.get('total', 0)}")
    lines.append(f"Active:   {workers_data.get('active', 0)}")
    lines.append(f"Idle:     {workers_data.get('idle', 0)}")
    lines.append(f"Expected: {workers_data.get('expected', 0)}")
    
    # Worker details
    worker_details = workers_data.get('details', [])
    if worker_details:
        lines.append("")
        lines.append("🔧 Worker Details")
        lines.append("-" * 20)
        lines.append(format_worker_details(worker_details))
    
    lines.append("")
    
    # Work units section
    work_units = status_data.get('work_units', {})
    lines.append("📦 Work Units")
    lines.append("-" * 20)
    lines.append(f"Total:      {work_units.get('total', 0)}")
    lines.append(f"Completed:  {work_units.get('completed', 0)}")
    lines.append(f"Processing: {work_units.get('processing', 0)}")
    lines.append(f"Pending:    {work_units.get('pending', 0)}")
    lines.append(f"Failed:     {work_units.get('failed', 0)}")
    
    # Recent completions
    recent_completions = status_data.get('recent_completions', [])
    if recent_completions:
        lines.append("")
        lines.append("🎉 Recent Completions")
        lines.append("-" * 20)
        for completion in recent_completions[-3:]:  # Show last 3
            work_id = completion.get('id', 'Unknown')
            entries = completion.get('entries_processed', 0)
            worker = completion.get('worker_id', 'Unknown')
            lines.append(f"  {work_id}: {entries:,} entries by {worker}")
    
    return "\n".join(lines)


def format_worker_details(workers: List[Dict[str, Any]]) -> str:
    """Format worker details into a table."""
    if not workers:
        return "No workers available"
    
    lines = []
    
    # Table header
    header = f"{'Worker ID':<12} {'Status':<10} {'Rate/min':<10} {'Total':<8} {'Last Seen':<12}"
    lines.append(header)
    lines.append("-" * len(header))
    
    # Worker rows
    for worker in workers:
        worker_id = worker.get('worker_id', 'Unknown')[:11]
        status = worker.get('status', 'Unknown')[:9]
        rate = worker.get('average_rate', 0)
        total = worker.get('total_processed', 0)
        
        # Format last heartbeat
        last_heartbeat = worker.get('last_heartbeat')
        if last_heartbeat:
            try:
                heartbeat_time = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                now = datetime.now(heartbeat_time.tzinfo) if heartbeat_time.tzinfo else datetime.now()
                delta = now - heartbeat_time
                
                if delta.total_seconds() < 60:
                    last_seen = "now"
                elif delta.total_seconds() < 3600:
                    last_seen = f"{int(delta.total_seconds() / 60)}m ago"
                else:
                    last_seen = f"{int(delta.total_seconds() / 3600)}h ago"
            except:
                last_seen = "unknown"
        else:
            last_seen = "never"
        
        # Status indicator
        status_indicator = get_status_indicator(status)
        
        line = f"{worker_id:<12} {status_indicator}{status:<9} {rate:<10.1f} {total:<8,} {last_seen:<12}"
        lines.append(line)
    
    return "\n".join(lines)


def create_progress_bar(percentage: float, width: int = 30) -> str:
    """Create a visual progress bar."""
    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}]"


def get_status_indicator(status: str) -> str:
    """Get status indicator emoji."""
    status_indicators = {
        'working': '🟢 ',
        'idle': '⚪ ',
        'error': '🔴 ',
        'offline': '⚫ '
    }
    return status_indicators.get(status.lower(), '❓ ')


def format_performance_summary(metrics: Dict[str, Any]) -> str:
    """Format performance metrics summary."""
    lines = []
    
    lines.append("⚡ Performance Summary")
    lines.append("=" * 30)
    
    total_rate = metrics.get('total_processing_rate', 0)
    worker_count = metrics.get('active_worker_count', 0)
    completion_rate = metrics.get('work_unit_completion_rate', 0)
    health = metrics.get('system_health', 'unknown')
    
    lines.append(f"System Health:     {health.title()}")
    lines.append(f"Total Rate:        {total_rate:.1f} entries/min")
    lines.append(f"Active Workers:    {worker_count}")
    lines.append(f"Completion Rate:   {completion_rate:.1f}%")
    
    if worker_count > 0:
        avg_rate = total_rate / worker_count
        lines.append(f"Avg Rate/Worker:   {avg_rate:.1f} entries/min")
    
    # Worker efficiency details
    worker_efficiency = metrics.get('worker_efficiency', [])
    if worker_efficiency:
        lines.append("")
        lines.append("Worker Efficiency:")
        lines.append("-" * 20)
        
        for worker in sorted(worker_efficiency, key=lambda x: x.get('total_processed', 0), reverse=True):
            worker_id = worker.get('worker_id', 'Unknown')[:10]
            total = worker.get('total_processed', 0)
            rate = worker.get('average_rate', 0)
            lines.append(f"{worker_id}: {total:,} entries ({rate:.1f}/min)")
    
    return "\n".join(lines)


def format_cost_analysis(estimation_result) -> str:
    """Format cost analysis from estimation result."""
    lines = []
    
    lines.append("💰 Cost Analysis")
    lines.append("=" * 25)
    
    lines.append(f"Language:      {estimation_result.language.title()}")
    lines.append(f"Servers:       {estimation_result.servers}")
    lines.append(f"Entries:       {estimation_result.estimated_entries:,}")
    lines.append(f"Processing:    {estimation_result.processing_time_hours:.1f} hours")
    lines.append(f"Total Cost:    {estimation_result.cost_currency} {estimation_result.cost_total:.2f}")
    lines.append(f"Speedup:       {estimation_result.speedup_factor:.1f}x")
    
    # Efficiency metrics
    metrics = estimation_result.efficiency_metrics
    lines.append("")
    lines.append("Efficiency Metrics:")
    lines.append("-" * 20)
    lines.append(f"Cost/Entry:    {estimation_result.cost_currency} {metrics.get('cost_per_entry', 0):.6f}")
    lines.append(f"Parallel Eff:  {metrics.get('parallel_efficiency_percent', 0):.1f}%")
    lines.append(f"ROI Factor:    {metrics.get('roi_factor', 0):.1f}x")
    
    return "\n".join(lines)


def format_live_dashboard(status_data: Dict[str, Any], width: int = 80) -> str:
    """Format a live dashboard view."""
    lines = []
    
    # Header with timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"AQEA Live Dashboard - {now}"
    lines.append(header.center(width))
    lines.append("=" * width)
    
    # Quick stats in columns
    overview = status_data.get('overview', {})
    progress = status_data.get('progress', {})
    workers = status_data.get('workers', {})
    
    # First row: Progress and Workers
    progress_percent = progress.get('progress_percent', 0)
    current_rate = progress.get('current_rate_per_minute', 0)
    active_workers = workers.get('active', 0)
    total_workers = workers.get('total', 0)
    
    col1 = f"Progress: {progress_percent:.1f}%"
    col2 = f"Rate: {current_rate:.1f}/min"
    col3 = f"Workers: {active_workers}/{total_workers}"
    
    spacing = (width - len(col1) - len(col2) - len(col3)) // 2
    quick_stats = f"{col1}{' ' * spacing}{col2}{' ' * spacing}{col3}"
    lines.append(quick_stats)
    
    # Progress bar
    progress_bar = create_progress_bar(progress_percent, width - 20)
    lines.append(f"Progress: {progress_bar}")
    
    lines.append("")
    
    # ETA and runtime
    runtime = overview.get('runtime_hours', 0)
    eta_hours = progress.get('eta_hours')
    
    runtime_str = f"Runtime: {runtime:.1f}h"
    if eta_hours:
        eta_str = f"ETA: {eta_hours:.1f}h"
    else:
        eta_str = "ETA: calculating..."
    
    lines.append(f"{runtime_str:<40}{eta_str:>39}")
    
    # Entries processed
    processed = progress.get('total_processed_entries', 0)
    estimated = progress.get('total_estimated_entries', 0)
    
    entries_str = f"Entries: {processed:,} / {estimated:,}"
    lines.append(entries_str.center(width))
    
    lines.append("")
    
    # Worker status summary
    worker_details = workers.get('details', [])
    if worker_details:
        working_workers = [w for w in worker_details if w.get('status') == 'working']
        if working_workers:
            lines.append("Active Workers:")
            for worker in working_workers[:5]:  # Show top 5
                worker_id = worker.get('worker_id', 'Unknown')[:10]
                rate = worker.get('average_rate', 0)
                lines.append(f"  {worker_id}: {rate:.1f} entries/min")
    
    return "\n".join(lines)


def format_extraction_summary(final_status: Dict[str, Any]) -> str:
    """Format final extraction summary."""
    lines = []
    
    lines.append("🎉 Extraction Complete!")
    lines.append("=" * 40)
    
    overview = final_status.get('overview', {})
    progress = final_status.get('progress', {})
    workers = final_status.get('workers', {})
    
    # Summary statistics
    total_processed = progress.get('total_processed_entries', 0)
    runtime_hours = overview.get('runtime_hours', 0)
    avg_rate = total_processed / (runtime_hours * 60) if runtime_hours > 0 else 0
    
    lines.append(f"Language:         {overview.get('language', 'Unknown').title()}")
    lines.append(f"Source:           {overview.get('source', 'Unknown').title()}")
    lines.append(f"Total Entries:    {total_processed:,}")
    lines.append(f"Runtime:          {runtime_hours:.1f} hours")
    lines.append(f"Average Rate:     {avg_rate:.1f} entries/min")
    lines.append(f"Workers Used:     {workers.get('total', 0)}")
    
    # Performance summary
    lines.append("")
    lines.append("Performance Summary:")
    lines.append("-" * 20)
    
    if runtime_hours > 0:
        entries_per_hour = total_processed / runtime_hours
        lines.append(f"Entries/Hour:     {entries_per_hour:,.0f}")
    
    # Work unit summary
    work_units = final_status.get('work_units', {})
    completed_units = work_units.get('completed', 0)
    failed_units = work_units.get('failed', 0)
    success_rate = (completed_units / (completed_units + failed_units)) * 100 if (completed_units + failed_units) > 0 else 0
    
    lines.append(f"Success Rate:     {success_rate:.1f}%")
    lines.append(f"Work Units:       {completed_units} completed, {failed_units} failed")
    
    return "\n".join(lines) 