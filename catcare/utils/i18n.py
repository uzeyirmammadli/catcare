"""
Internationalization utilities for the Cat Care application
"""

from flask_babel import gettext, ngettext, lazy_gettext

# Translation functions
_ = gettext
_l = lazy_gettext
_n = ngettext

# Common translations for the application
COMMON_TRANSLATIONS = {
    # Navigation
    'nav.home': _l('Home'),
    'nav.report': _l('Report Case'),
    'nav.search': _l('Search'),
    'nav.resolved': _l('Resolved Cases'),
    'nav.volunteer': _l('Volunteer'),
    'nav.admin': _l('Admin'),
    'nav.profile': _l('Profile'),
    'nav.login': _l('Login'),
    'nav.logout': _l('Logout'),
    'nav.register': _l('Register'),
    
    # Common actions
    'action.save': _l('Save'),
    'action.cancel': _l('Cancel'),
    'action.delete': _l('Delete'),
    'action.edit': _l('Edit'),
    'action.view': _l('View'),
    'action.submit': _l('Submit'),
    'action.search': _l('Search'),
    'action.filter': _l('Filter'),
    'action.reset': _l('Reset'),
    'action.back': _l('Back'),
    'action.next': _l('Next'),
    'action.previous': _l('Previous'),
    
    # Status
    'status.open': _l('Open'),
    'status.resolved': _l('Resolved'),
    'status.active': _l('Active'),
    'status.inactive': _l('Inactive'),
    'status.verified': _l('Verified'),
    'status.unverified': _l('Unverified'),
    
    # Roles
    'role.admin': _l('Admin'),
    'role.volunteer': _l('Volunteer'),
    'role.reporter': _l('Reporter'),
    
    # Case needs
    'need.medical': _l('Medical Care'),
    'need.food': _l('Food/Water'),
    'need.shelter': _l('Shelter'),
    'need.rescue': _l('Rescue'),
    'need.vaccination': _l('Vaccination'),
    'need.sterilization': _l('Sterilization'),
    
    # Messages
    'msg.success': _l('Success'),
    'msg.error': _l('Error'),
    'msg.warning': _l('Warning'),
    'msg.info': _l('Information'),
    'msg.loading': _l('Loading...'),
    'msg.no_data': _l('No data available'),
    'msg.confirm': _l('Are you sure?'),
    
    # Forms
    'form.username': _l('Username'),
    'form.email': _l('Email'),
    'form.password': _l('Password'),
    'form.confirm_password': _l('Confirm Password'),
    'form.first_name': _l('First Name'),
    'form.last_name': _l('Last Name'),
    'form.location': _l('Location'),
    'form.description': _l('Description'),
    'form.phone': _l('Phone'),
    'form.required': _l('Required'),
    'form.optional': _l('Optional'),
    
    # Time
    'time.today': _l('Today'),
    'time.yesterday': _l('Yesterday'),
    'time.days_ago': _l('days ago'),
    'time.hours_ago': _l('hours ago'),
    'time.minutes_ago': _l('minutes ago'),
    'time.just_now': _l('Just now'),
}

def get_translation(key, default=None):
    """Get translation for a key with fallback"""
    return COMMON_TRANSLATIONS.get(key, default or key)

def translate_role(role):
    """Translate user role"""
    role_map = {
        'ADMIN': get_translation('role.admin'),
        'VOLUNTEER': get_translation('role.volunteer'),
        'REPORTER': get_translation('role.reporter'),
    }
    return role_map.get(role, role)

def translate_status(status):
    """Translate case status"""
    status_map = {
        'OPEN': get_translation('status.open'),
        'RESOLVED': get_translation('status.resolved'),
    }
    return status_map.get(status, status)

def translate_need(need):
    """Translate case need"""
    need_map = {
        'medical': get_translation('need.medical'),
        'food': get_translation('need.food'),
        'shelter': get_translation('need.shelter'),
        'rescue': get_translation('need.rescue'),
        'vaccination': get_translation('need.vaccination'),
        'sterilization': get_translation('need.sterilization'),
    }
    return need_map.get(need, need.title())