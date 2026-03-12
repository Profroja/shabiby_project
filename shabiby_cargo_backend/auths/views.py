from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login as django_login
from .serializers import LoginSerializer, UserSerializer

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username_or_email = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            # Try to authenticate with username first
            user = authenticate(username=username_or_email, password=password)
            
            # If authentication fails, try with email
            if user is None:
                from .models import User
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is not None:
                # Create Django session
                django_login(request, user)
                
                user_data = UserSerializer(user).data
                
                # Determine redirect URL based on user role
                if user.role == 'branch_agent':
                    redirect_url = '/branchagent-dashboard/'
                elif user.role == 'admin':
                    redirect_url = '/admin-dashboard/'
                elif user.role == 'conductor':
                    redirect_url = '/conductor-dashboard/'
                else:
                    # Default redirect for other roles
                    redirect_url = '/admin-dashboard/'
                
                return Response({
                    'success': True,
                    'message': 'Login successful',
                    'user': user_data,
                    'redirect_url': redirect_url
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'message': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            'success': False,
            'message': 'Invalid data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

@login_required
def admin_dashboard(request):
    from cargo_management.models import Cargo, CargoCenter, Customer, Agent, Vehicle
    
    # Total statistics
    total_cargos = Cargo.objects.count()
    total_agents = Agent.objects.count()
    total_vehicles = Vehicle.objects.count()
    total_centers = CargoCenter.objects.count()
    total_customers = Customer.objects.count()
    
    # Cargo status statistics
    registered_cargos = Cargo.objects.filter(status='registered').count()
    in_transit_cargos = Cargo.objects.filter(status='shipped').count()
    arrived_cargos = Cargo.objects.filter(status='arrived').count()
    delivered_cargos = Cargo.objects.filter(status='delivered').count()
    
    context = {
        'total_cargos': total_cargos,
        'total_agents': total_agents,
        'total_vehicles': total_vehicles,
        'total_centers': total_centers,
        'total_customers': total_customers,
        'registered_cargos': registered_cargos,
        'in_transit_cargos': in_transit_cargos,
        'arrived_cargos': arrived_cargos,
        'delivered_cargos': delivered_cargos,
    }
    
    return render(request, 'admin_dashboard.html', context)

@login_required
def branchagent_dashboard(request):
    from cargo_management.models import Cargo, CargoCenter
    
    # Get agent's branch
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    if agent_branch:
        # Total cargos for this branch (origin or destination)
        total_cargos = Cargo.objects.filter(
            models.Q(origin_branch=agent_branch) | models.Q(destination_branch=agent_branch)
        ).count()
        
        # Registered cargos (at this branch)
        registered_cargos = Cargo.objects.filter(
            origin_branch=agent_branch,
            status='registered'
        ).count()
        
        # In transit cargos (shipped from or to this branch)
        in_transit_cargos = Cargo.objects.filter(
            models.Q(origin_branch=agent_branch) | models.Q(destination_branch=agent_branch),
            status='shipped'
        ).count()
        
        # Incoming cargos (destination is this branch, not yet delivered)
        incoming_cargos = Cargo.objects.filter(
            destination_branch=agent_branch,
            status__in=['shipped', 'arrived']
        ).count()
        
        # Onboarded cargos (shipped from this branch - loaded on vehicle)
        onboarded_cargos = Cargo.objects.filter(
            origin_branch=agent_branch,
            status='shipped'
        ).count()
        
        # Offboarded cargos (arrived at this branch - unloaded from vehicle)
        offboarded_cargos = Cargo.objects.filter(
            destination_branch=agent_branch,
            status='arrived'
        ).count()
        
        # Get registered cargos list for display
        registered_cargos_list = Cargo.objects.filter(
            origin_branch=agent_branch,
            status='registered'
        ).select_related('sender', 'receiver', 'origin_branch', 'destination_branch').order_by('-created_at')
    else:
        total_cargos = 0
        registered_cargos = 0
        in_transit_cargos = 0
        incoming_cargos = 0
        onboarded_cargos = 0
        offboarded_cargos = 0
        registered_cargos_list = []
    
    # Get all branches for the registration modal
    branches = CargoCenter.objects.filter(is_active=True).order_by('location')
    
    context = {
        'total_cargos': total_cargos,
        'registered_cargos': registered_cargos,
        'in_transit_cargos': in_transit_cargos,
        'incoming_cargos': incoming_cargos,
        'onboarded_cargos': onboarded_cargos,
        'offboarded_cargos': offboarded_cargos,
        'registered_cargos_list': registered_cargos_list,
        'branches': branches,
    }
    
    return render(request, 'branchagent_dashboard.html', context)

def agents_page(request):
    return render(request, 'agents.html')

def cargo_centers_page(request):
    return render(request, 'cargo-centers.html')

def logout_view(request):
    """Logout user and redirect to login page"""
    from django.contrib.auth import logout
    from django.shortcuts import redirect
    
    logout(request)
    return redirect('login_page')

@login_required
def calculate_shipping_fee(request):
    """API endpoint to calculate shipping fee based on cargo value"""
    from cargo_management.models import ShippingFeeConfig
    from decimal import Decimal
    
    try:
        cargo_value = request.GET.get('cargo_value')
        
        if not cargo_value:
            return JsonResponse({
                'success': False,
                'message': 'Cargo value is required'
            }, status=400)
        
        # Convert cargo value to Decimal
        cargo_value_decimal = Decimal(cargo_value)
        
        # Get shipping fee config for this cargo value range
        shipping_config = ShippingFeeConfig.objects.filter(
            min_cargo_value__lte=cargo_value_decimal,
            max_cargo_value__gte=cargo_value_decimal,
            is_active=True
        ).first()
        
        if not shipping_config:
            return JsonResponse({
                'success': False,
                'message': 'No shipping fee configuration found for this cargo value. Please contact admin.'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'shipping_amount': float(shipping_config.shipping_fee),
            'cargo_value': float(cargo_value_decimal),
            'min_cargo_value': float(shipping_config.min_cargo_value),
            'max_cargo_value': float(shipping_config.max_cargo_value)
        })
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid cargo value'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error calculating shipping fee: {str(e)}'
        }, status=500)
