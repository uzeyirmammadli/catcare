from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.exceptions import BadRequest
from . import db
from .models import Case, User
from .services.case_service import CaseService
from .utils.validators import InputValidator, ValidationError
from .utils.decorators import rate_limit, validate_json, handle_errors
from .utils.helpers import create_response, paginate_query

api = Blueprint("api", __name__, url_prefix="/api/v1")
case_service = CaseService()
validator = InputValidator()


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
        username = validator.validate_username(username)
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
            status = validator.validate_status(status)
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
            "location": validator.validate_location(data.get("location")),
            "needs": validator.validate_needs(data.get("needs", [])),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
        }

        if case_data["latitude"] or case_data["longitude"]:
            case_data["latitude"], case_data["longitude"] = validator.validate_coordinates(
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
        new_case = case_service.create_case(user_id, case_data, files)
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
            case_data["location"] = validator.validate_location(data["location"])
        if "needs" in data:
            case_data["needs"] = validator.validate_needs(data["needs"])
        if "status" in data:
            case_data["status"] = validator.validate_status(data["status"])
        if "latitude" in data or "longitude" in data:
            case_data["latitude"], case_data["longitude"] = validator.validate_coordinates(
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
        updated_case = case_service.update_case(case_id, user_id, case_data, files)
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
        resolved_case = case_service.resolve_case(case_id, user_id, data, files)
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
        success = case_service.delete_case(case_id, user_id)
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
        pagination = case_service.search_cases(filters, page, per_page)

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
