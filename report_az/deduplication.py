"""
deduplication.py - Detect and handle duplicate articles
"""
import re
import logging
import sqlite3
from typing import List, Tuple, Dict
from database import get_connection

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    if not title:
        return ""
    # Lowercase
    title = title.lower()
    # Remove punctuation
    title = re.sub(r'[^\w\s]', '', title)
    # Normalize whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    # Azerbaijani character normalization
    replacements = {
        'ə': 'e', 'ı': 'i', 'ö': 'o', 'ü': 'u', 'ğ': 'g', 'ş': 's', 'ç': 'c'
    }
    for char, replacement in replacements.items():
        title = title.replace(char, replacement)
    return title


def find_duplicates() -> List[Tuple]:
    """Find articles with duplicate titles"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a1.id, a1.url, a1.title, a2.id, a2.url, a2.title
            FROM articles a1
            JOIN articles a2 ON a1.id < a2.id
            WHERE a1.title IS NOT NULL 
              AND a2.title IS NOT NULL
              AND lower(trim(a1.title)) = lower(trim(a2.title))
              AND a1.status = 'success'
              AND a2.status = 'success'
            LIMIT 1000
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def find_url_duplicates() -> List[Tuple]:
    """Find articles with duplicate URLs (should not exist but check)"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, COUNT(*) as count
            FROM articles
            GROUP BY url
            HAVING count > 1
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def mark_duplicates():
    """Mark duplicate articles in database"""
    duplicates = find_duplicates()
    if not duplicates:
        logger.info("No duplicate articles found")
        return 0
    
    logger.info(f"Found {len(duplicates)} duplicate article pairs")
    
    # Log them
    for dup in duplicates[:20]:
        logger.info(f"  Duplicate: {dup[1]} <-> {dup[4]}")
    
    return len(duplicates)


def get_dedup_stats() -> Dict:
    """Get deduplication statistics"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Count exact URL duplicates
        cursor.execute("SELECT COUNT(*) FROM (SELECT url FROM articles GROUP BY url HAVING COUNT(*) > 1)")
        url_dups = cursor.fetchone()[0]
        
        # Count exact title duplicates
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT lower(trim(title)) as norm_title 
                FROM articles 
                WHERE title IS NOT NULL AND status='success'
                GROUP BY norm_title 
                HAVING COUNT(*) > 1
            )
        """)
        title_dups = cursor.fetchone()[0]
        
        return {
            'url_duplicates': url_dups,
            'title_duplicates': title_dups,
        }
    finally:
        conn.close()

