import os
from uuid import  uuid4
from datetime import datetime, timedelta
import logging
from flask import request, render_template, redirect, url_for, jsonify, flash, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from flask import Blueprint, send_from_directory, send_file
from math import radians, cos, sin, asin, sqrt
from sqlalchemy import func
from flask_wtf.csrf import generate_csrf
from functools import wraps
from .models import db, User, Comment, Case
from .forms import RegistrationForm, LoginForm, CommentForm
from . import db, login_manager

if os.getenv('GAE_ENV', '').startswith('standard'):
    from google.cloud import storage

main = Blueprint('main', __name__)
logging.basicConfig(level=logging.DEBUG)

def csrf_protected(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "POST":
            csrf_token = request.headers.get('X-CSRFToken')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'CSRF token missing'}), 400
        return f(*args, **kwargs)
    return decorated_function
@main.route('/test')
def test_interface():
    return send_file('templates/test.html')

@main.route('/comment/<comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    # Get the comment by id
    comment = Comment.query.get(comment_id)
    
    # If the comment doesn't exist, redirect with an error message
    if not comment:
        flash("Comment not found.", "error")
        return redirect(url_for('view_case_details', case_id=comment.case_id))

    # Get updated data from the request
    content = request.form.get("content")
    case_id = request.form.get("case_id")  # Make sure this is provided in the request
    
    # Validate that the case exists in the database
    case = Case.query.get(case_id)
    if not case:
        flash("The referenced case does not exist.", "error")
        return redirect(url_for('main.view_case_details', case_id=comment.case_id))

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

    return redirect(url_for('main.view_case_details', case_id=comment.case_id))
 
@main.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user is authorized to delete the comment
    if comment.user_id != current_user.id:
        flash('You are not authorized to delete this comment.', 'error')
        return redirect(url_for('main.view_case_details', case_id=comment.case_id))
    
    try:
        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment: {e}")
        flash('Error deleting comment. Please try again.', 'error')
    
    return redirect(url_for('main.view_case_details', case_id=comment.case_id))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Authentication routes
@main.route('/register', methods=['GET', 'POST'])
def register():
    print(f"Method: {request.method}")
    print(f"User authenticated: {current_user.is_authenticated}")
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if request.method == 'POST':
        print(f"Form valid: {form.validate_on_submit()}")
        print(f"Form errors: {form.errors}")
        if form.validate_on_submit():
            try:
                # Check if user exists
                existing_user = User.query.filter_by(username=form.username.data).first()
                if existing_user:
                    flash('Username already exists. Please choose a different one.', 'error')
                    return render_template('register.html', form=form)
                
                # Create new user
                user = User(username=form.username.data)
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                flash('Registration successful!', 'success')
                return redirect(url_for('main.login'))
            except Exception as e:
                db.session.rollback()
                flash(f'Registration failed: {str(e)}', 'error')
                return render_template('register.html', form=form)
        else:
            # If form validation fails, render the template with errors
            return render_template('register.html', form=form)
    
    # GET request
    return render_template('register.html', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    print("LOG")
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('main.show_cases'))
            else:
                flash('Invalid username or password', 'error')
                return render_template('login.html', form=form)
        else:
            # If form validation fails, render the template with errors
            return render_template('login.html', form=form)
    
    # GET request
    return render_template('login.html', form=form)

@main.route('/check_users')
def check_users():
    users = User.query.all()
    return f"Number of users: {len(users)}"

@main.route('/logout')
@login_required
def logout():
    print("Logging out user")
    logout_user()
    print(f"User authenticated: {current_user.is_authenticated}")
    return redirect(url_for('main.show_cases'))

# Error handlers
@main.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@main.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


def upload_file(file):
    if not file:
        return None
        
    filename = f"{str(uuid4())}_{secure_filename(file.filename)}"
    
    if os.getenv('GAE_ENV', '').startswith('standard'):
        # Cloud environment: upload to Google Cloud Storage
        client = storage.Client()
        bucket = client.bucket('eco-layout-442118-t8-uploads')
        blob = bucket.blob(filename)
        
        # Rewind the file pointer to the beginning
        file.seek(0)
        
        # Upload the file
        blob.upload_from_file(file, content_type=file.content_type)
        
        # Return ONLY the Cloud Storage URL (no /uploads/ prefix)
        return f"https://storage.googleapis.com/eco-layout-442118-t8-uploads/{filename}"
    else:
        # Local environment: save to local filesystem
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return f"/uploads/{filename}"


@main.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        try:
            # Handle photos
            photos = request.files.getlist('photos[]')
            photo_urls = []
            
            # Handle videos
            videos = request.files.getlist('videos[]')
            video_urls = []
            
            #Handle location
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            
            # Upload photos
            for photo in photos:
                if photo and photo.filename:
                    if os.getenv('GAE_ENV', '').startswith('standard'):
                        filename = f"{str(uuid4())}_{secure_filename(photo.filename)}"
                        client = storage.Client()
                        bucket = client.bucket('eco-layout-442118-t8-uploads')
                        blob = bucket.blob(f"photos/{filename}")
                        photo.seek(0)
                        blob.upload_from_file(photo, content_type=photo.content_type)
                        photo_urls.append(f"https://storage.googleapis.com/eco-layout-442118-t8-uploads/photos/{filename}")
                    else:
                        filename = secure_filename(photo.filename)
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'photos', filename)
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        photo.save(filepath)
                        photo_urls.append(f"/uploads/photos/{filename}")

            # Upload videos
            for video in videos:
                if video and video.filename:
                    if os.getenv('GAE_ENV', '').startswith('standard'):
                        filename = f"{str(uuid4())}_{secure_filename(video.filename)}"
                        client = storage.Client()
                        bucket = client.bucket('eco-layout-442118-t8-uploads')
                        blob = bucket.blob(f"videos/{filename}")
                        video.seek(0)
                        blob.upload_from_file(video, content_type=video.content_type)
                        video_urls.append(f"https://storage.googleapis.com/eco-layout-442118-t8-uploads/videos/{filename}")
                    else:
                        filename = secure_filename(video.filename)
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'videos', filename)
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        video.save(filepath)
                        video_urls.append(f"/uploads/videos/{filename}")

            new_case = Case(
                id=str(uuid4()),
                photos=photo_urls,
                videos=video_urls,
                location=request.form['location'],
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                needs=request.form.getlist('needs[]'),
                status='OPEN',
                user_id=current_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_case)
            db.session.commit()
            flash('Case reported successfully!', 'success')
            return redirect(url_for('main.show_cases'))
            
        except Exception as e:
            current_app.logger.error(f"Error creating case: {e}")
            flash('Error creating case. Please try again.', 'error')
            
    return render_template('report.html')


