from django.shortcuts import render, redirect


# Create your views here.
def dashboard(request):
    """
    Dashboard view for authenticated users.
    """
    if not request.user.is_authenticated:
        return redirect("authentication:login")

    return render(request, "journal/dashboard.html", {"user": request.user})
