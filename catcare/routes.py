import os
import uuid
from uuid import uuid4
from datetime import datetime, timedelta
import logging
from flask import request, render_template, redirect, url_for, jsonify, flash, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from flask import Blueprint, send_from_directory, send_file
from math import radians, cos, sin, asin, sqrt
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf.csrf import generate_csrf
from functools import wraps
from .models import db, User, Comment, Case, SavedSearch
from .forms import RegistrationForm, LoginForm, CommentForm, UpdateProfileForm, ChangePasswordForm
from . import db, login_manager
from .services.storage_service import StorageService

main = Blueprint("main", __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@main.route("/test")
def test_interface():
    return send_file("templates/test.html")


@main.route("/comment/<comment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_comment(comment_id):
    # Get the comment by id
    comment = Comment.query.get(comment_id)

    # If the comment doesn't exist, redirect with an error message
    if not comment:
        flash("Comment not found.", "error")
        return redirect(url_for("view_case_details", case_id=comment.case_id))

    # Get updated data from the request
    content = request.form.get("content")
    case_id = request.form.get("case_id")  # Make sure this is provided in the request

    # Validate that the case exists in the database
    case = Case.query.get(case_id)
    if not case:
        flash("The referenced case does not exist.", "error")
        return redirect(url_for("main.view_case_details", case_id=comment.case_id))

    # Update the comment fields
    comment.content = content if content else comment.content
    comment.case_id = case.id  # Ensure `case_id` is set correctly
    comment.updated_at = datetime.utcnow()

    try:
        # Commit changes to the database
        db.session.commit()
        flash("Comment updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the comment.", "error")
        print(e)  # For debugging

    return redirect(url_for("main.view_case_details", case_id=comment.case_id))


@main.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    # Check if user is authorized to delete the comment
    if comment.user_id != current_user.id:
        flash("You are not authorized to delete this comment.", "error")
        return redirect(url_for("main.view_case_details", case_id=comment.case_id))

    try:
        db.session.delete(comment)
        db.session.commit()
        flash("Comment deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment: {e}")
        flash("Error deleting comment. Please try again.", "error")

    return redirect(url_for("main.view_case_details", case_id=comment.case_id))


@login_manager.user_loader
def load_user(user_id):
    try:
        user = User.query.get(int(user_id))
        db.session.commit()
        return user
    except SQLAlchemyError:
        db.session.rollback()
        return None


# Authentication routes
@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.homepage"))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Check if username or email exists
            if User.query.filter_by(username=form.username.data).first():
                flash("Username already exists. Please choose a different one.", "error")
                return render_template("register.html", form=form)

            if User.query.filter_by(email=form.email.data).first():
                flash("Email already registered. Please use a different email.", "error")
                return render_template("register.html", form=form)

            # Create new user
            user = User(
                username=form.username.data, email=form.email.data, join_date=datetime.utcnow()
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("main.login"))
        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {str(e)}", "error")

    return render_template("register.html", form=form)


@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.homepage"))

    form = LoginForm()
    if form.validate_on_submit():
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == form.login.data) | (User.email == form.login.data)
        ).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            return redirect(next_page if next_page else url_for("main.homepage"))
        else:
            flash("Invalid username/email or password", "error")

    return render_template("login.html", form=form)


@main.route("/check_users")
def check_users():
    users = User.query.all()
    return f"Number of users: {len(users)}"


@main.route("/logout")
@login_required
def logout():
    print("Logging out user")
    logout_user()
    print(f"User authenticated: {current_user.is_authenticated}")
    return redirect(url_for("main.show_cases"))


@main.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)


