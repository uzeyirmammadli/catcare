import uuid
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, jsonify
from .sqlite_memory import initialize, create_case, delete_cat, select_cats_by_status, scan_case, resolve_case, seed, get_all_cases, get_case_by_id, search_and_filter_cases
from .view import prepare_cases_for_display

app = Flask(__name__)

# Initialize or seed the database as 
print("Fetching records")
db_path = 'cats.db'
initialize(db_path)

@app.route('/')
def index():
    open_cases = select_cats_by_status(db_path, 'OPEN')
    print("sfsdgsdfg") 
    return render_template('index.html', open_cases=open_cases)

@app.route('/search')
def search():
    open_cases = select_cats_by_status(db_path, 'OPEN')
    return render_template('search.html', open_cases=open_cases) 


@app.route('/report', methods=['GET', 'POST'])
def report():
    print(request.form)
    if request.method == 'POST':
        report = {
            'id': str(uuid.uuid4()),  # Generate a unique ID
            'photo': request.form['photo'],
            'location': request.form['location'],
            'need': request.form['need'],
            'status': 'OPEN',  # Set initial status to OPEN
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        create_case(db_path, report)
        return redirect(url_for('index'))
    return render_template('report.html')

@app.route('/cases')
def show_cases():
    # Assume get_cases() fetches a list of case dictionaries

    #prepared_cases = prepare_cases_for_display(cases)
    # Example data fetching logic
    page = request.args.get('page', 1, type=int)
    cases = get_all_cases(db_path)  # Fetch your cases from the database or API
    total_cases = len(cases)
    per_page = 10  # Set how many cases to show per page
    total_pages = (total_cases + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_cases = cases[start:end]  # Get the cases for the current page

    return render_template('cases.html', cases=paginated_cases, current_page=page, total_pages=total_pages)


@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        location = request.form['location']
        found = scan_case(db_path, location)
        return render_template('scan_results.html', found=found)
    return render_template('scan.html')

@app.route('/resolve/<case_id>', methods=['GET','POST'])
def resolve(case_id):
    if request.method == 'GET':
        return render_template('resolve_cases.html', case_id=case_id)
    if request.method == 'POST':
        case_id = request.form['case_id']
        result = resolve_case(db_path, case_id)  # Assumes resolve_case returns something useful
        if result:
            message = 'Case resolved successfully.'
            return render_template('resolve_cases.html', message=message, success=True, case_id=case_id)
        else:
            message = 'Failed to resolve the case. Please check the case ID.'
            return render_template('resolve_cases.html', message=message, success=False, case_id=case_id)

    # Optional: Redirect to another page if accessed via GET or other non-POST method
    return redirect(url_for('index'))


@app.route('/delete/<case_id>', methods=['GET', 'POST'])
def delete(case_id):
    if request.method == 'GET':
        return render_template('delete.html', case_id=case_id)
    elif request.method == 'POST':
        # Handle case deletion logic (using delete_cat)
        case_id = request.form['case_id']
        delete_cat(db_path, case_id)
        return redirect(url_for('index'))  # Redirect back to index

@app.route('/case/<case_id>', methods=['GET'])  # Route with integer case ID capture
def view_case_by_id(case_id):
    case_data = get_case_by_id(db_path,case_id)  # Call the function from sqlite_memory.py
    if case_data:
         return render_template('case.html', case=case_data)  # Pass retrieved data to template
    else:
         return render_template('case.html', case=None, error_message="Case not found")

@app.route('/view/<status>', methods=['GET'])
def view_by_status(status):
    default_status = 'OPEN'  # Choose your preferred default value
    print(f"Received status: {status}")  # Optional for debugging
    status = status.upper() or default_status
    print(f"Using status: {status}")  # Optional for debugging
    try:
        cases = select_cats_by_status(db_path, status)
        # Process and return cases data (your existing logic)
        return jsonify(cases)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400  # Return error response with details and status cod


    # return render_template('view_cases.html', cases=cases, status=status)
@app.route('/case_list', methods=['GET'])
def case_list():
    search = request.args.get('search')
    location = request.args.get('location')
    status = request.args.get('status')
    need = request.args.get('need')
    created_at = request.args.get('created_at')

    # Fetch filtered and searched cases
    filtered_cases = search_and_filter_cases(db_path, search, location, status, need, created_at)
    return render_template('case_list.html', case_list=filtered_cases)
if __name__ == '__main__':
    app.run(debug=True)
