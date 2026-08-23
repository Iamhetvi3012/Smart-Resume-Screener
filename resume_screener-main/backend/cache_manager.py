"""
Supabase Cache Manager for Resume Processing
Implements two-level caching:
1. Parsed resume cache (by file hash)
2. Screening result cache (by file hash + job details)
"""

import hashlib
import logging
from typing import Optional, Dict
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching of parsed resumes and screening results in Supabase."""

    def __init__(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
            )

        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Cache manager initialized with Supabase")

    @staticmethod
    def hash_file(file_bytes: bytes) -> str:
        """
        Generate SHA-256 hash of file content.

        Args:
            file_bytes: File content as bytes

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def generate_screening_key(
        file_hash: str, job_title: str, job_description: str
    ) -> str:
        """
        Generate unique key for screening cache.

        Args:
            file_hash: Hash of the resume file
            job_title: Job title
            job_description: Job description

        Returns:
            Unique screening cache key
        """
        composite = f"{file_hash}:{job_title}:{job_description}"
        return hashlib.sha256(composite.encode()).hexdigest()

    def get_parsed_resume(self, file_hash: str) -> Optional[Dict]:
        """
        Retrieve parsed resume from cache.

        Args:
            file_hash: Hash of the resume file

        Returns:
            Parsed resume dictionary if found, None otherwise
        """
        try:
            response = (
                self.supabase.table("parsed_resumes")
                .select("*")
                .eq("file_hash", file_hash)
                .execute()
            )

            if response.data and len(response.data) > 0:
                logger.info(f"✓ Cache HIT for parsed resume: {file_hash[:16]}...")
                return response.data[0]["parsed_data"]

            logger.info(f"✗ Cache MISS for parsed resume: {file_hash[:16]}...")
            return None

        except Exception as e:
            logger.error(f"Error retrieving parsed resume from cache: {e}")
            return None

    def store_parsed_resume(self, file_hash: str, parsed_data: Dict) -> bool:
        """
        Store parsed resume in cache.

        Args:
            file_hash: Hash of the resume file
            parsed_data: Parsed resume dictionary

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            data = {"file_hash": file_hash, "parsed_data": parsed_data}

            self.supabase.table("parsed_resumes").upsert(data).execute()
            logger.info(f"✓ Stored parsed resume in cache: {file_hash[:16]}...")
            return True

        except Exception as e:
            logger.error(f"Error storing parsed resume in cache: {e}")
            return False

    def get_screening_result(
        self, file_hash: str, job_title: str, job_description: str
    ) -> Optional[Dict]:
        """
        Retrieve screening result from cache.

        Args:
            file_hash: Hash of the resume file
            job_title: Job title
            job_description: Job description

        Returns:
            Screening result dictionary if found, None otherwise
        """
        try:
            screening_key = self.generate_screening_key(
                file_hash, job_title, job_description
            )

            response = (
                self.supabase.table("screening_results")
                .select("*")
                .eq("screening_key", screening_key)
                .execute()
            )

            if response.data and len(response.data) > 0:
                logger.info(f"✓ Cache HIT for screening: {screening_key[:16]}...")
                return response.data[0]["screening_data"]

            logger.info(f"✗ Cache MISS for screening: {screening_key[:16]}...")
            return None

        except Exception as e:
            logger.error(f"Error retrieving screening result from cache: {e}")
            return None

    def store_screening_result(
        self,
        file_hash: str,
        job_title: str,
        job_description: str,
        screening_data: Dict,
    ) -> bool:
        """
        Store screening result in cache.

        Args:
            file_hash: Hash of the resume file
            job_title: Job title
            job_description: Job description
            screening_data: Screening result dictionary

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            screening_key = self.generate_screening_key(
                file_hash, job_title, job_description
            )

            data = {
                "screening_key": screening_key,
                "file_hash": file_hash,
                "job_title": job_title,
                "job_description": job_description,
                "screening_data": screening_data,
            }

            self.supabase.table("screening_results").upsert(data).execute()
            logger.info(f"✓ Stored screening result in cache: {screening_key[:16]}...")
            return True

        except Exception as e:
            logger.error(f"Error storing screening result in cache: {e}")
            return False

    def get_complete_result(
        self, file_hash: str, job_title: str, job_description: str
    ) -> Optional[Dict]:
        """
        Retrieve complete result (parsed + screened) from cache.

        Args:
            file_hash: Hash of the resume file
            job_title: Job title
            job_description: Job description

        Returns:
            Dictionary with 'parsed' and 'screened' keys if both found, None otherwise
        """
        screening_result = self.get_screening_result(
            file_hash, job_title, job_description
        )
        parsed_resume = self.get_parsed_resume(file_hash)

        if screening_result and parsed_resume:
            logger.info(f"✓ Complete cache HIT for {file_hash[:16]}...")
            return {"parsed": parsed_resume, "screened": screening_result}

        return None
