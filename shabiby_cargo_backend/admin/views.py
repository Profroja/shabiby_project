from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from cargo_management.models import Agent, CargoCenter, Vehicle, ShippingFeeConfig, Cargo
from auths.models import User
import json
from decimal import Decimal


def agents_list_view(request):
    """Render agents page with all agents from database"""
    agents = Agent.objects.select_related('user', 'office').all()
    cargo_centers = CargoCenter.objects.filter(is_active=True).all()
    
    context = {
        'agents': agents,
        'cargo_centers': cargo_centers,
    }
    return render(request, 'agents.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def create_agent(request):
    """API endpoint to create a new agent"""
    try:
        data = json.loads(request.body)
        
        # Create User first
        user = User.objects.create_user(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            first_name=data.get('firstName'),
            last_name=data.get('lastName'),
            mobile_number=data.get('mobileNumber'),
            role=data.get('role')
        )
        
        # Get cargo center if office is provided
        office = None
        if data.get('office'):
            office = CargoCenter.objects.get(id=data.get('office'))
        
        # Create Agent profile
        agent = Agent.objects.create(
            user=user,
            office=office
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Agent created successfully',
            'agent': {
                'id': agent.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'email': user.email,
                'office': office.center_name if office else 'No Office',
                'role': user.get_role_display()
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def update_agent(request, agent_id):
    """API endpoint to update an existing agent"""
    try:
        data = json.loads(request.body)
        agent = Agent.objects.get(id=agent_id)
        user = agent.user
        
        # Update user fields
        user.first_name = data.get('firstName', user.first_name)
        user.last_name = data.get('lastName', user.last_name)
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.mobile_number = data.get('mobileNumber', user.mobile_number)
        user.role = data.get('role', user.role)
        
        # Update password if provided
        if data.get('password'):
            user.set_password(data.get('password'))
        
        user.save()
        
        # Update office
        if data.get('office'):
            agent.office = CargoCenter.objects.get(id=data.get('office'))
            agent.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Agent updated successfully'
        })
    except Agent.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Agent not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_agent(request, agent_id):
    """API endpoint to delete an agent"""
    try:
        agent = Agent.objects.get(id=agent_id)
        user = agent.user
        
        # Delete agent (will cascade delete user due to OneToOne relationship)
        agent.delete()
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Agent deleted successfully'
        })
    except Agent.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Agent not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@require_http_methods(["GET"])
def get_agent(request, agent_id):
    """API endpoint to get a single agent's details"""
    try:
        agent = Agent.objects.select_related('user', 'office').get(id=agent_id)
        user = agent.user
        
        return JsonResponse({
            'success': True,
            'agent': {
                'id': agent.id,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'username': user.username,
                'email': user.email,
                'mobileNumber': user.mobile_number or '',
                'office': agent.office.id if agent.office else '',
                'role': user.role
            }
        })
    except Agent.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Agent not found'
        }, status=404)


# ==================== CARGO CENTERS VIEWS ====================

def cargo_centers_list_view(request):
    """Render cargo centers page with all centers from database"""
    cargo_centers = CargoCenter.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_centers = cargo_centers.count()
    active_centers = cargo_centers.filter(is_active=True).count()
    inactive_centers = cargo_centers.filter(is_active=False).count()
    
    context = {
        'cargo_centers': cargo_centers,
        'total_centers': total_centers,
        'active_centers': active_centers,
        'inactive_centers': inactive_centers,
    }
    return render(request, 'cargo-centers.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def create_cargo_center(request):
    """API endpoint to create a new cargo center"""
    try:
        data = json.loads(request.body)
        
        # Create cargo center
        cargo_center = CargoCenter.objects.create(
            center_name=data.get('centerName'),
            location=data.get('location'),
            is_active=data.get('isActive', True)
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Cargo center created successfully',
            'center': {
                'id': cargo_center.id,
                'center_name': cargo_center.center_name,
                'location': cargo_center.location,
                'is_active': cargo_center.is_active,
                'created_at': cargo_center.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def update_cargo_center(request, center_id):
    """API endpoint to update an existing cargo center"""
    try:
        data = json.loads(request.body)
        cargo_center = CargoCenter.objects.get(id=center_id)
        
        # Update fields
        cargo_center.center_name = data.get('centerName', cargo_center.center_name)
        cargo_center.location = data.get('location', cargo_center.location)
        cargo_center.is_active = data.get('isActive', cargo_center.is_active)
        cargo_center.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cargo center updated successfully'
        })
    except CargoCenter.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo center not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_cargo_center(request, center_id):
    """API endpoint to delete a cargo center"""
    try:
        cargo_center = CargoCenter.objects.get(id=center_id)
        cargo_center.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Cargo center deleted successfully'
        })
    except CargoCenter.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo center not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@require_http_methods(["GET"])
