"""
Database Module for AQEA Distributed Extractor

Zentrale Datenbank-Anbindung für alle Worker und Master.
"""

from .supabase import SupabaseDatabase, get_database, close_database

__all__ = ['SupabaseDatabase', 'get_database', 'close_database'] 