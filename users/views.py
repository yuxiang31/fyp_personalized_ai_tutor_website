from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from .forms import CustomUserCreationForm, ProfileUpdateForm, CustomAuthenticationForm

# Create your views here.
def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST) # passing form information that submit through post method
        # , it will also perform validation such as check is there any same username that already being registered
        if form.is_valid():
            login(request, form.save()) # -> this code also return user value 
            return redirect("chat:index")
    else:
        # here will have two possibilities which is
        # 1. the user send the request using "GET" as first time registration
        # 2. the form is not valid that might not meet some of the rules
        form = CustomUserCreationForm()
        # 3. another possibility is that it might the username already exist
        #  ,it validate at line 8 and if not valid, it will proceed to here which the register form will be display again
    return render(request, 'users/register.html', {"form": form})

def login_view(request):
    if request.method == "POST":
        form = CustomAuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            # LOGIN HERE
            # form.get_user-> this code is to get user value 
            login(request, form.get_user()) # we can call get_user here is because we already validate the form in the previous line of code
            return redirect("chat:index")
    else:
        form = CustomAuthenticationForm(request=request)
    return render(request, 'users/login.html', {"form": form})

@login_required
def profile_view(request):
    # Show and update the current user's profile
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('users:profile')
        else:
            # If invalid, surface only detailed field errors via messages
            for field, errors in form.errors.items():
                # field == '__all__' indicates non-field errors
                label = form.fields[field].label if field in form.fields else 'Error'
                for err in errors:
                    messages.error(request, f"{label}: {err}")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'users/profile.html', {
        'form': form,
    })