def get_cargo_center(request, center_id):
    """API endpoint to get a single cargo center's details"""
    try:
        cargo_center = CargoCenter.objects.get(id=center_id)
        
        return JsonResponse({
            'success': True,
            'center': {
                'id': cargo_center.id,
                'centerName': cargo_center.center_name,
                'location': cargo_center.location,
                'isActive': cargo_center.is_active
            }
        })
    except CargoCenter.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo center not found'
        }, status=404)


# ============= VEHICLES VIEWS =============

def vehicles_list_view(request):
    """Render vehicles page with all vehicles from database"""
    vehicles = Vehicle.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_vehicles = vehicles.count()
    active_vehicles = vehicles.filter(is_active=True).count()
    inactive_vehicles = vehicles.filter(is_active=False).count()
    
    context = {
        'vehicles': vehicles,
        'total_vehicles': total_vehicles,
        'active_vehicles': active_vehicles,
        'inactive_vehicles': inactive_vehicles,
    }
    
    return render(request, 'vehicles.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def create_vehicle(request):
    """Create a new vehicle"""
    try:
        data = json.loads(request.body)
        
        # Create vehicle
        vehicle = Vehicle.objects.create(
            vehicle_type=data.get('vehicleType'),
            vehicle_model=data.get('vehicleModel'),
            company_owner=data.get('companyOwner'),
            registration_number=data.get('registrationNumber'),
            plate_number=data.get('plateNumber'),
            max_weight=Decimal(str(data.get('maxWeight'))),
            chassis_number=data.get('chassisNumber'),
            is_active=data.get('isActive', True)
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Vehicle created successfully',
            'vehicle_id': vehicle.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def update_vehicle(request, vehicle_id):
    """Update an existing vehicle"""
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        data = json.loads(request.body)
        
        # Update vehicle fields
        vehicle.vehicle_type = data.get('vehicleType', vehicle.vehicle_type)
        vehicle.vehicle_model = data.get('vehicleModel', vehicle.vehicle_model)
        vehicle.company_owner = data.get('companyOwner', vehicle.company_owner)
        vehicle.registration_number = data.get('registrationNumber', vehicle.registration_number)
        vehicle.plate_number = data.get('plateNumber', vehicle.plate_number)
        vehicle.max_weight = Decimal(str(data.get('maxWeight', vehicle.max_weight)))
        vehicle.chassis_number = data.get('chassisNumber', vehicle.chassis_number)
        vehicle.is_active = data.get('isActive', vehicle.is_active)
        
        vehicle.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Vehicle updated successfully'
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Vehicle not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_vehicle(request, vehicle_id):
    """Delete a vehicle"""
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        vehicle.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Vehicle deleted successfully'
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Vehicle not found'
        }, status=404)


@require_http_methods(["GET"])
def get_vehicle(request, vehicle_id):
    """Get a single vehicle's details"""
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        
        return JsonResponse({
            'success': True,
            'vehicle': {
                'id': vehicle.id,
                'vehicleType': vehicle.vehicle_type,
                'vehicleModel': vehicle.vehicle_model,
                'companyOwner': vehicle.company_owner,
                'registrationNumber': vehicle.registration_number,
                'plateNumber': vehicle.plate_number,
                'maxWeight': str(vehicle.max_weight),
                'chassisNumber': vehicle.chassis_number,
                'isActive': vehicle.is_active,
            }
        })
    except Vehicle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Vehicle not found'
        }, status=404)


