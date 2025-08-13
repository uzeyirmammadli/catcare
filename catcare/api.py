from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.exceptions import BadRequest
from werkzeug.utils import secure_filename
import os
import tempfile
import uuid
from datetime import datetime
from . import db
from .models import Case, User, MediaMetadata, MediaThumbnail, BatchProcessingLog
from .services.case_service import CaseService
from .services.media_processing_service import MediaProcessingService
from .utils.validators import InputValidator, ValidationError
from .utils.decorators import rate_limit, validate_json, handle_errors
from .utils.helpers import create_response, paginate_query

api = Blueprint("api", __name__, url_prefix="/api/v1")

# Lazy initialization of services to avoid application context issues
case_service = None
media_processing_service = None
validator = None

def get_case_service():
    global case_service
    if case_service is None:
        case_service = CaseService()
    return case_service

def get_media_processing_service():
    global media_processing_service
    if media_processing_service is None:
        media_processing_service = MediaProcessingService()
    return media_processing_service

def get_validator():
    global validator
    if validator is None:
        validator = InputValidator()
    return validator


@api.route("/login", methods=["POST"])
@rate_limit(max_requests=5, window_minutes=15)  # Prevent brute force
@validate_json(["username", "password"])
@handle_errors
def login():
    """Login a user and return an access token"""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # Validate input
    try:
        username = get_validator().validate_username(username)
    except ValidationError as e:
        return jsonify(create_response(error=str(e))), 400

    user = User.query.filter((User.username == username) | (User.email == username)).first()

    if not user or not user.check_password(password):
        return jsonify(create_response(error="Invalid credentials")), 401

    access_token = create_access_token(identity=user.id)
    return jsonify(
        create_response(
            data={"access_token": access_token, "user_id": user.id}, message="Login successful"
        )
    )


