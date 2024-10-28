import os
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, jsonify, flash, abort, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import NotFound
from flask import Blueprint
from flask_sqlalchemy import SQLAlchemy
from typing import Dict, Any
from .models import db, User, Comment, Case
from .forms import RegistrationForm, LoginForm, CommentForm
from . import db, login_manager

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Display open cases on the homepage."""
    try:
        open_cases = Case.query.filter_by(status='OPEN').all()
        return render_template('index.html', open_cases=open_cases)
    except Exception as e:
        flash(f'Error loading cases: {str(e)}', 'danger')
        return render_template('index.html', open_cases=[])
@main.route('/case/<case_id>', methods=['GET', 'POST'])
@login_required
def view_case(case_id):
    # Validate UUID format
    try:
        UUID(case_id)  # Validate UUID format
    except ValueError:
        raise NotFound("Invalid case ID format")
    
    case = Case.query.get_or_404(case_id)
    
    # Add some debug logging
    current_app.logger.debug(f"Looking up case with ID: {case_id}")
    
    if not case:
        current_app.logger.error(f"Case not found with ID: {case_id}")
        raise NotFound("Case not found")
        
    form = CommentForm()

    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data,
            case_id=case.id,
            user_id=current_user.id
        )
        db.session.add(comment)
        
        try:
            db.session.commit()
            flash('Comment added successfully!', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error adding comment: {e}")
            flash('Error adding comment. Please try again.', 'error')
        
        return redirect(url_for('main.view_case', case_id=case_id))

    # Paginate comments
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('COMMENTS_PER_PAGE', 10)
    
    comments = case.comments.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return render_template('case.html',
                         case=case,
                         form=form,
                         comments=comments)

@main.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user is authorized to edit the comment
    if comment.user_id != current_user.id:
        flash('You are not authorized to edit this comment.', 'error')
        return redirect(url_for('main.view_case', case_id=comment.case_id))
    
    form = CommentForm()
    
    if request.method == 'GET':
        form.content.data = comment.content
    
    elif form.validate_on_submit():
        comment.content = form.content.data
        try:
            db.session.commit()
            flash('Comment updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating comment: {e}")
            flash('Error updating comment. Please try again.', 'error')
        
        return redirect(url_for('main.view_case', case_id=comment.case_id))
    
    return render_template('edit_comment.html', form=form, comment=comment)

@main.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    # Check if user is authorized to delete the comment
    if comment.user_id != current_user.id:
        flash('You are not authorized to delete this comment.', 'error')
        return redirect(url_for('main.view_case', case_id=comment.case_id))
    
    try:
        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment: {e}")
        flash('Error deleting comment. Please try again.', 'error')
    
    return redirect(url_for('main.view_case', case_id=comment.case_id))
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
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('main.index'))
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
    return redirect(url_for('main.index'))

# Error handlers
@main.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@main.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@main.route('/report', methods=['GET', 'POST'])
@login_required  # Add this decorator to ensure only logged-in users can report
def report():
    if request.method == 'POST':
        try:
            # Create new Case instance using the SQLAlchemy model
            new_case = Case(
                id=str(uuid4()),
                photo=request.form['photo'],
                location=request.form['location'],
                need=request.form['need'],
                status='OPEN',
                user_id=current_user.id,  # Associate the case with the current user
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add to database session
            db.session.add(new_case)
            
            # Commit the transaction
            try:
                db.session.commit()
                flash('Case reported successfully!', 'success')
                return redirect(url_for('main.index'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error creating case: {e}")
                flash('Error creating case. Please try again.', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Error creating case: {e}")
            flash('Error creating case. Please try again.', 'error')
    
    return render_template('report.html')

@main.route('/cases')
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


@main.route('/search', methods=['GET', 'POST'])
def search():
    """Search for cases by location and status."""
    query = request.args.get('query', '')
    status = request.args.get('status', 'OPEN')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('CASES_PER_PAGE', 10)
    
    try:
        # Base query
        query_obj = Case.query
        
        # Apply filters if provided
        if query:
            query_obj = query_obj.filter(Case.location.ilike(f'%{query}%'))
        if status:
            query_obj = query_obj.filter(Case.status == status.upper())
            
        # Order by most recent first
        query_obj = query_obj.order_by(Case.created_at.desc())
        
        # Paginate results
        pagination = query_obj.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Get distinct locations for the dropdown
        locations = db.session.query(Case.location).distinct().all()
        locations = [loc[0] for loc in locations]
        
        return render_template('search.html',
                             cases=pagination.items,
                             pagination=pagination,
                             current_page=page,
                             total_pages=pagination.pages,
                             query=query,
                             status=status,
                             locations=locations)
                             
    except Exception as e:
        current_app.logger.error(f"Search error: {str(e)}")
        flash('An error occurred while searching. Please try again.', 'error')
        return render_template('search.html',
                             cases=[],
                             pagination=None,
                             current_page=1,
                             total_pages=1,
                             query=query,
                             status=status,
                             locations=[])
 
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
@main.route('/scan', methods=['GET', 'POST'])
def scan():
    """Search cases by location."""
    if request.method == 'POST':
        location = request.form['location']
        try:
            found = Case.get_by_location(location)
            return render_template('scan_results.html', found=found)
        except Exception as e:
            flash(f'Error scanning location: {str(e)}', 'danger')
            return render_template('scan_results.html', found=[])
    return render_template('scan.html')

@main.route('/resolve/<int:case_id>', methods=['GET', 'POST'])
@login_required
def resolve_case(case_id):
    case = Case.query.get(case_id)
    
    if request.method == 'GET':
        if not case:
            flash('Case not found', 'danger')
            return redirect(url_for('main.index'))
        return render_template('resolve_cases.html', case_id=case_id)
    
    if request.method == 'POST':
        # If case is found, resolve it
        if case:
            try:
                case.resolve()  # Call the resolve method
                flash('Case resolved successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error resolving case: {e}")
                flash('Error resolving case. Please try again.', 'danger')
            return render_template('resolve_cases.html', case_id=case_id, message='Case resolved', success=True)
        else:
            flash('Case not found', 'danger')
            return redirect(url_for('main.index'))


@main.route('/update/<case_id>', methods=['GET', 'POST'])
@login_required
def update(case_id):
    try:
        # Get the case or return 404
        case = Case.query.get_or_404(case_id)
        
        if request.method == 'POST':
            # Get form data
            photo = request.form.get('photo')
            location = request.form.get('location')
            need = request.form.get('need')
            status = request.form.get('status')
            
            # Validate required fields
            if not all([photo, location, need, status]):
                flash('All fields are required', 'error')
                return render_template('update_case.html', case=case)
            
            # Validate status
            if status not in ['OPEN', 'RESOLVED']:
                flash('Invalid status value', 'error')
                return render_template('update_case.html', case=case)
            
            try:
                # Update case
                case.photo = photo
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
        return redirect(url_for('main.index'))

@main.route('/case/<case_id>/details', methods=['GET'])  # Changed route path
def view_case_details(case_id):  # Changed function name
    """View a single case and its comments."""
    try:
        case = Case.query.get_or_404(case_id)
        return render_template('case.html', case=case)
    except Exception as e:
        flash(f'Error loading case: {str(e)}', 'danger')
        return redirect(url_for('main.show_cases'))

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

# def create_app():
#     init_db()
#     return main

# if __name__ == '__main__':
#     main = create_app()
#     main.run(debug=True)