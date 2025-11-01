from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends SimpleJWT to allow logging in with either username or email.
    Accepts any of: username, email, or login (alias).
    """

    def validate(self, attrs):
        User = get_user_model()
        username_field = self.username_field

        # Accept alternate field names
        login_value = attrs.get("login") or attrs.get("email") or attrs.get(username_field)

        if login_value and "@" in str(login_value):
            # Treat as email; map to username for downstream authentication
            user = User.objects.filter(email__iexact=login_value).only(User.USERNAME_FIELD).first()
            if user:
                attrs[username_field] = getattr(user, User.USERNAME_FIELD)
        elif login_value and username_field not in attrs:
            # If client sent "login" but not "username"
            attrs[username_field] = login_value

        return super().validate(attrs)

