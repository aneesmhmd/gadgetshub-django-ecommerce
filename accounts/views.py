from django.shortcuts import render, redirect, HttpResponseRedirect
from django.http import HttpResponse
from .forms import RegistrationForm, UserAddressForm
from .models import Account, Address
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.urls import reverse

# verification
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage

# Create your views here.
    
def login(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            auth.login(request, user)
            print(request.path_info)
            return HttpResponseRedirect(request.path_info)

        else:
            messages.error(request, 'Invalid login credentials')
            return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/login.html')



@login_required
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out')
    return redirect(login)



def signup(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split("@")[0]
            user = Account.objects.create_user(
                first_name=first_name, last_name=last_name, email=email, username=username, password=password)
            user.phone_number = phone_number
            user.save()

            # user activation
            current_site = get_current_site(request)
            mail_subject = 'Please activate your account'
            message = render_to_string('accounts/account_verification.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            messages.success(
                request, "We've sent a verification link to the registered email address. Please verify it")
            return redirect('login')

    else:
        form = RegistrationForm()
    context = {
        'form': form,
    }
    return render(request, 'accounts/signup.html', context)



def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(
            request, 'Congratulations! Your account is activated.')
        return redirect(login)
    else:
        messages.error(request, 'Invalid activation link')
        return redirect(login)



def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)

            # Reset password email
            current_site = get_current_site(request)
            mail_subject = 'Reset Your Password'
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()

            messages.success(
                request, 'Password reset email has been sent to your email  address')
            return redirect('login')

        else:
            messages.error(request, 'Account does not exist!')
            return redirect('forgot_password')

    return render(request, 'accounts/forgot_password.html')



def reset_password_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')
        return redirect('reset_password')
    else:
        messages.error(request, 'This link has expired!')
        return redirect('login')



def reset_password(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset succesfull')
            return redirect('login')
        else:
            messages.error(request, 'Password doesnot match')
            return redirect('reset_password')

    return render(request, 'accounts/reset_password.html')


# -------------------------- User Dashboard --------------------------

@login_required(login_url='login')
def dashboard(request):
    address = Address.objects.filter(user=request.user).order_by('-id')
    context = {'user_addresses': address}
    return render(request, 'user/dashboard.html', context)



@login_required(login_url='login')
def edit_profile(request, user_id):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone_number = request.POST['phone_number']
        edited_user = Account.objects.filter(id=user_id)
        edited_user.update(first_name=first_name,
                           last_name=last_name, phone_number=phone_number)

        messages.success(request, 'Profile Details updated successfully')
        return redirect('dashboard')

    return render(request, 'user/edit_profile.html')



@login_required(login_url='login')
def change_password(request, user_id):
    if request.method == 'POST':
        old_password = request.POST['old_password']
        new_password = request.POST['new_password']
        confirm_new_password = request.POST['confirm_new_password']
        user = Account.objects.get(id=user_id)
        if not user.check_password(old_password):
            messages.error(request, 'Incorrect password')
            return redirect(dashboard)
        else:
            if new_password == confirm_new_password:
                user.set_password(new_password)
                user.save()
                auth.login(request, user)
                messages.success(request, 'Password changed succesfully!')
                return redirect(dashboard)
            else:
                messages.error(request, 'Password doesnot match.')
                return redirect(dashboard)

    return render(request, 'user/change_password.html')



@login_required
def change_dp(request):
    user_id = request.user.id
    user = Account.objects.get(id=user_id)

    try:
        image = request.FILES['user_image']
        user.user_image = image
        user.save()
    except:
        pass
    return redirect(dashboard)


# -------------------------- Addresses --------------------------

@login_required
def add_address(request,num=0):
    if request.method == "POST":
        address_form = UserAddressForm(data=request.POST)

        if address_form.is_valid():
            address_form = address_form.save(commit=False)
            address_form.user = request.user

            Address.objects.filter(user=request.user).update(default=False)
            address_form.default = True
            address_form.save()

            number = int(request.GET.get('num'))
            
            if number == 1:
                return HttpResponseRedirect(reverse("dashboard"))
            elif number == 2:
                return HttpResponseRedirect(reverse("checkout"))

    else:
        address_form = UserAddressForm()
        return render(request, "user/address.html", {"form": address_form, "num" : num})



@login_required
def edit_address(request, id):
    if request.method == "POST":
        address = Address.objects.get(id=id, user=request.user)
        address_form = UserAddressForm(instance=address, data=request.POST)
        if address_form.is_valid():
            address_form.save()        
            return HttpResponseRedirect(reverse("dashboard"))
        
    else:
        address = Address.objects.get(id=id, user=request.user)
        address_form = UserAddressForm(instance=address)
    return render(request, "user/edit_address.html", {"form": address_form})



@login_required
def delete_address(request, id, num):
    address = Address.objects.get(id=id, user=request.user)
    address.delete()

    if num == 1:
        return redirect('dashboard')
    elif num == 2:
        return redirect('checkout')



@login_required
def default_address(request, id, num):
    Address.objects.filter(
        user=request.user, default=True).update(default=False)
    Address.objects.filter(id=id, user=request.user).update(default=True)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
