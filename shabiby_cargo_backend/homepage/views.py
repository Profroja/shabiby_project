from django.shortcuts import render, redirect

def login_page(request):
    """Display login page"""
    # If user is already logged in, redirect to appropriate dashboard
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('/admin-dashboard/')
        elif request.user.role == 'branch_agent':
            return redirect('/branchagent-dashboard/')
        elif request.user.role == 'conductor':
            return redirect('/conductor-dashboard/')
        else:
            return redirect('/admin-dashboard/')
    
    return render(request, 'login.html')
