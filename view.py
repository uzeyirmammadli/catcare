import uuid
from datetime import datetime

#Entity
def build_report(r):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        'id': f'{str(uuid.uuid4())}',
        'photo': r['photo'],
        'location': r['area'],
        'need': r['need'],
        'status': 'OPEN',
        'created_at': current_time,
        'updated_at': current_time
    }    

# VIEW
def prepare_cases_for_display(cases):
    # This function remains the same as present, but now it prepares data for rendering in a template.
    prepared_cases = []
    for case in cases:
        prepared_case = f"ID: {case['id']} | Photo: {case['photo']} | Location: {case['location']} | Status: {case['status']} | Created_at: {case['created_at']} | Updated_at: {case['updated_at']}"
        prepared_cases.append(prepared_case)
    return prepared_cases
