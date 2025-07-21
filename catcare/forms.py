from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    login = StringField("Username or Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    show_password = BooleanField("Show Password")
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=6, message="Password must be at least 6 characters long"),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    role = StringField("Role", validators=[DataRequired()])
    show_password = BooleanField("Show Password")
    submit = SubmitField("Register")


class CommentForm(FlaskForm):
    content = TextAreaField(
        "Comment",
        validators=[
            DataRequired(message="Comment cannot be empty."),
            Length(min=1, max=1000, message="Comment must be between 1 and 1000 characters."),
        ],
    )
    submit = SubmitField("Post Comment")


class UpdateProfileForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)])
    first_name = StringField("First Name", validators=[Optional(), Length(max=50)])
    last_name = StringField("Last Name", validators=[Optional(), Length(max=50)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Update Profile")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(),
            Length(min=6),
            EqualTo("confirm_password", message="Passwords must match"),
        ],
    )
    confirm_password = PasswordField("Confirm New Password", validators=[DataRequired()])
    submit = SubmitField("Change Password")


class ResendVerificationForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Resend Verification Email")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "New Password",
        validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")]
    )
    submit = SubmitField("Reset Password")


class AdminUserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    first_name = StringField("First Name", validators=[Optional(), Length(max=50)])
    last_name = StringField("Last Name", validators=[Optional(), Length(max=50)])
    role = StringField("Role", validators=[DataRequired()])
    is_active = BooleanField("Active")
    is_verified = BooleanField("Verified")
    submit = SubmitField("Update User")
