from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends SimpleJWT to allow logging in with either username or email.
    Accepts any of: username, email, or login (alias).
    """
    # Explicitly define the fields to accept
    username_field = get_user_model().USERNAME_FIELD # Use the actual username field from the User model
    email_field = 'email' # Assuming 'email' is the email field

    def validate(self, attrs):
        User = get_user_model()
        
        # Get the login value from various possible input fields
        login_value = attrs.get("login") or attrs.get(self.email_field) or attrs.get(self.username_field)

        if not login_value:
            raise serializers.ValidationError("Must provide 'username', 'email', or 'login'.")

        # Determine if login_value is an email
        if "@" in str(login_value):
            # Try to find user by email
            user = User.objects.filter(**{self.email_field: login_value}).first()
            if user:
                # If found, set the actual username field for SimpleJWT
                attrs[self.username_field] = getattr(user, self.username_field)
            else:
                # If no user found by email, let SimpleJWT handle the error
                # (e.g., by raising AuthenticationFailed)
                pass
        else:
            # Assume it's a username, let SimpleJWT handle it directly
            attrs[self.username_field] = login_value

        # Remove redundant fields before calling super().validate
        attrs.pop("login", None)
        attrs.pop(self.email_field, None) # Remove email if it was used as input

        return super().validate(attrs)

