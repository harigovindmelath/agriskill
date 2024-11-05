from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.generics import get_object_or_404
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from .models import Landowner, SkilledProfessional
import numpy as np
import logging
from .models import SkillSharePost
from django.core.files.storage import FileSystemStorage
import re


# Login View
def user_login(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')

        # Validate inputs
        if not identifier or not password:
            messages.error(request, 'Email/Phone and password are required.')
            return redirect('login')

        # Check user existence
        user = None
        if identifier:
            user = Landowner.objects.filter(email=identifier).first() or Landowner.objects.filter(
                mobile_number=identifier).first()
            if not user:
                user = SkilledProfessional.objects.filter(
                    email=identifier).first() or SkilledProfessional.objects.filter(
                    mobile_number=identifier).first()

        # Validate user credentials
        if user and check_password(password, user.password):
            request.session['user_email'] = user.email

            # Redirect based on user type and handle next parameter
            if isinstance(user, Landowner):
                request.session['user_role'] = 'landowner'
                return redirect(request.POST.get('next', 'landowner_home'))  # Default to landowner_home
            else:
                request.session['user_role'] = 'skilled_professional'
                return redirect(request.POST.get('next', 'skilled_professional'))  # Default to skilled_professional

        messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')


# Role Selection View
def role_selection(request):
    if request.method == 'POST':
        selected_role = request.POST.get('role')
        if selected_role:
            request.session['selected_role'] = selected_role
            return redirect(
                'skilled_professional_signup' if selected_role == 'skilled_professional' else 'landowner_signup'
            )
        messages.error(request, "Please select a role.")
    return render(request, 'role_selection.html')


# Signup View for Skilled Professional
def skilled_professional_signup(request):
    # Initialize the temporary storage dictionary outside of POST
    if 'temporary_skilled_professionals' not in request.session:
        request.session['temporary_skilled_professionals'] = {}

    if request.method == 'POST':
        # Collect input data
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        age = request.POST.get('age')
        mobile_number = request.POST.get('mobile_number')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        skills = request.POST.get('skills')  # Skills are collected here
        district = request.POST.get('district')
        city = request.POST.get('city')

        # Verify passwords match
        if password != confirm_password:
            return render(request, 'signup_skilled_professional.html', {'error': 'Passwords do not match'})

        # Temporary storage logic
        temporary_skilled_professionals = request.session['temporary_skilled_professionals']
        temporary_skilled_professionals[email] = {  # Use email as a key
            'full_name': full_name,
            'age': age,
            'mobile_number': mobile_number,
            'skills': skills,
            'district': district,
            'city': city
        }
        print(temporary_skilled_professionals)
        # Save the updated temporary skilled professionals back to the session
        request.session['temporary_skilled_professionals'] = temporary_skilled_professionals

        # Attempt to save the data to the database
        try:
            new_professional = SkilledProfessional(
                full_name=full_name,
                email=email,
                age=age,
                mobile_number=mobile_number,
                password=password,
                skills=skills,  # Skills should be saved here
                district=district,
                city=city
            )
            new_professional.save()
        except Exception as e:
            print(f"Failed to save to DB: {e}")
            return render(request, 'signup_skilled_professional.html', {'error': 'Failed to save your information.'})

        return redirect('login')  # Redirect to a success page or login

    return render(request, 'signup_skilled_professional.html')


def landowner_signup(request):
    # Check if the selected role is 'landowner'
    if request.session.get('selected_role') != 'landowner':
        return redirect('role_selection')

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('mobile_number')
        age = request.POST.get('age')  # Capture the age from the form
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Validate that all fields are filled
        if not all([full_name, email, phone_number, age, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, 'signup_landowner.html')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'signup_landowner.html')

        # Hash the password
        hashed_password = make_password(password)

        # Create a new Landowner instance with the age included
        landowner = Landowner(
            full_name=full_name,
            email=email,
            mobile_number=phone_number,
            age=age,  # Add the age field here
            password=hashed_password
        )

        try:
            # Attempt to save the landowner instance
            landowner.save()
            messages.success(request, "Signup successful for Landowner!")
            return redirect('login')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    return render(request, 'signup_landowner.html')


# Landowner Home View - Search for Skilled Professionals using TF-IDF and KNN
@login_required
def landowner_home(request):
    if request.method == 'POST':
        total_area = request.POST.get('total_area')
        skills = request.POST.get('skills')

        # Debug: Print form data
        print("Total Area:", total_area)
        print("Skills (raw):", skills)
        print("Request for post data:", request.POST)

        if not skills:
            messages.error(request, "Please enter required skills.")
            return redirect('landowner_home')

        # Preprocess landowner skills
        landowner_skills = [preprocess_skills(skill) for skill in skills.split(',') if skill.strip()]
        print("Landowner Skills (processed):", landowner_skills)

        skilled_professionals = SkilledProfessional.objects.all()
        if not skilled_professionals.exists():
            print("No skilled professionals found in the database.")
            messages.warning(request, "No skilled professionals available at the moment.")
            return redirect('landowner_home')

        # Preprocess professionals' skills and prepare for TF-IDF
        professional_skills = [preprocess_skills(prof.skills) for prof in skilled_professionals]
        print("Professional Skills (processed):", professional_skills)

        # Combine all skills
        all_skills = professional_skills + [', '.join(landowner_skills)]
        print("All Skills for TF-IDF:", all_skills)

        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(all_skills)
            print("TF-IDF Matrix Shape:", tfidf_matrix.shape)

            n_neighbors = min(5, len(skilled_professionals))
            knn = NearestNeighbors(n_neighbors=n_neighbors, metric='cosine')
            knn.fit(tfidf_matrix[:-1])

            landowner_vector = tfidf_matrix[-1]
            distances, indices = knn.kneighbors([landowner_vector])
            print("Distances:", distances)
            print("Indices:", indices)

            # Extract matched professionals based on indices
            matching_professionals = [skilled_professionals[int(i)] for i in indices.flatten()]
            print("Matching Professionals:", [(prof.full_name, prof.skills) for prof in matching_professionals])

            if not matching_professionals:
                print("No matching professionals found.")
                messages.info(request, "No matching professionals found. Try different skills.")
                return redirect('landowner_home')

            # Store in session for the matched professionals page
            request.session['matched_professionals'] = [
                {'name': prof.full_name, 'skills': prof.skills}
                for prof in matching_professionals
            ]

        except Exception as e:
            print("Error during TF-IDF and KNN processing:", str(e))
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('landowner_home')

        return redirect('matched_professionals')

    return render(request, 'landowner_home.html')


# Skilled Professional Home View (Merged with Update Work Location)


@login_required
def skilled_professional_home(request):
    # Get the logged-in user's email from the session
    user_email = request.session.get('user_email')

    # Check if a skilled professional exists with the given email
    try:
        skilled_professional = SkilledProfessional.objects.get(email=user_email)
    except SkilledProfessional.DoesNotExist:
        messages.error(request, "Skilled professional not found.")
        return redirect('login')  # Redirect to login if skilled professional not found

    if request.method == 'POST':
        # Retrieve the skilled professional's skills
        skilled_professional_skills = skilled_professional.skills

        # Debug: Print skills
        print(f"[DEBUG] Skilled Professional Skills: {skilled_professional_skills}")

        if not skilled_professional_skills:
            messages.warning(request, "Please specify your skills.")
            return redirect('skilled_professional')

        # Split skills into a list
        professional_skills_list = [skill.strip() for skill in skilled_professional_skills.split(',') if skill.strip()]

        if not professional_skills_list:
            messages.error(request, "No skills found for the skilled professional.")
            return redirect('skilled_professional')

        # Step 1: Filter landowners by help_needed based on the first skill
        landowners_by_skill = Landowner.objects.filter(
            Q(help_needed__icontains=professional_skills_list[0])  # Match first skill initially
        )

        # Debug: Check landowners filtered by the first skill
        print(
            f"[DEBUG] Landowners after skill filter: {[{'name': l.full_name, 'help_needed': l.help_needed} for l in landowners_by_skill]}")

        # Step 2: Further filter using the rest of the skills
        for skill in professional_skills_list[1:]:
            landowners_by_skill = landowners_by_skill.filter(help_needed__icontains=skill)

        # Debug: Final check of matching landowners
        print(
            f"[DEBUG] Final Matching Landowners: {[{'name': l.full_name, 'help_needed': l.help_needed} for l in landowners_by_skill]}")

        if not landowners_by_skill.exists():
            messages.info(request, "No landowners found matching your skills.")
            return redirect('skilled_professional')

        # Store matched landowners in session
        request.session['matched_landowners'] = [
            {
                'name': landowner.full_name,
                'help_needed': landowner.help_needed,
                'district': landowner.district,
                'city': landowner.city
            }
            for landowner in landowners_by_skill
        ]

        # Redirect to the matched landowners page after storing results in session
        return redirect('matched_landowners')

    # Render the skilled professional home page
    return render(request, 'skilled_professional.html', {'user': skilled_professional})


def custom_logout(request):
    # Log the user out and display a success message
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')  # Redirect to the login page


def job_listings():
    return None


def profile(request):
    # Check if the user is logged in by verifying session data
    if 'user_email' not in request.session or 'user_role' not in request.session:
        return redirect('login')

    user_email = request.session['user_email']
    user_role = request.session['user_role']

    # Fetch the user details based on role
    user = None
    if user_role == 'landowner':
        user = Landowner.objects.filter(email=user_email).first()
    elif user_role == 'skilled_professional':
        user = SkilledProfessional.objects.filter(email=user_email).first()

    # Render profile page with user data
    context = {
        'user': user,
        'role': user_role
    }
    return render(request, 'profile.html', context)


def matched_professionals(request):
    # Retrieve matched professionals from session
    matched_professionals = request.session.get('matched_professionals', [])
    print(matched_professionals)
    return render(request, 'matched_professionals.html', {'skilled_professionals': matched_professionals
                                                          })


def landowner_results(request, professional_name):
    # Fetch the professional by full_name (name field)
    professional = get_object_or_404(SkilledProfessional, full_name=professional_name)

    return render(request, 'landowner_results.html', {
        'professional': professional,
    })


def matched_landowners(request):
    return render(request, 'matched_landowner.html')


# views.py

@login_required
def skillshare_view(request):
    if request.method == 'POST':
        # Handle form submission for new post
        text = request.POST.get('postText', '')
        image = request.FILES.get('postImage')

        # Save post to the database
        post = SkillSharePost(text=text, image=image)
        post.save()

        # Redirect to the same page to display the new post
        return redirect('skillshare')

    # Fetch all posts to display on the SkillShare page
    posts = SkillSharePost.objects.all().order_by('-created_at')
    return render(request, 'skillshare.html', {'posts': posts})


def preprocess_skills(skills):
    skill = skills.lower()
    skill = skill.strip()
    skill = re.sub(r'\w\s]', '', skill)
