import os
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, jsonify, flash, abort, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import NotFound
from flask import Blueprint
from typing import Dict, Any
from .models import db, User, Comment, Case
from .forms import RegistrationForm, LoginForm, CommentForm
from .sqlite_memory import (
    initialize, create_case, delete_cat, select_cats_by_status,
    scan_case, resolve_case, seed, get_all_cases, get_case_by_id
)
from .view import prepare_cases_for_display
from . import db, login_manager

main = Blueprint('main', __name__)

@main.route('/')
def index():
    open_cases = select_cats_by_status(current_app.config['DATABASE_PATH'], 'OPEN')
    return render_template('index.html', open_cases=open_cases)
        
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

@main.route('/search')
def search():
    open_cases = select_cats_by_status(current_app.config['DATABASE_PATH'], 'OPEN')
    return render_template('search.html', open_cases=open_cases) 

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
    page = request.args.get('page', 1, type=int)
    cases = get_all_cases(current_app.config['DATABASE_PATH'])
    total_cases = len(cases)
    per_page = 10  # Set how many cases to show per page
    total_pages = (total_cases + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_cases = cases[start:end]  # Get the cases for the current page

    return render_template('cases.html', cases=paginated_cases, current_page=page, total_pages=total_pages)

@main.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        location = request.form['location']
        found = scan_case(current_app.config['DATABASE_PATH'], location)
        return render_template('scan_results.html', found=found)
    return render_template('scan.html')

@main.route('/resolve/<case_id>', methods=['GET','POST'])
def resolve(case_id):
    if request.method == 'GET':
        return render_template('resolve_cases.html', case_id=case_id)
    if request.method == 'POST':
        case_id = request.form['case_id']
        result = resolve_case(current_app.config['DATABASE_PATH'], case_id)
        if result:
            message = 'Case resolved successfully.'
            flash(message, 'success')
            return render_template('resolve_cases.html', message=message, success=True, case_id=case_id)
        else:
            message = 'Failed to resolve the case. Please check the case ID.'
            flash(message, 'danger')
            return render_template('resolve_cases.html', message=message, success=False, case_id=case_id)

    return redirect(url_for('main.index'))

@main.route('/delete/<case_id>', methods=['GET', 'POST'])
def delete(case_id):
    if request.method == 'GET':
        return render_template('delete.html', case_id=case_id)
    elif request.method == 'POST':
        delete_cat(current_app.config['DATABASE_PATH'], case_id)
        flash('Case deleted successfully!', 'success')
        return redirect(url_for('main.index'))

# @main.route('/case/<case_id>', methods=['GET'])
# def view_case_by_id(case_id):
#     case_data = get_case_by_id(current_app.config['DATABASE_PATH'], case_id)
#     if case_data:
#         return render_template('case.html', case=case_data)
#     else:
#         return render_template('case.html', case=None, error_message="Case not found")

@main.route('/view/<status>', methods=['GET'])
def view_by_status(status):
    default_status = 'OPEN'  
    status = status.upper() or default_status  # Ensure status is uppercase
    try:
        cases = select_cats_by_status(main.config['DATABASE_PATH'], status)
        return jsonify(cases)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# def create_app():
#     init_db()
#     return main

# if __name__ == '__main__':
#     main = create_app()
#     main.run(debug=True)