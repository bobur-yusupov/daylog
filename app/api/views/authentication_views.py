from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiExample
from api.serializers.authentication_serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
)

User = get_user_model()


@extend_schema(
    summary="User Registration",
    description="Register a new user account and receive an authentication token.",
    tags=["Authentication"],
    examples=[
        OpenApiExample(
            "Registration Example",
            value={
                "username": "johndoe",
                "email": "john@example.com",
                "password1": "securepassword123",
                "password2": "securepassword123",
                "first_name": "John",
                "last_name": "Doe",
            },
            request_only=True,
        )
    ],
)
class RegisterAPIView(APIView):
    """
    API view for user registration.

    POST /api/auth/register/
    Body: {
        "username": "string",
        "email": "string",
        "password1": "string",
        "password2": "string",
        "first_name": "string" (optional),
        "last_name": "string" (optional)
    }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "message": "User registered successfully",
                    "user": {
                        "id": str(user.id),
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    },
                    "token": token.key,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    """
    API view for user login.

    POST /api/auth/login/
    Body: {
        "username": "string",
        "password": "string"
    }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                token, created = Token.objects.get_or_create(user=user)
                return Response(
                    {
                        "message": "Login successful",
                        "user": {
                            "id": str(user.id),
                            "username": user.username,
                            "email": user.email,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                        },
                        "token": token.key,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    """
    API view for user logout.

    POST /api/auth/logout/
    Headers: Authorization: Token <token>
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Delete the user's token to effectively log them out
            request.user.auth_token.delete()
            logout(request)
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response(
                {"error": "Token not found"}, status=status.HTTP_400_BAD_REQUEST
            )


# Create aliases for backward compatibility with function-based view naming
register_api = RegisterAPIView.as_view()
login_api = LoginAPIView.as_view()
logout_api = LogoutAPIView.as_view()
