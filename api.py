from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from . import db
from .models import Case, User

api = Blueprint('api', __name__, url_prefix='/api/v1')

@api.route('/login', methods=['POST'])
def login():
    """Login a user and return an access token"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({'access_token': access_token})

@api.route('/cases', methods=['GET'])
@jwt_required()
def get_cases():
    """Fetch all cases for the authenticated user"""
    user_id = get_jwt_identity()
    cases = Case.query.filter_by(user_id=user_id).all()
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

@api.route('/cases', methods=['POST'])
@jwt_required()
def create_case():
    """Create a new case for the authenticated user"""
    data = request.get_json()
    user_id = get_jwt_identity()

    new_case = Case(
        location=data.get("location"),
        status=data.get("status"),
        need=data.get("need"),
        photo=data.get("photo"),
        user_id=user_id
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

@api.route('/cases/<case_id>', methods=['PUT'])
@jwt_required()
def update_case(case_id):
    """Update an existing case by ID for the authenticated user"""
    data = request.get_json()
    user_id = get_jwt_identity()
    case = Case.query.filter_by(id=case_id, user_id=user_id).first()

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

@api.route('/cases/<case_id>', methods=['GET'])
@jwt_required()
def get_case_by_id(case_id):
    user_id = get_jwt_identity()
    case = Case.query.filter_by(id=case_id, user_id=user_id).first()
    
    if not case:
        return jsonify({"error": "Case not found"}), 404
        
    return jsonify({
        "id": case.id,
        "location": case.location,
        "status": case.status,
        "need": case.need,
        "photo": case.photo,
        "created_at": case.created_at,
        "updated_at": case.updated_at
    }), 200

@api.route('/cases/<string:case_id>/resolve', methods=['PUT'])
@jwt_required()
def resolve_case(case_id):
    user_id = get_jwt_identity()
    case = Case.query.filter_by(id=case_id, user_id=user_id).first()
    
    if not case:
        return jsonify({"error": "Case not found"}), 404
        
    data = request.get_json()
    case.status = "RESOLVED"
    case.resolution_notes = data.get('resolution_notes', '')
    
    db.session.commit()
    
    return jsonify({
        "message": "Case resolved successfully",
        "case": {
            "id": case.id,
            "status": case.status,
            "resolution_notes": case.resolution_notes,
            "updated_at": case.updated_at
        }
    }), 200

@api.route('/cases/<case_id>', methods=['DELETE'])
@jwt_required()
def delete_case(case_id):

    user_id = get_jwt_identity()
    case = Case.query.filter_by(id=case_id, user_id=user_id).first()
    
    if not case:
        return jsonify({"error": "Case not found"}), 404
        
    db.session.delete(case)
    db.session.commit()
    
    return jsonify({
        "message": "Case deleted successfully"
    }), 200

@api.route('/cases/search', methods=['GET'])
@jwt_required()
def search_cases():
    user_id = get_jwt_identity()
    query = Case.query.filter_by(user_id=user_id)
    
    # Apply filters
    if request.args.get('status'):
        query = query.filter(Case.status == request.args.get('status'))
    if request.args.get('location'):
        query = query.filter(Case.location.ilike(f"%{request.args.get('location')}%"))
    if request.args.get('need'):
        query = query.filter(Case.need == request.args.get('need'))
    if request.args.get('date_from'):
        query = query.filter(Case.created_at >= request.args.get('date_from'))
    if request.args.get('date_to'):
        query = query.filter(Case.created_at <= request.args.get('date_to'))
    
    cases = query.all()
    cases_data = [{
        "id": case.id,
        "location": case.location,
        "status": case.status,
        "need": case.need,
        "photo": case.photo,
        "created_at": case.created_at,
        "updated_at": case.updated_at
    } for case in cases]
    
    return jsonify(cases=cases_data), 200