# ============================================
# SHIPPING FEE CONFIGURATION VIEWS
# ============================================

def shipping_fee_configs_view(request):
    """Render shipping fee configurations page"""
    configs = ShippingFeeConfig.objects.all().order_by('min_cargo_value')
    
    context = {
        'configs': configs,
    }
    return render(request, 'shipping_fee_configs.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def create_shipping_fee_config(request):
    """API endpoint to create a new shipping fee configuration"""
    try:
        data = json.loads(request.body)
        
        min_value = Decimal(data.get('min_cargo_value'))
        max_value = Decimal(data.get('max_cargo_value'))
        shipping_fee = Decimal(data.get('shipping_fee'))
        
        # Validate that min < max
        if min_value >= max_value:
            return JsonResponse({
                'success': False,
                'message': 'Minimum cargo value must be less than maximum cargo value'
            }, status=400)
        
        # Check for overlapping ranges
        from django.db.models import Q
        overlapping = ShippingFeeConfig.objects.filter(
            is_active=True
        ).filter(
            Q(min_cargo_value__lte=max_value, max_cargo_value__gte=min_value)
        ).exists()
        
        if overlapping:
            return JsonResponse({
                'success': False,
                'message': 'This range overlaps with an existing configuration'
            }, status=400)
        
        # Create shipping fee config
        config = ShippingFeeConfig.objects.create(
            min_cargo_value=min_value,
            max_cargo_value=max_value,
            shipping_fee=shipping_fee,
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Shipping fee configuration created successfully',
            'config': {
                'id': config.id,
                'min_cargo_value': str(config.min_cargo_value),
                'max_cargo_value': str(config.max_cargo_value),
                'shipping_fee': str(config.shipping_fee),
                'is_active': config.is_active
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
def update_shipping_fee_config(request, config_id):
    """API endpoint to update a shipping fee configuration"""
    try:
        config = ShippingFeeConfig.objects.get(id=config_id)
        data = json.loads(request.body)
        
        min_value = Decimal(data.get('min_cargo_value'))
        max_value = Decimal(data.get('max_cargo_value'))
        shipping_fee = Decimal(data.get('shipping_fee'))
        
        # Validate that min < max
        if min_value >= max_value:
            return JsonResponse({
                'success': False,
                'message': 'Minimum cargo value must be less than maximum cargo value'
            }, status=400)
        
        # Check for overlapping ranges (excluding current config)
        from django.db.models import Q
        overlapping = ShippingFeeConfig.objects.filter(
            is_active=True
        ).exclude(id=config_id).filter(
            Q(min_cargo_value__lte=max_value, max_cargo_value__gte=min_value)
        ).exists()
        
        if overlapping:
            return JsonResponse({
                'success': False,
                'message': 'This range overlaps with an existing configuration'
            }, status=400)
        
        # Update config
        config.min_cargo_value = min_value
        config.max_cargo_value = max_value
        config.shipping_fee = shipping_fee
        config.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Shipping fee configuration updated successfully'
        })
        
    except ShippingFeeConfig.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Configuration not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_shipping_fee_config(request, config_id):
    """API endpoint to delete a shipping fee configuration"""
    try:
        config = ShippingFeeConfig.objects.get(id=config_id)
        config.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Shipping fee configuration deleted successfully'
        })
        
    except ShippingFeeConfig.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Configuration not found'
        }, status=404)


# ==================== ADMIN ALL CARGOS VIEW ====================

@login_required
def all_cargos_view(request):
    """View for all cargos from all branches (Admin view)"""
    # Get all cargos from all branches
    cargos = Cargo.objects.select_related(
        'sender', 'receiver', 'origin_branch', 'destination_branch', 
        'assigned_vehicle', 'registered_by', 'shipped_by', 'delivered_by_agent'
    ).order_by('-created_at')
    
    context = {
        'cargos': cargos,
    }
    return render(request, 'all-cargos.html', context)
