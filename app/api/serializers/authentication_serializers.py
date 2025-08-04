from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """

    password1 = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        )
        extra_kwargs = {
            "email": {"required": True},
        }

    def validate(self, attrs):
        """
        Validate that the two password fields match.
        """
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        """
        Create a new user with encrypted password.
        """
        validated_data.pop("password2")
        password = validated_data.pop("password1")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user details.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "last_login",
        )
        read_only_fields = ("id", "date_joined", "last_login")