@main.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.bio = form.bio.data
        db.session.commit()
        flash("Your profile has been updated!", "success")
        return redirect(url_for("main.profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.bio.data = current_user.bio
    return render_template("edit_profile.html", form=form)


@main.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Your password has been updated!", "success")
            return redirect(url_for("main.profile"))
        else:
            flash("Invalid current password.", "danger")
    return render_template("change_password.html", form=form)


# Error handlers
@main.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@main.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("500.html"), 500


def upload_file(file):
    """Upload file using StorageService with proper error handling"""
    if not file:
        return None
    
    storage_service = StorageService()
    return storage_service.upload_file(file)


@main.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if request.method == "POST":
        try:
            current_app.logger.info("Starting case creation...")
            
            # Handle photos
            photos = request.files.getlist("photos[]")
            photo_urls = []

            # Handle videos
            videos = request.files.getlist("videos[]")
            video_urls = []

            # Handle location
            latitude = request.form.get("latitude")
            longitude = request.form.get("longitude")
            location = request.form.get("location")
            
            current_app.logger.info(f"Form data - Location: {location}, Photos: {len(photos)}, Videos: {len(videos)}")

            # Validate required fields
            if not location:
                flash("Location is required.", "error")
                return render_template("report.html")

            # Upload photos using StorageService
            storage_service = StorageService()
            for photo in photos:
                if photo and photo.filename:
                    current_app.logger.info(f"Uploading photo: {photo.filename}")
                    photo_url = storage_service.upload_file(photo, "photos")
                    if photo_url:
                        photo_urls.append(photo_url)
                        current_app.logger.info(f"Photo uploaded: {photo_url}")

            # Upload videos using StorageService
            for video in videos:
                if video and video.filename:
                    current_app.logger.info(f"Uploading video: {video.filename}")
                    video_url = storage_service.upload_file(video, "videos")
                    if video_url:
                        video_urls.append(video_url)
                        current_app.logger.info(f"Video uploaded: {video_url}")

            current_app.logger.info("Creating case object...")
            new_case = Case(
                id=str(uuid4()),
                photos=photo_urls,
                videos=video_urls,
                location=location,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                needs=request.form.getlist("needs[]"),
                status="OPEN",
                user_id=current_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            current_app.logger.info("Adding case to database...")
            db.session.add(new_case)
            db.session.commit()
            current_app.logger.info("Case created successfully!")
            flash("Case reported successfully!", "success")
            return redirect(url_for("main.show_cases"))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating case: {e}", exc_info=True)
            flash("Error creating case. Please try again.", "error")
            return render_template("report.html")

    return render_template("report.html")


@main.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # For direct GCS URLs, redirect to the actual URL
    if filename.startswith("https://storage.googleapis.com/"):
        return redirect(filename)

    # For local uploads, serve from your uploads directory
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@main.route("/")
def homepage():
    """Show the homepage with stats and success stories."""
    try:
        # Get statistics
        total_cases = Case.query.count()
        resolved_cases = Case.query.filter_by(status="RESOLVED").count()
        total_users = User.query.count()
        
        # Calculate success rate
        success_rate = int((resolved_cases / total_cases * 100)) if total_cases > 0 else 0
        
        stats = {
            'cats_helped': resolved_cases,
            'active_volunteers': total_users,
            'success_rate': success_rate
        }
        
        # Get recent success stories (resolved cases with photos)
        success_stories_query = (
            Case.query
            .filter_by(status="RESOLVED")
            .order_by(Case.resolved_at.desc().nullslast())
            .limit(6)
            .all()
        )
        
        # Format success stories
        formatted_stories = []
        for case in success_stories_query:
            # Check if case has photos (either original or resolution photos)
            has_photos = (case.photos and len(case.photos) > 0) or (case.resolution_photos and len(case.resolution_photos) > 0)
            
            if has_photos:
                story = {
                    'title': f"Success in {case.location.split(',')[0] if case.location else 'Unknown Location'}",
                    'description': case.resolution_notes or "Another successful rescue and recovery!",
                    'location': case.location.split(',')[0] if case.location else 'Unknown Location',
                    'date': case.resolved_at.strftime('%B %Y') if case.resolved_at else 'Recently',
                    'before_photo': case.photos[0] if case.photos and len(case.photos) > 0 else None,
                    'after_photo': case.resolution_photos[0] if case.resolution_photos and len(case.resolution_photos) > 0 else None
                }
                formatted_stories.append(story)
        
        return render_template(
            "homepage.html",
            stats=stats,
            success_stories=formatted_stories
        )
        
    except Exception as e:
        current_app.logger.error(f"Error loading homepage: {e}")
        # Fallback to basic homepage with default stats
        default_stats = {
            'cats_helped': 150,  # Default fallback numbers
            'active_volunteers': 45,
            'success_rate': 85
        }
        return render_template(
            "homepage.html",
            stats=default_stats,
            success_stories=[]
        )


@main.route("/cases")
def show_cases():
    """Show all open cases with pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = 10

    try:
        # Get only OPEN cases
        query = Case.query.filter_by(status="OPEN").order_by(Case.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        db.session.commit()

        return render_template(
            "cases.html",
            cases=pagination.items,
            pagination=pagination,
            current_page=page,
            total_pages=pagination.pages,
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        flash("Database error occurred. Please try again.", "danger")
        return render_template(
            "cases.html", cases=[], pagination=None, current_page=1, total_pages=1
        )


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers
    r = 6371
    return c * r


@main.route("/advanced-search", methods=["GET"])
def advanced_search():
    """Advanced search endpoint with multiple filter criteria."""
    try:
        # Get all filter parameters
        filters = {
            "location": request.args.get("location"),
            "latitude": request.args.get("latitude", type=float),
            "longitude": request.args.get("longitude", type=float),
            "radius": request.args.get("radius", type=float, default=5.0),
            "status": request.args.get("status"),
            "needs": request.args.getlist("needs[]")
            or [],  # Default to empty list if no needs are selected
            "date_from": request.args.get("date_from"),
            "date_to": request.args.get("date_to"),
            "sort_by": request.args.get("sort_by", "created_at"),
            "sort_order": request.args.get("sort_order", "desc"),
        }

        page = request.args.get("page", 1, type=int)
        per_page = current_app.config.get("CASES_PER_PAGE", 10)

        # Start with base query
        query = Case.query

        # Apply filters
        if filters["location"]:
            query = query.filter(Case.location.ilike(f"%{filters['location']}%"))

        if filters["status"]:
            query = query.filter(Case.status == filters["status"].upper())

        if filters["needs"]:
            from sqlalchemy import or_

            # Use ANY operator which is more widely supported
            need_conditions = [Case.needs.any(need) for need in filters["needs"]]
            query = query.filter(or_(*need_conditions))

        if filters["date_from"]:
            date_from = datetime.strptime(filters["date_from"], "%Y-%m-%d")
            query = query.filter(Case.created_at >= date_from)

        if filters["date_to"]:
            date_to = datetime.strptime(filters["date_to"], "%Y-%m-%d")
            date_to = date_to + timedelta(days=1)
            query = query.filter(Case.created_at < date_to)

        # Location-based filtering - get cases with coordinates first
        if filters["latitude"] and filters["longitude"]:
            query = query.filter(Case.latitude.isnot(None), Case.longitude.isnot(None))

        # Apply sorting
        sort_column = getattr(Case, filters["sort_by"])
        if filters["sort_order"] == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Get all cases first (before pagination for distance filtering)
        all_cases = query.all()
        
        # Apply distance filtering if coordinates are provided
        if filters["latitude"] and filters["longitude"]:
            filtered_cases = []
            for case in all_cases:
                if case.latitude and case.longitude:
                    distance = haversine_distance(
                        filters["latitude"], filters["longitude"],
                        case.latitude, case.longitude
                    )
                    if distance <= filters["radius"]:
                        # Add distance attribute to case for display
                        case.distance = round(distance, 2)
                        filtered_cases.append(case)
            
            # Sort by distance if requested
            if filters["sort_by"] == "distance":
                filtered_cases.sort(
                    key=lambda x: x.distance,
                    reverse=(filters["sort_order"] == "desc")
                )
            
            # Manual pagination for filtered cases
            total_filtered = len(filtered_cases)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_cases = filtered_cases[start:end]
            
            # Create a mock pagination object
            class MockPagination:
                def __init__(self, items, page, per_page, total):
                    self.items = items
                    self.page = page
                    self.per_page = per_page
                    self.total = total
                    self.pages = (total + per_page - 1) // per_page
                    self.has_prev = page > 1
                    self.has_next = page < self.pages
                    self.prev_num = page - 1 if self.has_prev else None
                    self.next_num = page + 1 if self.has_next else None
            
            pagination = MockPagination(paginated_cases, page, per_page, total_filtered)
        else:
            # Regular pagination without distance filtering
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Log cases with null needs
        for case in pagination.items:
            if case.needs is None:
                current_app.logger.warning(f"Case {case.id} has null needs field.")

        # Get distinct locations
        locations = [loc[0] for loc in db.session.query(Case.location).distinct().all() if loc[0]]

        # Sort options
        sort_options = [
            ("created_at", "Creation Date"),
            ("updated_at", "Last Updated"),
            ("location", "Location"),
            ("status", "Status"),
        ]

        if filters["latitude"] and filters["longitude"]:
            sort_options.append(("distance", "Distance"))

        # Get saved searches for authenticated users
        saved_searches = []
        if current_user.is_authenticated:
            saved_searches = SavedSearch.query.filter_by(user_id=current_user.id).order_by(SavedSearch.created_at.desc()).all()

        return render_template(
            "advanced_search.html",
            cases=pagination.items if pagination else [],
            pagination=pagination,
            current_page=page,
            filters=filters,
            locations=locations,
            statuses=["OPEN", "RESOLVED"],
            sort_options=sort_options,
            saved_searches=saved_searches,
        )

    except Exception as e:
        current_app.logger.error(f"Search error: {str(e)}", exc_info=True)
        flash("An error occurred while searching. Please try again.", "error")
        return render_template(
            "advanced_search.html",
            cases=[],
            pagination=None,
            current_page=1,
            filters=filters,
            locations=[],
            statuses=["OPEN", "RESOLVED"],
            sort_options=[],
        )


@main.route("/resolve/<case_id>", methods=["GET", "POST"])
@login_required
def resolve_case(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        return_to = request.args.get("return_to") or request.form.get("return_to")

        if request.method == "POST":
            storage_service = StorageService()

            # Handle resolution photos using StorageService
            photos = request.files.getlist("photos[]")
            if photos and any(photo.filename for photo in photos):
                if not case.resolution_photos:
                    case.resolution_photos = []

                for photo in photos:
                    if photo.filename:
                        photo_url = storage_service.upload_file(photo, "resolution_photos")
                        if photo_url:
                            case.resolution_photos.append(photo_url)
                            current_app.logger.info(f"Added resolution photo: {photo_url}")

            # Handle resolution videos using StorageService
            videos = request.files.getlist("videos[]")
            if videos and any(video.filename for video in videos):
                if not case.resolution_videos:
                    case.resolution_videos = []

                for video in videos:
                    if video.filename:
                        video_url = storage_service.upload_file(video, "resolution_videos")
                        if video_url:
                            case.resolution_videos.append(video_url)
                            current_app.logger.info(f"Added resolution video: {video_url}")

            # Handle PDFs using StorageService
            pdfs = request.files.getlist("pdfs[]")
            if pdfs and any(pdf.filename for pdf in pdfs):
                if not case.pdfs:
                    case.pdfs = []

                for pdf in pdfs:
                    if pdf.filename and pdf.filename.lower().endswith(".pdf"):
                        pdf_url = storage_service.upload_file(pdf, "resolution_docs")
                        if pdf_url:
                            case.pdfs.append(pdf_url)
                            current_app.logger.info(f"Added resolution PDF: {pdf_url}")

            # Update case status and notes
            case.status = "RESOLVED"
            case.resolution_notes = request.form.get("resolution_notes")
            case.updated_at = datetime.utcnow()
            case.resolved_at = datetime.utcnow()  # Set resolved timestamp
            case.resolved_by_id = current_user.id

            db.session.commit()
            flash("Case resolved successfully!", "success")
            return redirect(return_to or url_for("main.show_cases"))

        return render_template(
            "resolve_case.html",
            case=case,
            case_id=case_id,
            message=None,
            success=True,
            return_to=return_to,
        )

    except Exception as e:
        logger.error(f"Error in resolve_case: {str(e)}", exc_info=True)
        db.session.rollback()
        flash("Error updating case", "error")
        return redirect(return_to or url_for("main.show_cases"))


@main.route("/resolved-cases")
@login_required
def show_resolved_cases():
    """Show resolved cases with pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = 10

    try:
        query = Case.query.filter_by(status="RESOLVED").order_by(Case.resolved_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        db.session.commit()

        return render_template(
            "resolved_cases.html",
            cases=pagination.items,
            pagination=pagination,
            current_page=page,
            total_pages=pagination.pages,
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        flash("Database error occurred. Please try again.", "danger")
        return render_template(
            "resolved_cases.html", cases=[], pagination=None, current_page=1, total_pages=1
        )


@main.route("/update/<case_id>", methods=["GET", "POST"])
@login_required
def update(case_id):
    case = Case.query.get_or_404(case_id)

    if request.method == "POST":
        try:
            storage_service = StorageService()

            # Update basic details
            case.location = request.form.get("location")
            case.latitude = request.form.get("latitude", type=float)
            case.longitude = request.form.get("longitude", type=float)
            case.needs = request.form.getlist("needs[]")
            case.status = request.form.get("status")

            # Ensure photos and videos arrays exist
            if case.photos is None:
                case.photos = []
            if case.videos is None:
                case.videos = []

            # Handle photos using StorageService
            photos = request.files.getlist("photos[]")
            for photo in photos:
                if photo and photo.filename:
                    photo_url = storage_service.upload_file(photo, "photos")
                    if photo_url:
                        # Append to existing photos
                        case.photos = case.photos + [photo_url]
                        current_app.logger.info(f"Added photo: {photo_url}")

            # Handle videos using StorageService
            videos = request.files.getlist("videos[]")
            for video in videos:
                if video and video.filename:
                    video_url = storage_service.upload_file(video, "videos")
                    if video_url:
                        # Append to existing videos
                        case.videos = case.videos + [video_url]
                        current_app.logger.info(f"Added video: {video_url}")

            # Log final state
            current_app.logger.info(f"Final photos: {case.photos}")
            current_app.logger.info(f"Final videos: {case.videos}")

            db.session.add(case)
            db.session.commit()

            return jsonify({"success": True, "message": "Case updated successfully"})

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating case: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    # GET request - render the update form
    return render_template("update_case.html", case=case)


@main.route("/remove_media/<case_id>", methods=["POST"])
@login_required
def remove_media(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        data = request.get_json()

        media_type = data.get("type")
        url = data.get("url")

        current_app.logger.info(f"Before removal - Photos: {case.photos}, Videos: {case.videos}")

        if media_type == "photo":
            if case.photos:
                case.photos = [p for p in case.photos if p != url]
        elif media_type == "video":
            if case.videos:
                case.videos = [v for v in case.videos if v != url]

        current_app.logger.info(f"After removal - Photos: {case.photos}, Videos: {case.videos}")

        db.session.add(case)  # Explicitly mark as modified
        db.session.commit()

        return jsonify({"success": True, "message": f"{media_type} removed successfully"})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing media: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@main.route("/delete_case/<case_id>", methods=["GET", "POST"])
@login_required
def delete(case_id):
    next_page = request.args.get("next") or request.form.get("next")
    if request.method == "GET":
        return render_template("delete.html", case_id=case_id)

    if request.method == "POST":
        try:
            case = Case.query.get_or_404(case_id)
            db.session.delete(case)
            db.session.commit()
            flash("Case deleted successfully!", "success")
            return redirect(next_page or url_for("main.show_cases"))
        except Exception as e:
            current_app.logger.error(f"Error deleting case: {e}")
            flash("Error deleting case", "error")
            return redirect(next_page or url_for("main.show_cases"))

    return render_template("delete.html", case_id=case_id)


@main.route("/case/<case_id>/details", methods=["GET", "POST"])
@login_required
def view_case_details(case_id):
    return_to = request.args.get("return_to") or request.form.get("return_to")
    case = Case.query.get_or_404(case_id)
    form = CommentForm()

    # app.logger.debug(f"Photos for case {case_id}: {case.photos}")

    if form.validate_on_submit():
        comment = Comment(content=form.content.data, case_id=case.id, user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash("Comment added successfully!", "success")
        # Redirect back to the same page but preserve the return URL
        return redirect(url_for("main.view_case_details", case_id=case_id, return_to=return_to))

    page = request.args.get("page", 1, type=int)
    comments = case.comments.order_by(Comment.created_at.desc()).paginate(
        page=page, per_page=5, error_out=False
    )

    return render_template(
        "case.html", case=case, comments=comments, form=form, return_to=return_to
    )


@main.route("/cases/status/<status>")  # Changed route path
def list_cases_by_status(status):  # Changed function name
    """API endpoint to view cases by status."""
    try:
        cases = Case.get_by_status(status)
        return jsonify([case.to_dict() for case in cases])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


# Saved Search Routes
@main.route("/api/saved-searches", methods=["GET"])
@login_required
def get_saved_searches():
    """Get all saved searches for the current user."""
    try:
        saved_searches = SavedSearch.query.filter_by(user_id=current_user.id).order_by(SavedSearch.created_at.desc()).all()
        return jsonify([search.to_dict() for search in saved_searches])
    except Exception as e:
        current_app.logger.error(f"Error getting saved searches: {e}")
        return jsonify({"error": "Failed to load saved searches"}), 500


@main.route("/api/saved-searches", methods=["POST"])
@login_required
def save_search():
    """Save a new search preference."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({"error": "Search name is required"}), 400
        
        # Check if name already exists for this user
        existing = SavedSearch.query.filter_by(user_id=current_user.id, name=data['name']).first()
        if existing:
            return jsonify({"error": "A search with this name already exists"}), 400
        
        # Create new saved search
        saved_search = SavedSearch(
            name=data['name'],
            location=data.get('location'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            radius=data.get('radius', 5.0),
            status=data.get('status'),
            needs=data.get('needs', []),
            date_from=datetime.strptime(data['date_from'], '%Y-%m-%d').date() if data.get('date_from') else None,
            date_to=datetime.strptime(data['date_to'], '%Y-%m-%d').date() if data.get('date_to') else None,
            sort_by=data.get('sort_by', 'created_at'),
            sort_order=data.get('sort_order', 'desc'),
            is_default=data.get('is_default', False),
            user_id=current_user.id
        )
        
        # If this is set as default, unset other defaults
        if saved_search.is_default:
            SavedSearch.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
        
        db.session.add(saved_search)
        db.session.commit()
        
        return jsonify({"message": "Search saved successfully", "search": saved_search.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving search: {e}")
        return jsonify({"error": "Failed to save search"}), 500


@main.route("/api/saved-searches/<int:search_id>", methods=["DELETE"])
@login_required
def delete_saved_search(search_id):
    """Delete a saved search."""
    try:
        saved_search = SavedSearch.query.filter_by(id=search_id, user_id=current_user.id).first()
        if not saved_search:
            return jsonify({"error": "Search not found"}), 404
        
        db.session.delete(saved_search)
        db.session.commit()
        
        return jsonify({"message": "Search deleted successfully"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting saved search: {e}")
        return jsonify({"error": "Failed to delete search"}), 500


@main.route("/api/saved-searches/<int:search_id>/load", methods=["GET"])
@login_required
def load_saved_search(search_id):
    """Load a saved search and redirect to advanced search with parameters."""
    try:
        saved_search = SavedSearch.query.filter_by(id=search_id, user_id=current_user.id).first()
        if not saved_search:
            flash("Search not found", "error")
            return redirect(url_for("main.advanced_search"))
        
        # Build query parameters from saved search
        params = {}
        if saved_search.location:
            params['location'] = saved_search.location
        if saved_search.latitude:
            params['latitude'] = saved_search.latitude
        if saved_search.longitude:
            params['longitude'] = saved_search.longitude
        if saved_search.radius:
            params['radius'] = saved_search.radius
        if saved_search.status:
            params['status'] = saved_search.status
        if saved_search.needs:
            params['needs[]'] = saved_search.needs
        if saved_search.date_from:
            params['date_from'] = saved_search.date_from.strftime('%Y-%m-%d')
        if saved_search.date_to:
            params['date_to'] = saved_search.date_to.strftime('%Y-%m-%d')
        if saved_search.sort_by:
            params['sort_by'] = saved_search.sort_by
        if saved_search.sort_order:
            params['sort_order'] = saved_search.sort_order
        
        return redirect(url_for("main.advanced_search", **params))
        
    except Exception as e:
        current_app.logger.error(f"Error loading saved search: {e}")
        flash("Failed to load saved search", "error")
        return redirect(url_for("main.advanced_search"))