@api.route("/cases", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=100, window_minutes=60)
@handle_errors
def get_cases():
    """Fetch cases for the authenticated user with pagination"""
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)
    status = request.args.get("status")

    query = Case.query.filter_by(user_id=user_id)

    if status:
        try:
            status = get_validator().validate_status(status)
            query = query.filter_by(status=status)
        except ValidationError as e:
            return jsonify(create_response(error=str(e))), 400

    pagination = paginate_query(query, page, per_page)

    cases_data = [case.to_dict() for case in pagination.items]

    return jsonify(
        create_response(
            data={
                "cases": cases_data,
                "pagination": {
                    "page": pagination.page,
                    "pages": pagination.pages,
                    "per_page": pagination.per_page,
                    "total": pagination.total,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
            }
        )
    )


@api.route("/cases", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=20, window_minutes=60)
@validate_json(["location"])
@handle_errors
def create_case():
    """Create a new case for the authenticated user"""
    data = request.get_json()
    user_id = get_jwt_identity()

    # Validate input data
    try:
        case_data = {
            "location": get_validator().validate_location(data.get("location")),
            "needs": get_validator().validate_needs(data.get("needs", [])),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
        }

        if case_data["latitude"] or case_data["longitude"]:
            case_data["latitude"], case_data["longitude"] = get_validator().validate_coordinates(
                case_data["latitude"], case_data["longitude"]
            )

    except ValidationError as e:
        return jsonify(create_response(error=str(e))), 400

    # Handle file uploads from multipart form data
    files = {}
    if request.files:
        files["photos"] = request.files.getlist("photos[]")
        files["videos"] = request.files.getlist("videos[]")

    try:
        new_case = get_case_service().create_case(user_id, case_data, files)
        return (
            jsonify(create_response(data=new_case.to_dict(), message="Case created successfully")),
            201,
        )

    except Exception as e:
        current_app.logger.error(f"Error creating case: {e}")
        return jsonify(create_response(error="Failed to create case")), 500


@api.route("/cases/<case_id>", methods=["PUT"])
@jwt_required()
@rate_limit(max_requests=30, window_minutes=60)
@handle_errors
def update_case(case_id):
    """Update an existing case by ID for the authenticated user"""
    data = request.get_json() or {}
    user_id = get_jwt_identity()

    # Validate input data
    try:
        case_data = {}
        if "location" in data:
            case_data["location"] = get_validator().validate_location(data["location"])
        if "needs" in data:
            case_data["needs"] = get_validator().validate_needs(data["needs"])
        if "status" in data:
            case_data["status"] = get_validator().validate_status(data["status"])
        if "latitude" in data or "longitude" in data:
            case_data["latitude"], case_data["longitude"] = get_validator().validate_coordinates(
                data.get("latitude"), data.get("longitude")
            )
    except ValidationError as e:
        return jsonify(create_response(error=str(e))), 400

    # Handle file uploads
    files = {}
    if request.files:
        files["photos"] = request.files.getlist("photos[]")
        files["videos"] = request.files.getlist("videos[]")

    try:
        updated_case = get_case_service().update_case(case_id, user_id, case_data, files)
        return jsonify(
            create_response(data=updated_case.to_dict(), message="Case updated successfully")
        )
    except ValueError as e:
        return jsonify(create_response(error=str(e))), 404
    except Exception as e:
        current_app.logger.error(f"Error updating case: {e}")
        return jsonify(create_response(error="Failed to update case")), 500


@api.route("/cases/<case_id>", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=200, window_minutes=60)
@handle_errors
def get_case_by_id(case_id):
    """Get a specific case by ID"""
    user_id = get_jwt_identity()
    case = Case.query.filter_by(id=case_id, user_id=user_id).first()

    if not case:
        return jsonify(create_response(error="Case not found")), 404

    return jsonify(create_response(data=case.to_dict()))


@api.route("/cases/<string:case_id>/resolve", methods=["PUT"])
@jwt_required()
@rate_limit(max_requests=20, window_minutes=60)
@handle_errors
def resolve_case(case_id):
    """Resolve a case with optional resolution files"""
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    # Handle file uploads
    files = {}
    if request.files:
        files["photos"] = request.files.getlist("photos[]")
        files["videos"] = request.files.getlist("videos[]")
        files["pdfs"] = request.files.getlist("pdfs[]")

    try:
        resolved_case = get_case_service().resolve_case(case_id, user_id, data, files)
        return jsonify(
            create_response(data=resolved_case.to_dict(), message="Case resolved successfully")
        )
    except ValueError as e:
        return jsonify(create_response(error=str(e))), 404
    except Exception as e:
        current_app.logger.error(f"Error resolving case: {e}")
        return jsonify(create_response(error="Failed to resolve case")), 500


@api.route("/cases/<case_id>", methods=["DELETE"])
@jwt_required()
@rate_limit(max_requests=10, window_minutes=60)
@handle_errors
def delete_case(case_id):
    """Delete a case and its associated files"""
    user_id = get_jwt_identity()

    try:
        success = get_case_service().delete_case(case_id, user_id)
        if success:
            return jsonify(create_response(message="Case deleted successfully"))
        else:
            return jsonify(create_response(error="Failed to delete case")), 500
    except ValueError as e:
        return jsonify(create_response(error=str(e))), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting case: {e}")
        return jsonify(create_response(error="Failed to delete case")), 500


@api.route("/cases/search", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=50, window_minutes=60)
@handle_errors
def search_cases():
    """Search cases with advanced filters and pagination"""
    user_id = get_jwt_identity()

    # Get search parameters
    filters = {
        "location": request.args.get("location"),
        "status": request.args.get("status"),
        "needs": request.args.getlist("needs[]"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
        "sort_by": request.args.get("sort_by", "created_at"),
        "sort_order": request.args.get("sort_order", "desc"),
    }

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 100)

    try:
        # Use the case service for advanced search
        pagination = get_case_service().search_cases(filters, page, per_page)

        # Filter results by user_id (add this to the service method)
        user_cases = [case for case in pagination.items if case.user_id == user_id]

        cases_data = [case.to_dict() for case in user_cases]

        return jsonify(
            create_response(
                data={
                    "cases": cases_data,
                    "pagination": {
                        "page": pagination.page,
                        "pages": pagination.pages,
                        "per_page": pagination.per_page,
                        "total": len(user_cases),
                        "has_next": pagination.has_next,
                        "has_prev": pagination.has_prev,
                    },
                    "filters": filters,
                }
            )
        )

    except Exception as e:
        current_app.logger.error(f"Error searching cases: {e}")
        return jsonify(create_response(error="Search failed")), 500


# Media Processing Endpoints

@api.route("/media/process", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=50, window_minutes=60)
@handle_errors
def process_single_media():
    """Process a single media file with advanced processing features."""
    user_id = get_jwt_identity()
    
    # Check if file is present
    if 'file' not in request.files:
        return jsonify(create_response(error="No file provided")), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify(create_response(error="No file selected")), 400
    
    # Get processing options
    case_id = request.form.get('case_id')
    compression_quality = request.form.get('compression_quality', 85, type=int)
    generate_thumbnails = request.form.get('generate_thumbnails', 'true').lower() == 'true'
    extract_metadata = request.form.get('extract_metadata', 'true').lower() == 'true'
    
    # Validate case ownership
    if case_id:
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify(create_response(error="Case not found or access denied")), 404
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        # Process the media file
        processing_options = {
            'compression_quality': compression_quality,
            'generate_thumbnails': generate_thumbnails,
            'extract_metadata': extract_metadata,
            'case_id': case_id
        }
        
        processed_media = get_media_processing_service().process_uploaded_media(
            temp_path, 
            original_filename=secure_filename(file.filename),
            options=processing_options
        )
        
        # Store metadata in database if case_id provided
        if case_id and processed_media:
            metadata = MediaMetadata(
                case_id=case_id,
                filename=processed_media.processed_filename,
                original_filename=processed_media.original_filename,
                file_size_original=processed_media.file_size_original,
                file_size_processed=processed_media.file_size_processed,
                compression_ratio=processed_media.compression_ratio,
                format_original=processed_media.format_original,
                format_processed=processed_media.format_processed,
                processing_time=processed_media.processing_time
            )
            
            # Add EXIF metadata if available
            if processed_media.metadata:
                timestamp_str = processed_media.metadata.get('timestamp_original')
                if timestamp_str:
                    try:
                        # Convert string timestamp to datetime object
                        if isinstance(timestamp_str, str):
                            metadata.timestamp_original = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        else:
                            metadata.timestamp_original = timestamp_str
                    except (ValueError, TypeError):
                        metadata.timestamp_original = None
                gps_coords = processed_media.metadata.get('gps_coordinates')
                if gps_coords:
                    metadata.gps_latitude = gps_coords[0]
                    metadata.gps_longitude = gps_coords[1]
                metadata.location_name = processed_media.metadata.get('location_name')
                camera_info = processed_media.metadata.get('camera_info', {})
                metadata.camera_make = camera_info.get('make')
                metadata.camera_model = camera_info.get('model')
                image_dims = processed_media.metadata.get('image_dimensions')
                if image_dims:
                    metadata.image_width = image_dims[0]
                    metadata.image_height = image_dims[1]
                metadata.orientation = processed_media.metadata.get('orientation', 1)
            
            db.session.add(metadata)
            db.session.flush()  # Get the ID
            
            # Store thumbnail information
            for thumb_info in processed_media.thumbnails:
                thumbnail = MediaThumbnail(
                    media_metadata_id=metadata.id,
                    size_label=thumb_info['size_label'],
                    filename=thumb_info['filename'],
                    file_size=thumb_info['file_size'],
                    width=thumb_info['width'],
                    height=thumb_info['height']
                )
                db.session.add(thumbnail)
            
            db.session.commit()
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        
        return jsonify(create_response(
            data={
                'processed_media': {
                    'filename': processed_media.processed_filename,
                    'original_filename': processed_media.original_filename,
                    'file_size_original': processed_media.file_size_original,
                    'file_size_processed': processed_media.file_size_processed,
                    'compression_ratio': processed_media.compression_ratio,
                    'format_original': processed_media.format_original,
                    'format_processed': processed_media.format_processed,
                    'thumbnails': processed_media.thumbnails,
                    'metadata': processed_media.metadata,
                    'processing_time': processed_media.processing_time,
                    'processing_status': processed_media.processing_status
                }
            },
            message="Media processed successfully"
        )), 201
        
    except Exception as e:
        # Clean up temporary file on error
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except OSError:
            pass
        
        current_app.logger.error(f"Media processing failed: {str(e)}")
        return jsonify(create_response(error="Media processing failed")), 500


@api.route("/media/batch-process", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=10, window_minutes=60)
@handle_errors
def process_batch_media():
    """Process multiple media files in batch with progress tracking."""
    user_id = get_jwt_identity()
    
    # Check if files are present
    if 'files' not in request.files:
        return jsonify(create_response(error="No files provided")), 400
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify(create_response(error="No files selected")), 400
    
    # Get processing options
    case_id = request.form.get('case_id')
    compression_quality = request.form.get('compression_quality', 85, type=int)
    generate_thumbnails = request.form.get('generate_thumbnails', 'true').lower() == 'true'
    extract_metadata = request.form.get('extract_metadata', 'true').lower() == 'true'
    
    # Validate case ownership
    if case_id:
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify(create_response(error="Case not found or access denied")), 404
    
    # Create batch processing log
    batch_log = BatchProcessingLog(
        user_id=user_id,
        total_files=len(files),
        successful_files=0,
        failed_files=0,
        started_at=datetime.utcnow(),
        status='STARTED'
    )
    db.session.add(batch_log)
    db.session.commit()
    
    try:
        processing_results = []
        total_size_original = 0
        total_size_processed = 0
        successful_count = 0
        failed_count = 0
        
        processing_options = {
            'compression_quality': compression_quality,
            'generate_thumbnails': generate_thumbnails,
            'extract_metadata': extract_metadata,
            'case_id': case_id
        }
        
        for file in files:
            if file.filename == '':
                continue
                
            try:
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                    file.save(temp_file.name)
                    temp_path = temp_file.name
                
                # Process the media file
                processed_media = get_media_processing_service().process_uploaded_media(
                    temp_path,
                    original_filename=secure_filename(file.filename),
                    options=processing_options
                )
                
                if processed_media:
                    # Store metadata in database if case_id provided
                    if case_id:
                        metadata = MediaMetadata(
                            case_id=case_id,
                            filename=processed_media.processed_filename,
                            original_filename=processed_media.original_filename,
                            file_size_original=processed_media.file_size_original,
                            file_size_processed=processed_media.file_size_processed,
                            compression_ratio=processed_media.compression_ratio,
                            format_original=processed_media.format_original,
                            format_processed=processed_media.format_processed,
                            processing_time=processed_media.processing_time
                        )
                        
                        # Add EXIF metadata if available
                        if processed_media.metadata:
                            timestamp_str = processed_media.metadata.get('timestamp_original')
                            if timestamp_str:
                                try:
                                    # Convert string timestamp to datetime object
                                    if isinstance(timestamp_str, str):
                                        metadata.timestamp_original = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    else:
                                        metadata.timestamp_original = timestamp_str
                                except (ValueError, TypeError):
                                    metadata.timestamp_original = None
                            gps_coords = processed_media.metadata.get('gps_coordinates')
                            if gps_coords:
                                metadata.gps_latitude = gps_coords[0]
                                metadata.gps_longitude = gps_coords[1]
                            metadata.location_name = processed_media.metadata.get('location_name')
                            camera_info = processed_media.metadata.get('camera_info', {})
                            metadata.camera_make = camera_info.get('make')
                            metadata.camera_model = camera_info.get('model')
                            image_dims = processed_media.metadata.get('image_dimensions')
                            if image_dims:
                                metadata.image_width = image_dims[0]
                                metadata.image_height = image_dims[1]
                            metadata.orientation = processed_media.metadata.get('orientation', 1)
                        
                        db.session.add(metadata)
                        db.session.flush()
                        
                        # Store thumbnail information
                        for thumb_info in processed_media.thumbnails:
                            thumbnail = MediaThumbnail(
                                media_metadata_id=metadata.id,
                                size_label=thumb_info['size_label'],
                                filename=thumb_info['filename'],
                                file_size=thumb_info['file_size'],
                                width=thumb_info['width'],
                                height=thumb_info['height']
                            )
                            db.session.add(thumbnail)
                    
                    processing_results.append({
                        'filename': processed_media.original_filename,
                        'status': 'success',
                        'processed_filename': processed_media.processed_filename,
                        'compression_ratio': processed_media.compression_ratio,
                        'processing_time': processed_media.processing_time
                    })
                    
                    total_size_original += processed_media.file_size_original
                    total_size_processed += processed_media.file_size_processed
                    successful_count += 1
                else:
                    processing_results.append({
                        'filename': file.filename,
                        'status': 'failed',
                        'error': 'Processing failed'
                    })
                    failed_count += 1
                
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                    
            except Exception as e:
                processing_results.append({
                    'filename': file.filename,
                    'status': 'failed',
                    'error': str(e)
                })
                failed_count += 1
                
                # Clean up temporary file on error
                try:
                    if 'temp_path' in locals():
                        os.unlink(temp_path)
                except OSError:
                    pass
        
        # Update batch processing log
        batch_log.successful_files = successful_count
        batch_log.failed_files = failed_count
        batch_log.total_size_original = total_size_original
        batch_log.total_size_processed = total_size_processed
        batch_log.average_compression_ratio = (total_size_processed / total_size_original * 100) if total_size_original > 0 else 0
        batch_log.completed_at = datetime.utcnow()
        batch_log.processing_time = (batch_log.completed_at - batch_log.started_at).total_seconds()
        batch_log.status = 'COMPLETED'
        
        db.session.commit()
        
        return jsonify(create_response(
            data={
                'batch_id': batch_log.id,
                'total_files': len(files),
                'successful_files': successful_count,
                'failed_files': failed_count,
                'total_size_original': total_size_original,
                'total_size_processed': total_size_processed,
                'average_compression_ratio': batch_log.average_compression_ratio,
                'processing_time': batch_log.processing_time,
                'results': processing_results
            },
            message="Batch processing completed"
        )), 201
        
    except Exception as e:
        # Update batch log with failure
        batch_log.status = 'FAILED'
        batch_log.completed_at = datetime.utcnow()
        db.session.commit()
        
        current_app.logger.error(f"Batch processing failed: {str(e)}")
        return jsonify(create_response(error="Batch processing failed")), 500


@api.route("/media/processing-status/<int:batch_id>", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=100, window_minutes=60)
@handle_errors
def get_processing_status(batch_id):
    """Get the status of a batch processing operation."""
    user_id = get_jwt_identity()
    
    batch_log = BatchProcessingLog.query.filter_by(id=batch_id, user_id=user_id).first()
    if not batch_log:
        return jsonify(create_response(error="Batch processing log not found")), 404
    
    return jsonify(create_response(data=batch_log.to_dict()))


@api.route("/media/processing-status", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=50, window_minutes=60)
@handle_errors
def get_user_processing_history():
    """Get processing history for the authenticated user with pagination."""
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)
    status = request.args.get("status")
    
    query = BatchProcessingLog.query.filter_by(user_id=user_id)
    
    if status:
        if status.upper() not in ['STARTED', 'COMPLETED', 'FAILED', 'CANCELLED']:
            return jsonify(create_response(error="Invalid status")), 400
        query = query.filter_by(status=status.upper())
    
    query = query.order_by(BatchProcessingLog.started_at.desc())
    pagination = paginate_query(query, page, per_page)
    
    logs_data = [log.to_dict() for log in pagination.items]
    
    # Get user statistics
    user_stats = BatchProcessingLog.get_user_stats(user_id)
    
    return jsonify(create_response(
        data={
            "processing_logs": logs_data,
            "user_stats": user_stats,
            "pagination": {
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    ))


@api.route("/media/metadata/<case_id>", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=100, window_minutes=60)
@handle_errors
def get_media_metadata(case_id):
    """Get media metadata for a specific case."""
    user_id = get_jwt_identity()
    
    # Verify case ownership
    case = Case.query.filter_by(id=case_id, user_id=user_id).first()
    if not case:
        return jsonify(create_response(error="Case not found or access denied")), 404
    
    # Get pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    
    # Query media metadata for the case
    query = MediaMetadata.query.filter_by(case_id=case_id).order_by(MediaMetadata.created_at.desc())
    pagination = paginate_query(query, page, per_page)
    
    metadata_list = [metadata.to_dict() for metadata in pagination.items]
    
    return jsonify(create_response(
        data={
            "case_id": case_id,
            "media_metadata": metadata_list,
            "pagination": {
                "page": pagination.page,
                "pages": pagination.pages,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    ))


@api.route("/media/metadata/<case_id>/<filename>", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=200, window_minutes=60)
@handle_errors
def get_single_media_metadata(case_id, filename):
    """Get metadata for a specific media file."""
    user_id = get_jwt_identity()
    
    # Verify case ownership
    case = Case.query.filter_by(id=case_id, user_id=user_id).first()
    if not case:
        return jsonify(create_response(error="Case not found or access denied")), 404
    
    # Get media metadata
    metadata = MediaMetadata.query.filter_by(case_id=case_id, filename=filename).first()
    if not metadata:
        return jsonify(create_response(error="Media metadata not found")), 404
    
    return jsonify(create_response(data=metadata.to_dict()))


# Performance and Optimization Endpoints

@api.route("/system/performance/stats", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=10, window_minutes=60)
@handle_errors
def get_performance_stats():
    """Get system performance statistics."""
    user_id = get_jwt_identity()
    
    # Check if user has admin privileges (implement based on your user model)
    user = User.query.get(user_id)
    if not user or not getattr(user, 'is_admin', False):
        return jsonify(create_response(error="Admin access required")), 403
    
    try:
        from .services.async_processing_queue import get_processing_queue
        from .services.media_cache_service import get_cache_service
        from .services.temp_file_manager import get_temp_file_manager
        from .services.cdn_service import get_cdn_service
        
        # Collect performance stats from all services
        stats = {
            'processing_queue': get_processing_queue().get_queue_stats(),
            'cache_service': get_cache_service().get_cache_stats(),
            'temp_file_manager': get_temp_file_manager().get_stats(),
            'cdn_service': get_cdn_service().get_performance_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(create_response(data=stats))
        
    except Exception as e:
        current_app.logger.error(f"Performance stats collection failed: {str(e)}")
        return jsonify(create_response(error="Failed to collect performance stats")), 500


@api.route("/system/performance/benchmarks", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=2, window_minutes=60)
@handle_errors
def run_performance_benchmarks():
    """Run comprehensive performance benchmarks."""
    user_id = get_jwt_identity()
    
    # Check if user has admin privileges
    user = User.query.get(user_id)
    if not user or not getattr(user, 'is_admin', False):
        return jsonify(create_response(error="Admin access required")), 403
    
    try:
        from .services.performance_benchmarks import get_performance_benchmarks
        
        # Run benchmarks (this may take a while)
        benchmarks = get_performance_benchmarks()
        results = benchmarks.run_comprehensive_benchmarks()
        
        return jsonify(create_response(
            data=results,
            message="Performance benchmarks completed"
        ))
        
    except Exception as e:
        current_app.logger.error(f"Performance benchmarks failed: {str(e)}")
        return jsonify(create_response(error="Benchmarks failed")), 500


@api.route("/system/cache/optimize", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=5, window_minutes=60)
@handle_errors
def optimize_cache():
    """Optimize cache by removing expired and least-used entries."""
    user_id = get_jwt_identity()
    
    # Check if user has admin privileges
    user = User.query.get(user_id)
    if not user or not getattr(user, 'is_admin', False):
        return jsonify(create_response(error="Admin access required")), 403
    
    try:
        from .services.media_cache_service import get_cache_service
        
        cache_service = get_cache_service()
        optimization_results = cache_service.optimize_cache()
        
        return jsonify(create_response(
            data=optimization_results,
            message="Cache optimization completed"
        ))
        
    except Exception as e:
        current_app.logger.error(f"Cache optimization failed: {str(e)}")
        return jsonify(create_response(error="Cache optimization failed")), 500


@api.route("/system/cache/clear", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=3, window_minutes=60)
@handle_errors
def clear_cache():
    """Clear cache entries."""
    user_id = get_jwt_identity()
    
    # Check if user has admin privileges
    user = User.query.get(user_id)
    if not user or not getattr(user, 'is_admin', False):
        return jsonify(create_response(error="Admin access required")), 403
    
    try:
        from .services.media_cache_service import get_cache_service
        
        data = request.get_json() or {}
        cache_type = data.get('cache_type')  # 'memory', 'disk', or None for both
        
        cache_service = get_cache_service()
        cleared_counts = cache_service.clear_cache(cache_type)
        
        return jsonify(create_response(
            data=cleared_counts,
            message="Cache cleared successfully"
        ))
        
    except Exception as e:
        current_app.logger.error(f"Cache clearing failed: {str(e)}")
        return jsonify(create_response(error="Cache clearing failed")), 500


@api.route("/system/temp-files/cleanup", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=5, window_minutes=60)
@handle_errors
def cleanup_temp_files():
    """Clean up temporary files."""
    user_id = get_jwt_identity()
    
    # Check if user has admin privileges
    user = User.query.get(user_id)
    if not user or not getattr(user, 'is_admin', False):
        return jsonify(create_response(error="Admin access required")), 403
    
    try:
        from .services.temp_file_manager import get_temp_file_manager
        
        data = request.get_json() or {}
        cleanup_type = data.get('cleanup_type', 'expired')  # 'expired', 'all', 'by_purpose', 'by_tags'
        
        temp_manager = get_temp_file_manager()
        
        if cleanup_type == 'expired':
            cleaned_count = temp_manager.cleanup_expired()
        elif cleanup_type == 'all':
            cleaned_count = temp_manager.cleanup_all()
        elif cleanup_type == 'by_purpose':
            purpose = data.get('purpose')
            if not purpose:
                return jsonify(create_response(error="Purpose required for by_purpose cleanup")), 400
            cleaned_count = temp_manager.cleanup_by_purpose(purpose)
        elif cleanup_type == 'by_tags':
            tags = data.get('tags', [])
            if not tags:
                return jsonify(create_response(error="Tags required for by_tags cleanup")), 400
            cleaned_count = temp_manager.cleanup_by_tags(tags)
        else:
            return jsonify(create_response(error="Invalid cleanup_type")), 400
        
        return jsonify(create_response(
            data={'cleaned_files': cleaned_count},
            message=f"Cleaned up {cleaned_count} temporary files"
        ))
        
    except Exception as e:
        current_app.logger.error(f"Temp file cleanup failed: {str(e)}")
        return jsonify(create_response(error="Temp file cleanup failed")), 500


@api.route("/system/storage/optimize", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=3, window_minutes=60)
@handle_errors
def optimize_storage():
    """Optimize storage by cleaning up old files and unused resources."""
    user_id = get_jwt_identity()
    
    # Check if user has admin privileges
    user = User.query.get(user_id)
    if not user or not getattr(user, 'is_admin', False):
        return jsonify(create_response(error="Admin access required")), 403
    
    try:
        from .services.storage_service import StorageService
        
        storage_service = StorageService()
        optimization_results = storage_service.optimize_storage()
        
        return jsonify(create_response(
            data=optimization_results,
            message="Storage optimization completed"
        ))
        
    except Exception as e:
        current_app.logger.error(f"Storage optimization failed: {str(e)}")
        return jsonify(create_response(error="Storage optimization failed")), 500


@api.route("/media/async-process", methods=["POST"])
@jwt_required()
@rate_limit(max_requests=20, window_minutes=60)
@handle_errors
def submit_async_processing():
    """Submit media file for asynchronous processing."""
    user_id = get_jwt_identity()
    
    # Check if file is present
    if 'file' not in request.files:
        return jsonify(create_response(error="No file provided")), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify(create_response(error="No file selected")), 400
    
    # Get processing options
    case_id = request.form.get('case_id')
    priority = request.form.get('priority', 'normal')
    processing_options = {
        'compression_quality': request.form.get('compression_quality', 85, type=int),
        'generate_thumbnails': request.form.get('generate_thumbnails', 'true').lower() == 'true',
        'extract_metadata': request.form.get('extract_metadata', 'true').lower() == 'true',
        'case_id': case_id
    }
    
    # Validate case ownership
    if case_id:
        case = Case.query.filter_by(id=case_id, user_id=user_id).first()
        if not case:
            return jsonify(create_response(error="Case not found or access denied")), 404
    
    try:
        from .services.async_processing_queue import get_processing_queue, TaskPriority
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        # Map priority string to enum
        priority_map = {
            'low': TaskPriority.LOW,
            'normal': TaskPriority.NORMAL,
            'high': TaskPriority.HIGH,
            'urgent': TaskPriority.URGENT
        }
        task_priority = priority_map.get(priority.lower(), TaskPriority.NORMAL)
        
        # Submit to async queue
        processing_queue = get_processing_queue()
        task_id = processing_queue.submit_task(
            'media_processing',
            temp_path,
            {**processing_options, 'original_filename': secure_filename(file.filename)},
            task_priority
        )
        
        return jsonify(create_response(
            data={
                'task_id': task_id,
                'status': 'submitted',
                'priority': priority,
                'estimated_completion': 'varies'
            },
            message="File submitted for asynchronous processing"
        )), 202
        
    except Exception as e:
        # Clean up temporary file on error
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except OSError:
            pass
        
        current_app.logger.error(f"Async processing submission failed: {str(e)}")
        return jsonify(create_response(error="Failed to submit for processing")), 500


@api.route("/media/async-status/<task_id>", methods=["GET"])
@jwt_required()
@rate_limit(max_requests=100, window_minutes=60)
@handle_errors
def get_async_processing_status(task_id):
    """Get status of asynchronous processing task."""
    user_id = get_jwt_identity()
    
    try:
        from .services.async_processing_queue import get_processing_queue
        
        processing_queue = get_processing_queue()
        task_status = processing_queue.get_task_status(task_id)
        
        if not task_status:
            return jsonify(create_response(error="Task not found")), 404
        
        return jsonify(create_response(data=task_status))
        
    except Exception as e:
        current_app.logger.error(f"Async status check failed: {str(e)}")
        return jsonify(create_response(error="Failed to get task status")), 500