# Update the uploaded_file route to handle both environments
# @main.route('/uploads/<path:filename>')
# def uploaded_file(filename):
#     if filename.startswith('https://'):
#         return redirect(filename)
#     elif os.getenv('GAE_ENV', '').startswith('standard'):
#         return redirect(f"https://storage.googleapis.com/eco-layout-442118-t8-uploads/{filename}")
#     return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
@main.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main.route('/')
def show_cases():
    """Show all cases with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    try:
        # Get paginated cases
        pagination = Case.query.order_by(Case.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False)
        
        return render_template('cases.html',
                             cases=pagination.items,
                             pagination=pagination,
                             current_page=page,
                             total_pages=pagination.pages)
    except Exception as e:
        flash(f'Error loading cases: {str(e)}', 'danger')
        return render_template('cases.html', 
                             cases=[],
                             pagination=None,
                             current_page=1,
                             total_pages=1)
 
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
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers
    r = 6371
    return c * r

@main.route('/advanced-search', methods=['GET'])
def advanced_search():
    """Advanced search endpoint with multiple filter criteria."""
    # Get all filter parameters
    filters = {
        'location': request.args.get('location'),
        'latitude': request.args.get('latitude', type=float),
        'longitude': request.args.get('longitude', type=float),
        'radius': request.args.get('radius', type=float, default=5.0),  # Default 5km radius
        'status': request.args.get('status'),
        'needs': request.args.getlist('needs[]'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'sort_by': request.args.get('sort_by', 'created_at'),
        'sort_order': request.args.get('sort_order', 'desc')
    }
    
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('CASES_PER_PAGE', 10)
    
    try:
        # Start with base query
        query = Case.query
        
        # Apply filters
        if filters['location']:
            query = query.filter(Case.location.ilike(f"%{filters['location']}%"))
        
        # Location-based search with Haversine distance
        if filters['latitude'] and filters['longitude']:
            # First, get all cases
            cases = query.all()
            
            # Calculate distances and filter within radius
            filtered_cases = []
            for case in cases:
                if case.latitude and case.longitude:  # Ensure case has coordinates
                    distance = haversine_distance(
                        filters['latitude'], 
                        filters['longitude'],
                        case.latitude, 
                        case.longitude
                    )
                    if distance <= filters['radius']:
                        # Create a dictionary of case attributes including the distance
                        case_dict = case.__dict__.copy()
                        case_dict['distance'] = round(distance, 2)
                        filtered_cases.append(case_dict)
            
            # Sort by distance if requested
            if filters['sort_by'] == 'distance':
                filtered_cases.sort(
                    key=lambda x: x.distance,
                    reverse=(filters['sort_order'] == 'desc')
                )
            else:
                # Apply other sorting
                filtered_cases.sort(
                    key=lambda x: getattr(x, filters['sort_by']),
                    reverse=(filters['sort_order'] == 'desc')
                )
            
            # Manual pagination
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_cases = filtered_cases[start_idx:end_idx]
            
            # Create a simple pagination object
            class SimplePagination:
                def __init__(self, items, total, page, per_page):
                    self.items = items
                    self.total = total
                    self.page = page
                    self.per_page = per_page
                    self.pages = (total + per_page - 1) // per_page
            
            pagination = SimplePagination(
                paginated_cases,
                len(filtered_cases),
                page,
                per_page
            )
            
        else:
            # Apply regular filters without location search
            if filters['status']:
                query = query.filter(Case.status == filters['status'].upper())
            
            if filters['needs']:
                query = query.filter(Case.needs.overlap(filters['needs']))
            
            if filters['date_from']:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d')
                query = query.filter(Case.created_at >= date_from)
            
            if filters['date_to']:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d')
                date_to = date_to + timedelta(days=1)
                query = query.filter(Case.created_at < date_to)
            
            # Apply sorting
            sort_column = getattr(Case, filters['sort_by'])
            if filters['sort_order'] == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
            
            # Regular pagination
            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        
        # Get distinct values for dropdowns
        locations = db.session.query(Case.location).distinct().all()
        
        # Update sort options to include distance
        sort_options = [
            ('created_at', 'Creation Date'),
            ('updated_at', 'Last Updated'),
            ('location', 'Location'),
            ('status', 'Status')
        ]
        if filters['latitude'] and filters['longitude']:
            sort_options.append(('distance', 'Distance'))
        
        # Prepare template data
        template_data = {
            'cases': pagination.items,
            'pagination': pagination,
            'current_page': page,
            'total_pages': pagination.pages,
            'filters': filters,
            'locations': [loc[0] for loc in locations],
            'statuses': ['OPEN', 'RESOLVED'],
            'sort_options': sort_options
        }
        
        return render_template('advanced_search.html', **template_data)
    
    except Exception as e:
        current_app.logger.error(f"Search error: {str(e)}")
        flash('An error occurred while searching. Please try again.', 'error')
        return render_template('advanced_search.html',
                           cases=[],
                           pagination=None,
                           current_page=1,
                           total_pages=1,
                           filters=filters,
                           locations=[],
                           statuses=['OPEN', 'RESOLVED'],
                           sort_options=[])

@main.route('/resolve/<case_id>', methods=['GET', 'POST'])
@login_required
def resolve_case(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        return_to = request.args.get('return_to') or request.form.get('return_to')
        
        if request.method == 'POST':
            case.status = request.form.get('status')
            case.resolution_notes = request.form.get('resolution_notes')
            case.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Case updated successfully!', 'success')
            return redirect(return_to or url_for('main.show_cases'))
            
        return render_template('resolve_case.html', 
                             case=case,
                             case_id=case_id,
                             message=None,
                             success=True,
                             return_to=return_to)
        
    except Exception as e:
        current_app.logger.error(f"Error resolving case: {e}")
        flash('Error updating case', 'error')
        return redirect(return_to or url_for('main.show_cases'))
    
@main.route('/update/<case_id>', methods=['GET', 'POST'])
@login_required
@csrf_protected
def update(case_id):
    if request.method == 'POST':
        try:
            case = Case.query.get_or_404(case_id)
            
            # Handle basic info
            case.location = request.form.get('location')
            case.latitude = float(request.form.get('latitude')) if request.form.get('latitude') else None
            case.longitude = float(request.form.get('longitude')) if request.form.get('longitude') else None
            case.needs = request.form.getlist('needs[]')
            case.status = request.form.get('status')
            case.updated_at = datetime.utcnow()
            
            # Filter out non-existent photos first
            if case.photos:
                current_photos = []
                for photo_url in case.photos:
                    file_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'],
                        photo_url.replace('/uploads/', '')
                    )
                    if os.path.exists(file_path):
                        current_photos.append(photo_url)
                case.photos = current_photos
            
            # Filter out non-existent videos
            if case.videos:
                current_videos = []
                for video_url in case.videos:
                    file_path = os.path.join(
                        current_app.config['UPLOAD_FOLDER'],
                        video_url.replace('/uploads/', '')
                    )
                    if os.path.exists(file_path):
                        current_videos.append(video_url)
                case.videos = current_videos
            
            # Handle new photos
            if request.files.getlist('photos[]'):
                if case.photos is None:
                    case.photos = []
                    
                for photo in request.files.getlist('photos[]'):
                    if photo and photo.filename:
                        try:
                            filename = f"{str(uuid4())}_{secure_filename(photo.filename)}"
                            photos_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'photos')
                            os.makedirs(photos_folder, exist_ok=True)
                            filepath = os.path.join(photos_folder, filename)
                            photo.save(filepath)
                            photo_url = f"/uploads/photos/{filename}"
                            case.photos.append(photo_url)
                            current_app.logger.info(f"Added photo: {photo_url}")
                        except Exception as e:
                            current_app.logger.error(f"Error saving photo: {str(e)}")
            
            # Handle new videos
            if request.files.getlist('videos[]'):
                if case.videos is None:
                    case.videos = []
                    
                for video in request.files.getlist('videos[]'):
                    if video and video.filename:
                        try:
                            filename = f"{str(uuid4())}_{secure_filename(video.filename)}"
                            videos_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'videos')
                            os.makedirs(videos_folder, exist_ok=True)
                            filepath = os.path.join(videos_folder, filename)
                            video.save(filepath)
                            video_url = f"/uploads/videos/{filename}"
                            case.videos.append(video_url)
                            current_app.logger.info(f"Added video: {video_url}")
                        except Exception as e:
                            current_app.logger.error(f"Error saving video: {str(e)}")
            
            try:
                current_app.logger.info(f"Final photos list: {case.photos}")
                current_app.logger.info(f"Final videos list: {case.videos}")
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Case updated successfully'
                })
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
                
        except Exception as e:
            current_app.logger.error(f"Error in update route: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # GET request
    case = Case.query.get_or_404(case_id)
    
    # Filter out non-existent media before rendering template
    if case.photos:
        case.photos = [photo for photo in case.photos if os.path.exists(
            os.path.join(current_app.config['UPLOAD_FOLDER'], photo.replace('/uploads/', ''))
        )]
    if case.videos:
        case.videos = [video for video in case.videos if os.path.exists(
            os.path.join(current_app.config['UPLOAD_FOLDER'], video.replace('/uploads/', ''))
        )]
    
    return render_template('update_case.html', case=case)

@main.route('/remove_media/<case_id>', methods=['POST'])
@login_required
def remove_media(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        data = request.get_json()
        
        if not data or 'type' not in data or 'url' not in data:
            current_app.logger.error("Invalid request data")
            return jsonify({
                'success': False,
                'error': 'Invalid request data'
            }), 400
            
        media_type = data['type']
        url = data['url']
        current_app.logger.info(f"Removing {media_type}: {url}")
        
        try:
            # Remove file from filesystem
            file_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                url.replace('/uploads/', '')
            )
            if os.path.exists(file_path):
                os.remove(file_path)
                current_app.logger.info(f"Deleted file: {file_path}")
            
            # Update database
            if media_type == 'photo':
                if case.photos and url in case.photos:
                    case.photos.remove(url)
                    current_app.logger.info("Removed photo URL from database")
            elif media_type == 'video':
                if case.videos and url in case.videos:
                    case.videos.remove(url)
                    current_app.logger.info("Removed video URL from database")
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid media type'
                }), 400
            
            db.session.commit()
            current_app.logger.info("Changes committed to database")
            
            return jsonify({
                'success': True,
                'message': f'{media_type.capitalize()} removed successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error removing {media_type}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Failed to remove {media_type}'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in remove_media route: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Add this context processor to make csrf_token available in all templates
@main.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)


@main.route('/delete_case/<case_id>', methods=['GET', 'POST'])
@login_required
def delete(case_id):
    next_page = request.args.get('next') or request.form.get('next')
    if request.method == 'GET':
        return render_template('delete.html', case_id=case_id)
    
    if request.method == 'POST':
        try:
            case = Case.query.get_or_404(case_id)
            db.session.delete(case)
            db.session.commit()
            flash('Case deleted successfully!', 'success')
            return redirect(next_page or url_for('main.show_cases'))
        except Exception as e:
            current_app.logger.error(f"Error deleting case: {e}")
            flash('Error deleting case', 'error')
            return redirect(next_page or url_for('main.show_cases'))
            
    return render_template('delete.html', case_id=case_id)

@main.route('/case/<case_id>/details', methods=['GET', 'POST'])
@login_required
def view_case_details(case_id):
    return_to = request.args.get('return_to') or request.form.get('return_to')
    case = Case.query.get_or_404(case_id)
    form = CommentForm()
    
    if form.validate_on_submit():
        comment = Comment(content=form.content.data,
                        case_id=case.id,
                        user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
        # Redirect back to the same page but preserve the return URL
        return redirect(url_for('main.view_case_details', case_id=case_id, return_to=return_to))
    
    page = request.args.get('page', 1, type=int)
    comments = case.comments.order_by(Comment.created_at.desc()).paginate(
        page=page, per_page=5, error_out=False)
    
    return render_template('case.html', 
                         case=case, 
                         comments=comments, 
                         form=form,
                         return_to=return_to)

@main.route('/cases/status/<status>')  # Changed route path
def list_cases_by_status(status):  # Changed function name
    """API endpoint to view cases by status."""
    try:
        cases = Case.get_by_status(status)
        return jsonify([case.to_dict() for case in cases])
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500
