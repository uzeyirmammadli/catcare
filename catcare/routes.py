import os
from uuid import  uuid4
from datetime import datetime, timedelta
import logging
from flask import request, render_template, redirect, url_for, jsonify, flash, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from flask import Blueprint, send_from_directory, send_file
from .models import db, User, Comment, Case
from .forms import RegistrationForm, LoginForm, CommentForm
from . import db, login_manager

if os.getenv('GAE_ENV', '').startswith('standard'):
    from google.cloud import storage

main = Blueprint('main', __name__)
logging.basicConfig(level=logging.DEBUG)

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

@main.route('/case/<case_id>/remove_media', methods=['POST'])
@login_required
def remove_media(case_id):
    try:
        case = Case.query.get_or_404(case_id)
        data = request.get_json()
        media_type = data.get('type')
        url = data.get('url')
        
        if media_type == 'photo':
            # Handle both old and new format
            if case.photos is None:
                case.photos = []
            if url in case.photos:
                case.photos.remove(url)
            if case.photo == url:
                case.photo = None
        elif media_type == 'video':
            if case.videos is None:
                case.videos = []
            if url in case.videos:
                case.videos.remove(url)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Error removing media: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Update the uploaded_file route to handle both environments
@main.route('/uploads/<path:filename>')
def uploaded_file(filename):
    if filename.startswith('https://'):
        return redirect(filename)
    elif os.getenv('GAE_ENV', '').startswith('standard'):
        return redirect(f"https://storage.googleapis.com/eco-layout-442118-t8-uploads/{filename}")
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
 
@main.route('/advanced-search', methods=['GET'])
def advanced_search():
    """Advanced search endpoint with multiple filter criteria."""
    # Get all filter parameters
    filters = {
        'location': request.args.get('location'),
        'status': request.args.get('status'),
        'need': request.args.get('need'),
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
        
        if filters['status']:
            query = query.filter(Case.status == filters['status'].upper())
            
        if filters['need']:
            query = query.filter(Case.need.ilike(f"%{filters['need']}%"))
        
        # Date range filtering
        if filters['date_from']:
            date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d')
            query = query.filter(Case.created_at >= date_from)
            
        if filters['date_to']:
            date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d')
            # Add one day to include the entire end date
            date_to = date_to + timedelta(days=1)
            query = query.filter(Case.created_at < date_to)
        
        # Apply sorting
        sort_column = getattr(Case, filters['sort_by'])
        if filters['sort_order'] == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Execute query with pagination
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Get distinct values for dropdowns
        locations = db.session.query(Case.location).distinct().all()
        needs = db.session.query(Case.need).distinct().all()
        
        # Prepare data for template
        template_data = {
            'cases': pagination.items,
            'pagination': pagination,
            'current_page': page,
            'total_pages': pagination.pages,
            'filters': filters,
            'locations': [loc[0] for loc in locations],
            'needs': [need[0] for need in needs],
            'statuses': ['OPEN', 'RESOLVED'],
            'sort_options': [
                ('created_at', 'Creation Date'),
                ('updated_at', 'Last Updated'),
                ('location', 'Location'),
                ('status', 'Status')
            ]
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
                             needs=[],
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
def update(case_id):
    
    try:
        case = Case.query.get_or_404(case_id)
        next_page = request.args.get('next') or request.form.get('next')
        
        if request.method == 'POST':
            # Migrate old format to new format
            case.migrate_old_format()
            
            location = request.form.get('location')
            lat = request.form.get('latitude')
            lon = request.form.get('longitude')
            needs = request.form.getlist('needs[]')
            status = request.form.get('status')
            
            if not location or not status:
                flash('Location and status are required', 'error')
                return render_template('update_case.html', case=case)
            
            # Handle new photos
            if request.files.getlist('photos[]'):
                for photo in request.files.getlist('photos[]'):
                    if photo and photo.filename:
                        filename = f"{str(uuid4())}_{secure_filename(photo.filename)}"
                        
                        if os.getenv('GAE_ENV', '').startswith('standard'):
                            client = storage.Client()
                            bucket = client.bucket('eco-layout-442118-t8-uploads')
                            blob = bucket.blob(f"photos/{filename}")
                            photo.seek(0)
                            blob.upload_from_file(photo, content_type=photo.content_type)
                            photo_url = f"https://storage.googleapis.com/eco-layout-442118-t8-uploads/photos/{filename}"
                        else:
                            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'photos', filename)
                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                            photo.save(filepath)
                            photo_url = f"/uploads/photos/{filename}"
                        
                        if case.photos is None:
                            case.photos = []
                        case.photos.append(photo_url)
            
            # Handle new videos (similar to photos)
            if request.files.getlist('videos[]'):
                for video in request.files.getlist('videos[]'):
                    if video and video.filename:
                        filename = f"{str(uuid4())}_{secure_filename(video.filename)}"
                        
                        if os.getenv('GAE_ENV', '').startswith('standard'):
                            client = storage.Client()
                            bucket = client.bucket('eco-layout-442118-t8-uploads')
                            blob = bucket.blob(f"videos/{filename}")
                            video.seek(0)
                            blob.upload_from_file(video, content_type=video.content_type)
                            video_url = f"https://storage.googleapis.com/eco-layout-442118-t8-uploads/videos/{filename}"
                        else:
                            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'videos', filename)
                            os.makedirs(os.path.dirname(filepath), exist_ok=True)
                            video.save(filepath)
                            video_url = f"/uploads/videos/{filename}"
                        
                        if case.videos is None:
                            case.videos = []
                        case.videos.append(video_url)
            
            case.location = location
            case.latitude = float(lat) if lat else None
            case.longitude = float(lon) if lon else None
            case.needs = needs
            case.status = status
            case.updated_at = datetime.utcnow()
            
            try:
                db.session.commit()
                flash('Case updated successfully!', 'success')
                return jsonify({'success': True})
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error while updating case: {str(e)}")
                return jsonify({'success': False, 'error': str(e)}), 500
                
        return render_template('update_case.html', case=case, next=next_page)
        
    except Exception as e:
        current_app.logger.error(f"Error in update route: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
