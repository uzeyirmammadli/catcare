# api.py
from flask import Blueprint, jsonify, request, abort
from . import db  
from .models import Case  

api = Blueprint('api', __name__, url_prefix='/api/v1')

@api.route('/cases', methods=['GET'])
def get_cases():
    """Fetch all cases"""
    cases = Case.query.all()
    cases_data = [
        {
            "id": case.id,
            "location": case.location,
            "status": case.status,
            "need": case.need,
            "photo": case.photo,
            "created_at": case.created_at,
            "updated_at": case.updated_at
        }
        for case in cases
    ]
    return jsonify(cases=cases_data), 200

@api.route('/api/v1/cases', methods=['POST'])
def create_case():
    """Create a new case."""
    if request.method == 'POST':
        data = request.get_json()

        # Check if user_id is provided in the request
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        new_case = Case(
            location=data.get("location"),
            status=data.get("status"),
            need=data.get("need"),
            photo=data.get("photo"),
            user_id=user_id  # Set the user_id here
        )

        db.session.add(new_case)
        db.session.commit()

        return jsonify({
            "id": new_case.id,
            "location": new_case.location,
            "status": new_case.status,
            "need": new_case.need,
            "photo": new_case.photo,
            "user_id": new_case.user_id
        }), 201


@api.route('/cases/<int:case_id>', methods=['PUT'])
def update_case(case_id):
    """Update an existing case by ID"""
    data = request.json
    case = Case.query.get(case_id)
    
    if not case:
        return jsonify({"error": "Case not found"}), 404

    if "location" in data:
        case.location = data['location']
    if "status" in data:
        case.status = data['status']
    if "need" in data:
        case.need = data['need']
    if "photo" in data:
        case.photo = data['photo']
    
    db.session.commit()

    return jsonify({
        "message": "Case updated successfully",
        "case": {
            "id": case.id,
            "location": case.location,
            "status": case.status,
            "need": case.need,
            "photo": case.photo,
            "updated_at": case.updated_at
        }
    }), 200
