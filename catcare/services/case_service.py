"""
Case service layer for business logic separation
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from werkzeug.utils import secure_filename
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from ..models import Case, db
from .storage_service import StorageService


class CaseService:
    """Service class for case-related operations"""

    def __init__(self):
        self.storage_service = StorageService()

    def create_case(self, user_id: int, case_data: Dict[str, Any], files: Dict) -> Case:
        """Create a new case with file uploads"""
        try:
            # Upload files
            photo_urls = self._upload_files(files.get("photos", []), "photos")
            video_urls = self._upload_files(files.get("videos", []), "videos")

            # Create case
            case = Case(
                id=str(uuid.uuid4()),
                photos=photo_urls,
                videos=video_urls,
                location=case_data["location"],
                latitude=case_data.get("latitude"),
                longitude=case_data.get("longitude"),
                needs=case_data.get("needs", []),
                status="OPEN",
                user_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            db.session.add(case)
            db.session.commit()
            return case

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating case: {e}")
            raise

    def update_case(
        self, case_id: str, user_id: int, case_data: Dict[str, Any], files: Dict = None
    ) -> Case:
        """Update an existing case"""
        try:
            case = Case.query.filter_by(id=case_id, user_id=user_id).first()
            if not case:
                raise ValueError("Case not found or unauthorized")

            # Update basic fields
            for field in ["location", "latitude", "longitude", "needs", "status"]:
                if field in case_data:
                    setattr(case, field, case_data[field])

            # Handle file uploads if provided
            if files:
                if files.get("photos"):
                    new_photos = self._upload_files(files["photos"], "photos")
                    case.photos = (case.photos or []) + new_photos

                if files.get("videos"):
                    new_videos = self._upload_files(files["videos"], "videos")
                    case.videos = (case.videos or []) + new_videos

            case.updated_at = datetime.utcnow()
            db.session.commit()
            return case

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating case: {e}")
            raise

    def resolve_case(
        self, case_id: str, user_id: int, resolution_data: Dict[str, Any], files: Dict = None
    ) -> Case:
        """Resolve a case with optional resolution files"""
        try:
            case = Case.query.get_or_404(case_id)

            # Upload resolution files
            if files:
                case.resolution_photos = self._upload_files(
                    files.get("photos", []), "resolution_photos"
                )
                case.resolution_videos = self._upload_files(
                    files.get("videos", []), "resolution_videos"
                )
                case.pdfs = self._upload_files(
                    files.get("pdfs", []), "resolution_docs", allowed_extensions=["pdf"]
                )

            # Update case
            case.status = "RESOLVED"
            case.resolution_notes = resolution_data.get("resolution_notes")
            case.resolved_at = datetime.utcnow()
            case.resolved_by_id = user_id
            case.updated_at = datetime.utcnow()

            db.session.commit()
            return case

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resolving case: {e}")
            raise

    def delete_case(self, case_id: str, user_id: int) -> bool:
        """Delete a case and its associated files"""
        try:
            case = Case.query.filter_by(id=case_id, user_id=user_id).first()
            if not case:
                raise ValueError("Case not found or unauthorized")

            # Delete associated files from storage
            self._delete_case_files(case)

            db.session.delete(case)
            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting case: {e}")
            raise

    def search_cases(self, filters: Dict[str, Any], page: int = 1, per_page: int = 10):
        """Search cases with filters and pagination"""
        try:
            query = Case.query

            # Apply filters
            if filters.get("location"):
                query = query.filter(Case.location.ilike(f"%{filters['location']}%"))

            if filters.get("status"):
                query = query.filter(Case.status == filters["status"].upper())

            if filters.get("needs"):
                from sqlalchemy import or_

                need_conditions = [Case.needs.any(need) for need in filters["needs"]]
                query = query.filter(or_(*need_conditions))

            if filters.get("date_from"):
                query = query.filter(Case.created_at >= filters["date_from"])

            if filters.get("date_to"):
                query = query.filter(Case.created_at <= filters["date_to"])

            # Apply sorting
            sort_by = filters.get("sort_by", "created_at")
            sort_order = filters.get("sort_order", "desc")
            sort_column = getattr(Case, sort_by)

            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            return query.paginate(page=page, per_page=per_page, error_out=False)

        except Exception as e:
            current_app.logger.error(f"Error searching cases: {e}")
            raise

    def _upload_files(
        self, files: List, folder: str, allowed_extensions: List[str] = None
    ) -> List[str]:
        """Upload multiple files and return URLs"""
        if not files:
            return []

        urls = []
        for file in files:
            if file and file.filename:
                if allowed_extensions and not any(
                    file.filename.lower().endswith(ext) for ext in allowed_extensions
                ):
                    continue

                url = self.storage_service.upload_file(file, folder)
                if url:
                    urls.append(url)

        return urls

    def _delete_case_files(self, case: Case):
        """Delete all files associated with a case"""
        files_to_delete = []

        if case.photos:
            files_to_delete.extend(case.photos)
        if case.videos:
            files_to_delete.extend(case.videos)
        if case.resolution_photos:
            files_to_delete.extend(case.resolution_photos)
        if case.resolution_videos:
            files_to_delete.extend(case.resolution_videos)
        if case.pdfs:
            files_to_delete.extend(case.pdfs)

        for file_url in files_to_delete:
            self.storage_service.delete_file(file_url)
