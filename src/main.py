#!/usr/bin/env python3
"""
AQEA Distributed Extractor - Main Entry Point

Handles CLI commands and orchestrates the distributed extraction system.
"""

import asyncio
import click
import logging
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from .coordinator.master import MasterCoordinator
from .workers.worker import ExtractionWorker
from .utils.config import Config
from .utils.logger import setup_logging


@click.group()
@click.option('--config', '-c', default='config/default.yml', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, verbose):
    """AQEA Distributed Extractor - Extract language data at scale"""
    ctx.ensure_object(dict)
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    # Load configuration
    ctx.obj['config'] = Config.load(config)
    ctx.obj['verbose'] = verbose


@cli.command()
@click.option('--language', '-l', required=True, help='Language to extract (de, en, fr, es)')
@click.option('--workers', '-w', default=5, help='Number of worker instances')
@click.option('--source', '-s', default='wiktionary', help='Data source (wiktionary, panlex, wikidata)')
@click.option('--port', '-p', default=8080, help='Master coordinator port')
@click.option('--work-units-file', help='JSON file with predefined work units')
@click.option('--config-file', help='Alternative config file (JSON)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging (DEBUG level)')
@click.pass_context
def start_master(ctx, language, workers, source, port, work_units_file, config_file, verbose):
    """Start the master coordinator server"""
    if config_file:
        # Lade benutzerdefinierte Konfiguration
        import json
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
        config = Config(config_dict)
    else:
        config = ctx.obj['config']
    
    # Setup logging mit übergebenem verbose Flag
    verbose = verbose or ctx.obj.get('verbose', False)
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    click.echo(f"🎯 Starting AQEA Distributed Extractor - Master Mode")
    click.echo(f"   Language: {language}")
    click.echo(f"   Workers: {workers}")
    click.echo(f"   Source: {source}")
    click.echo(f"   Port: {port}")
    click.echo(f"   Verbose: {verbose}")
    
    if work_units_file:
        click.echo(f"   Work Units: {work_units_file}")
    
    coordinator = MasterCoordinator(
        config=config,
        language=language,
        source=source,
        expected_workers=workers,
        port=port,
        work_units_file=work_units_file
    )
    
    try:
        asyncio.run(coordinator.run())
    except KeyboardInterrupt:
        click.echo("\n🛑 Master coordinator stopped")


@cli.command()
@click.option('--worker-id', '-i', required=True, help='Unique worker identifier')
@click.option('--master-host', '-m', required=True, help='Master coordinator host/IP')
@click.option('--master-port', '-p', default=8080, help='Master coordinator port')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging (DEBUG level)')
@click.pass_context
def start_worker(ctx, worker_id, master_host, master_port, verbose):
    """Start a worker extraction process"""
    config = ctx.obj['config']
    
    # Setup logging mit übergebenem verbose Flag
    verbose = verbose or ctx.obj.get('verbose', False)
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    click.echo(f"🔧 Starting AQEA Extraction Worker")
    click.echo(f"   Worker ID: {worker_id}")
    click.echo(f"   Master: {master_host}:{master_port}")
    click.echo(f"   Verbose: {verbose}")
    
    worker = ExtractionWorker(
        config=config,
        worker_id=worker_id,
        master_host=master_host,
        master_port=master_port
    )
    
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        click.echo(f"\n🛑 Worker {worker_id} stopped")


@cli.command()
@click.option('--master-host', '-m', default='localhost', help='Master coordinator host/IP')
@click.option('--master-port', '-p', default=8080, help='Master coordinator port')
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table', help='Output format')
@click.pass_context
def status(ctx, master_host, master_port, format):
    """Show extraction status"""
    from .monitoring.client import StatusClient
    
    client = StatusClient(master_host, master_port)
    
    try:
        status_data = asyncio.run(client.get_status())
        
        if format == 'json':
            import json
            click.echo(json.dumps(status_data, indent=2))
        else:
            # Pretty table format
            from .monitoring.display import format_status_table
            click.echo(format_status_table(status_data))
            
    except Exception as e:
        click.echo(f"❌ Failed to get status: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--language', '-l', required=True, help='Language to analyze')
@click.option('--servers', '-s', default=5, help='Number of servers')
@click.option('--hours', '-h', default=24, help='Extraction time in hours')
@click.pass_context
def estimate(ctx, language, servers, hours):
    """Estimate costs and performance for extraction"""
    from .utils.estimator import CostEstimator
    
    config = ctx.obj['config']
    estimator = CostEstimator(config)
    
    estimate_data = estimator.calculate(
        language=language,
        servers=servers,
        hours=hours
    )
    
    click.echo(f"\n📊 Extraction Estimate: {language} with {servers} servers")
    click.echo("=" * 60)
    click.echo(f"📈 Estimated entries: {estimate_data['entries']:,}")
    click.echo(f"⏱️  Processing time: {estimate_data['time_hours']:.1f} hours")
    click.echo(f"💰 Estimated cost: €{estimate_data['cost_eur']:.2f}")
    click.echo(f"🚀 Speedup vs single: {estimate_data['speedup']:.1f}x")
    click.echo(f"⚡ Entries/minute: {estimate_data['rate_per_minute']:.0f}")


@cli.command()
@click.option('--source', '-s', required=True, help='Data source to test')
@click.option('--entries', '-n', default=10, help='Number of test entries')
@click.pass_context
def test_source(ctx, source, entries):
    """Test data source connectivity and extraction"""
    from .data_sources.factory import DataSourceFactory
    
    config = ctx.obj['config']
    click.echo(f"🧪 Testing data source: {source}")
    
    try:
        # Create data source
        data_source = DataSourceFactory.create(source, config)
        
        # Test connection
        asyncio.run(data_source.test_connection())
        click.echo("✅ Connection successful")
        
        # Test extraction
        click.echo(f"🔍 Testing extraction of {entries} entries...")
        test_results = asyncio.run(data_source.test_extraction(entries))
        
        click.echo(f"✅ Extracted {len(test_results)} entries")
        for i, entry in enumerate(test_results[:3]):  # Show first 3
            click.echo(f"   {i+1}. {entry['word']} - {entry.get('ipa', 'N/A')}")
        
        if len(test_results) > 3:
            click.echo(f"   ... and {len(test_results) - 3} more")
            
    except Exception as e:
        click.echo(f"❌ Test failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def version(ctx):
    """Show version information"""
    from . import __version__
    click.echo(f"AQEA Distributed Extractor v{__version__}")


if __name__ == '__main__':
    cli() 