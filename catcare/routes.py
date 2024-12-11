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


@main.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        try:
            photo = request.files.get('photo')
            if photo:
                # Create a secure filename
                filename = f"{str(uuid4())}_{secure_filename(photo.filename)}"
                
                # Get the absolute path to the upload directory
                basedir = os.path.abspath(os.path.dirname(__file__))
                upload_dir = os.path.join(basedir, 'static', 'uploads')
                
                # Ensure upload directory exists
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save the file
                filepath = os.path.join(upload_dir, filename)
                try:
                    photo.save(filepath)
                    current_app.logger.info(f"File saved successfully at {filepath}")
                except Exception as e:
                    current_app.logger.error(f"Failed to save file: {e}")
                    raise
            else:
                filename = None

            # Create new Case instance
            new_case = Case(
                id=str(uuid4()),
                photo=filename,
                location=request.form['location'],
                need=request.form['need'],
                status='OPEN',
                user_id=current_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_case)
            
            try:
                db.session.commit()
                flash('Case reported successfully!', 'success')
                return redirect(url_for('main.show_cases'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error creating case: {e}")
                flash('Error creating case. Please try again.', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Error creating case: {e}")
            flash('Error creating case. Please try again.', 'error')
    
    return render_template('report.html')


@main.route('/uploads/<filename>')
def uploaded_file(filename):
    basedir = os.path.abspath(os.path.dirname(__file__))
    upload_dir = os.path.join(basedir, 'static', 'uploads')
    return send_from_directory(upload_dir, filename)

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
def resolve_case(case_id):
    """Resolve a case by updating its status."""
    case = Case.query.get_or_404(case_id)
    success = False
    message = None
    
    if request.method == 'POST':
        try:
            new_status = request.form.get('status')
            if new_status in ['OPEN', 'RESOLVED']:
                case.status = new_status
                db.session.commit()
                message = f'Case with ID {case_id} has been updated to {new_status}.'
                success = True
            else:
                message = 'Invalid status provided.'
                success = False
        except Exception as e:
            db.session.rollback()
            message = f'Error updating case: {str(e)}'
            success = False
    
    return render_template(
        'resolve_case.html',
        case=case,
        case_id=case_id,
        message=message,
        success=success
    )

@main.route('/update/<case_id>', methods=['GET', 'POST'])
@login_required
def update(case_id):
    try:
        # Get the case or return 404
        case = Case.query.get_or_404(case_id)
        
        if request.method == 'POST':
            # Check if there is a file in the request
            file = request.files.get('photo')
            location = request.form.get('location')
            need = request.form.get('need')
            status = request.form.get('status')
            
            # Validate required fields (excluding photo, as it might be optional)
            if not all([location, need, status]):
                flash('Location, need, and status are required', 'error')
                return render_template('update_case.html', case=case)
            
            # Validate status
            if status not in ['OPEN', 'RESOLVED']:
                flash('Invalid status value', 'error')
                return render_template('update_case.html', case=case)
            
            try:
                # Update fields
                if file and file.filename:
                    # Save the file securely
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    case.photo = filename  # Update the photo field with the new filename
                
                case.location = location
                case.need = need
                case.status = status
                case.updated_at = datetime.utcnow()
                
                # Commit changes
                db.session.commit()
                
                flash('Case updated successfully!', 'success')
                return redirect(url_for('main.show_cases'))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error while updating case: {str(e)}")
                flash('Error updating case. Please try again.', 'error')
                return render_template('update_case.html', case=case)
        
        # GET request - show form
        return render_template('update_case.html', case=case)
        
    except Exception as e:
        current_app.logger.error(f"Error in update route: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('main.show_cases'))

@main.route('/delete_case/<case_id>', methods=['GET', 'POST'])
@login_required
def delete(case_id):
    if request.method == 'GET':
        return render_template('delete.html', case_id=case_id)
    
    if request.method == 'POST':
        if Case.delete_case(case_id):
            flash('Case deleted successfully!', 'success')
        else:
            flash('Case not found or could not be deleted.', 'danger')
        return redirect(url_for('main.show_cases'))

@main.route('/case/<case_id>/details', methods=['GET', 'POST'])
@login_required
def view_case_details(case_id):
    """View a single case and its comments, with a form to add a new comment."""
    case = Case.query.get_or_404(case_id)
    form = CommentForm()
    page = request.args.get('page', 1, type=int)
    
    comments = Comment.query.filter_by(case_id=case.id).order_by(Comment.created_at.desc()).paginate(page=page, per_page=5)

    
    if form.validate_on_submit():
        # Add a new comment
        comment = Comment(content=form.content.data, user_id=current_user.id, case_id=case.id)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('main.view_case_details', case_id=case.id))

    return render_template('case.html', case=case, comments=comments, form=form)

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
