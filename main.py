import uuid
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for
from .sqlite_memory import initialize, create_case, delete_cat, select_cats_by_status, scan_case, resolve_case, seed, get_all_cases
from .view import prepare_cases_for_display

app = Flask(__name__)

# Initialize or seed the database as needed
db_path = 'cats.db'
initialize(db_path)

@app.route('/')
def index():
    open_cases = select_cats_by_status(db_path, 'OPEN')
    return render_template('index.html', open_cases=open_cases)

@app.route('/seed', methods=['GET', 'POST'])

def seed_database():
    if request.method == 'POST':
        seed(db_path)
        return redirect(url_for('index'))
    return render_template('seed.html') 

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
def show_cases(db_path):
    # Assume get_cases() fetches a list of case dictionaries
    cases = get_all_cases(db_path)  
    prepared_cases = prepare_cases_for_display(cases)
    return render_template('cases.html', cases=prepared_cases)

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


@app.route('/view/<status>', methods=['GET'])
def view_by_status(status):
    cases = select_cats_by_status(db_path, status.upper())  # Convert status to uppercase
    return render_template('view_cases.html', cases=cases, status=status)

if __name__ == '__main__':
    app.run(debug=True)
