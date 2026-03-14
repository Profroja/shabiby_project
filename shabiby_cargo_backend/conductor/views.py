from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from cargo_management.models import Cargo
import json

@login_required
def conductor_onboard(request):
    """Onboard cargo page for conductors"""
    from cargo_management.models import Vehicle
    
    # Get all active vehicles
    vehicles = Vehicle.objects.filter(is_active=True).order_by('plate_number')
    
    context = {
        'vehicles': vehicles,
    }
    
    return render(request, 'onboard.html', context)

@login_required
def conductor_offboard(request):
    """Offboard cargo page for conductors"""
    return render(request, 'offboard.html')

@login_required
@require_http_methods(["GET"])
def search_cargo(request):
    """API endpoint to search for cargo by cargo number"""
    cargo_number = request.GET.get('cargo_number', '').strip()
    
    if not cargo_number:
        return JsonResponse({
            'success': False,
            'message': 'Cargo number is required'
        }, status=400)
    
    # Extract cargo number from QR code format if needed
    # QR format: CARGO:SHB10032026-65978D|RECEIPT:RCP-10032026-65978|FROM:Moshi|TO:Dodoma|STATUS:registered
    if 'CARGO:' in cargo_number:
        parts = cargo_number.split('|')
        for part in parts:
            if part.startswith('CARGO:'):
                cargo_number = part.replace('CARGO:', '').strip()
                break
    
    try:
        cargo = Cargo.objects.select_related(
            'sender', 'receiver', 'origin_branch', 'destination_branch',
            'assigned_vehicle', 'shipped_by'
        ).get(cargo_number=cargo_number)
        
        # Prepare cargo data
        cargo_data = {
            'id': cargo.id,
            'cargo_number': cargo.cargo_number,
            'receipt_number': cargo.receipt_number if hasattr(cargo, 'receipt_number') else None,
            'description': cargo.cargo_description,
            'quantity': cargo.quantity,
            'weight': float(cargo.weight) if cargo.weight else None,
            'cargo_value': float(cargo.cargo_value),
            'shipping_amount': float(cargo.shipping_amount),
            'sender_name': cargo.sender.full_name,
            'sender_phone': cargo.sender.mobile_number,
            'receiver_name': cargo.receiver.full_name,
            'receiver_phone': cargo.receiver.mobile_number,
            'origin': cargo.origin_branch.location,
            'destination': cargo.destination_branch.location,
            'status': cargo.get_status_display(),
            'vehicle_plate': cargo.assigned_vehicle.plate_number if cargo.assigned_vehicle else None,
            'vehicle_model': cargo.assigned_vehicle.vehicle_model if cargo.assigned_vehicle else None,
            'conductor_name': cargo.shipped_by.user.get_full_name() if cargo.shipped_by and cargo.shipped_by.user else None,
        }
        
        return JsonResponse({
            'success': True,
            'cargo': cargo_data
        })
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f'Cargo with number "{cargo_number}" not found'
        }, status=404)
    except Exception as e:
        import traceback
        print(f"ERROR in search_cargo: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'message': f'Error searching cargo: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def onboard_cargo(request):
    """API endpoint to onboard a single cargo"""
    from cargo_management.models import Vehicle
    
    try:
        data = json.loads(request.body)
        cargo_id = data.get('cargo_id')
        vehicle_id = data.get('vehicle_id')
        
        if not cargo_id:
            return JsonResponse({
                'success': False,
                'message': 'Cargo ID is required'
            }, status=400)
        
        if not vehicle_id:
            return JsonResponse({
                'success': False,
                'message': 'Vehicle selection is required'
            }, status=400)
        
        # Get cargo
        cargo = Cargo.objects.get(id=cargo_id)
        
        # Get vehicle
        vehicle = Vehicle.objects.get(id=vehicle_id, is_active=True)
        
        # Check if cargo is in registered status
        if cargo.status != 'registered':
            return JsonResponse({
                'success': False,
                'message': f'Cargo is already {cargo.get_status_display()}. Only registered cargos can be onboarded.'
            }, status=400)
        
        # Get conductor's agent profile
        conductor = request.user
        conductor_agent = conductor.agent_profile if hasattr(conductor, 'agent_profile') else None
        
        if not conductor_agent:
            return JsonResponse({
                'success': False,
                'message': 'Conductor profile not found'
            }, status=400)
        
        # Update cargo status to shipped
        cargo.status = 'shipped'
        cargo.shipped_by = conductor_agent
        cargo.shipped_at = timezone.now()
        cargo.assigned_vehicle = vehicle
        cargo.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Cargo {cargo.cargo_number} onboarded to vehicle {vehicle.plate_number} successfully!'
        })
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found'
        }, status=404)
    except Vehicle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Vehicle not found or inactive'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error onboarding cargo: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def offboard_cargo(request):
    """API endpoint to offboard a single cargo (mark as arrived)"""
    try:
        data = json.loads(request.body)
        cargo_id = data.get('cargo_id')
        
        if not cargo_id:
            return JsonResponse({
                'success': False,
                'message': 'Cargo ID is required'
            }, status=400)
        
        # Get cargo
        cargo = Cargo.objects.get(id=cargo_id)
        
        # Check if cargo is in shipped status
        if cargo.status != 'shipped':
            return JsonResponse({
                'success': False,
                'message': f'Cargo is {cargo.get_status_display()}. Only cargos that are "On Way" can be offboarded.'
            }, status=400)
        
        # Get conductor's agent profile
        conductor = request.user
        conductor_agent = conductor.agent_profile if hasattr(conductor, 'agent_profile') else None
        
        if not conductor_agent:
            return JsonResponse({
                'success': False,
                'message': 'Conductor profile not found'
            }, status=400)
        
        # Verify this conductor shipped this cargo
        if cargo.shipped_by != conductor_agent:
            return JsonResponse({
                'success': False,
                'message': 'You can only offboard cargos that you onboarded'
            }, status=403)
        
        # Update cargo status to arrived
        cargo.status = 'arrived'
        cargo.arrived_at = timezone.now()
        cargo.current_branch = cargo.destination_branch
        cargo.save()
        
        # Send SMS notification to receiver
        from sms_notification.sms_notification import send_cargo_arrival_sms
        send_cargo_arrival_sms(cargo)
        
        return JsonResponse({
            'success': True,
            'message': f'Cargo {cargo.cargo_number} offboarded successfully! Marked as arrived at {cargo.destination_branch.location}.'
        })
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error offboarding cargo: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def bulk_offboard_cargos(request):
    """API endpoint to offboard multiple cargos at once (mark as arrived)"""
    try:
        data = json.loads(request.body)
        cargo_ids = data.get('cargo_ids', [])
        
        if not cargo_ids:
            return JsonResponse({
                'success': False,
                'message': 'At least one cargo ID is required'
            }, status=400)
        
        # Get conductor's agent profile
        conductor = request.user
        conductor_agent = conductor.agent_profile if hasattr(conductor, 'agent_profile') else None
        
        if not conductor_agent:
            return JsonResponse({
                'success': False,
                'message': 'Conductor profile not found'
            }, status=400)
        
        # Get all cargos
        cargos = Cargo.objects.filter(id__in=cargo_ids)
        
        if cargos.count() != len(cargo_ids):
            return JsonResponse({
                'success': False,
                'message': 'Some cargos were not found'
            }, status=404)
        
        # Check if all cargos are in shipped status
        non_shipped = cargos.exclude(status='shipped')
        if non_shipped.exists():
            non_shipped_list = ', '.join([c.cargo_number for c in non_shipped])
            return JsonResponse({
                'success': False,
                'message': f'Some cargos are not in shipped status: {non_shipped_list}'
            }, status=400)
        
        # Verify this conductor shipped all these cargos
        not_by_conductor = cargos.exclude(shipped_by=conductor_agent)
        if not_by_conductor.exists():
            return JsonResponse({
                'success': False,
                'message': 'You can only offboard cargos that you onboarded'
            }, status=403)
        
        # Update all cargos to arrived status
        offboarded_count = 0
        offboarded_numbers = []
        
        from sms_notification.sms_notification import send_cargo_arrival_sms
        
        for cargo in cargos:
            cargo.status = 'arrived'
            cargo.arrived_at = timezone.now()
            cargo.current_branch = cargo.destination_branch
            cargo.save()
            
            # Send SMS notification to receiver
            send_cargo_arrival_sms(cargo)
            
            offboarded_count += 1
            offboarded_numbers.append(cargo.cargo_number)
        
        return JsonResponse({
            'success': True,
            'message': f'{offboarded_count} cargo(s) offboarded successfully!',
            'offboarded_count': offboarded_count,
            'cargo_numbers': offboarded_numbers
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error offboarding cargos: {str(e)}'
        }, status=500)

@login_required
def conductor_dashboard(request):
    """Dashboard for conductors showing only their onboarded/offboarded cargo"""
    
    # Get conductor's agent profile
    conductor = request.user
    conductor_agent = conductor.agent_profile if hasattr(conductor, 'agent_profile') else None
    
    # Onboarded cargos (shipped by this conductor) - currently in transit
    onboarded_cargos = Cargo.objects.filter(
        shipped_by=conductor_agent,
        status='shipped'
    ).count()
    
    # Offboarded cargos (shipped by this conductor) - arrived at destination
    offboarded_cargos = Cargo.objects.filter(
        shipped_by=conductor_agent,
        status='arrived'
    ).count()
    
    context = {
        'onboarded_cargos': onboarded_cargos,
        'offboarded_cargos': offboarded_cargos,
    }
    
    return render(request, 'conductor_dashboard.html', context)


@login_required
def conductor_registered_cargos_view(request):
    """View for registered cargos from conductor's branch"""
    from cargo_management.models import Vehicle
    
    # Get conductor's branch
    conductor = request.user
    conductor_branch = conductor.agent_profile.office if hasattr(conductor, 'agent_profile') else None
    
    # Filter registered cargos by conductor's branch
    if conductor_branch:
        cargos = Cargo.objects.filter(
            status='registered',
            origin_branch=conductor_branch
        ).order_by('-created_at')
    else:
        cargos = Cargo.objects.filter(status='registered').order_by('-created_at')
    
    vehicles = Vehicle.objects.filter(is_active=True).order_by('plate_number')
    
    context = {
        'cargos': cargos,
        'vehicles': vehicles,
    }
    
    return render(request, 'conductor_registered_cargos.html', context)


@login_required
def conductor_onboarded_cargos_view(request):
    """View for all cargos shipped by this conductor (regardless of current status)"""
    # Get conductor's agent profile
    conductor = request.user
    conductor_agent = conductor.agent_profile if hasattr(conductor, 'agent_profile') else None
    
    # Get all cargos shipped by this conductor (status can be shipped, arrived, or delivered)
    if conductor_agent:
        cargos = Cargo.objects.filter(
            shipped_by=conductor_agent
        ).select_related(
            'sender', 'receiver', 'origin_branch', 'destination_branch', 'assigned_vehicle'
        ).order_by('-shipped_at')
    else:
        cargos = Cargo.objects.none()
    
    context = {
        'cargos': cargos,
    }
    
    return render(request, 'onboarded_list.html', context)


@login_required
def conductor_offboarded_cargos_view(request):
    """View for cargos shipped by this conductor that have arrived"""
    # Get conductor's agent profile
    conductor = request.user
    conductor_agent = conductor.agent_profile if hasattr(conductor, 'agent_profile') else None
    
    # Filter arrived cargos shipped by this conductor
    if conductor_agent:
        cargos = Cargo.objects.filter(
            shipped_by=conductor_agent,
            status='arrived'
        ).order_by('-arrived_at')
    else:
        cargos = Cargo.objects.none()
    
    context = {
        'cargos': cargos,
    }
    
    return render(request, 'conductor_offboarded_cargos.html', context)

@login_required
@require_http_methods(["GET"])
def search_cargo_group(request):
    """API endpoint to search for cargo group by QR code data"""
    from cargo_management.models import CargoGroup
    
    qr_data = request.GET.get('qr_data', '').strip()
    
    if not qr_data:
        return JsonResponse({
            'success': False,
            'message': 'QR code data is required'
        }, status=400)
    
    try:
        # Find cargo group by QR code data
        cargo_group = CargoGroup.objects.prefetch_related(
            'cargos__sender',
            'cargos__receiver',
            'cargos__origin_branch',
            'cargos__destination_branch'
        ).get(qr_code_data=qr_data)
        
        # Get all cargos in the group
        cargos = cargo_group.cargos.all()
        
        # Check if all cargos are in registered status
        non_registered = cargos.exclude(status='registered')
        if non_registered.exists():
            non_registered_list = ', '.join([c.cargo_number for c in non_registered])
            return JsonResponse({
                'success': False,
                'message': f'Some cargos are not in registered status: {non_registered_list}'
            }, status=400)
        
        # Prepare cargo data
        cargo_list = []
        for cargo in cargos:
            cargo_list.append({
                'id': cargo.id,
                'cargo_number': cargo.cargo_number,
                'origin': cargo.origin_branch.location,
                'destination': cargo.destination_branch.location,
                'quantity': cargo.quantity,
                'description': cargo.cargo_description,
                'sender_name': cargo.sender.full_name if cargo.sender else 'N/A',
                'receiver_name': cargo.receiver.full_name if cargo.receiver else 'N/A',
            })
        
        return JsonResponse({
            'success': True,
            'group_id': cargo_group.group_id,
            'total_cargos': cargos.count(),
            'cargos': cargo_list
        })
        
    except CargoGroup.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo group not found. Please check the QR code.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error searching cargo group: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def search_cargo_group_for_offboard(request):
    """API endpoint to search for cargo group by QR code data for offboarding"""
    from cargo_management.models import CargoGroup
    
    qr_data = request.GET.get('qr_data', '').strip()
    
    if not qr_data:
        return JsonResponse({
            'success': False,
            'message': 'QR code data is required'
        }, status=400)
    
    try:
        # Find cargo group by QR code data
        cargo_group = CargoGroup.objects.prefetch_related(
            'cargos__sender',
            'cargos__receiver',
            'cargos__origin_branch',
            'cargos__destination_branch'
        ).get(qr_code_data=qr_data)
        
        # Get all cargos in the group
        cargos = cargo_group.cargos.all()
        
        # Check if all cargos are in shipped status (for offboarding)
        non_shipped = cargos.exclude(status='shipped')
        if non_shipped.exists():
            non_shipped_list = ', '.join([f"{c.cargo_number} ({c.get_status_display()})" for c in non_shipped])
            return JsonResponse({
                'success': False,
                'message': f'Some cargos are not in shipped status: {non_shipped_list}. Only cargos "On Way" can be offboarded.'
            }, status=400)
        
        # Prepare cargo data
        cargo_list = []
        for cargo in cargos:
            cargo_list.append({
                'id': cargo.id,
                'cargo_number': cargo.cargo_number,
                'origin': cargo.origin_branch.location,
                'destination': cargo.destination_branch.location,
                'quantity': cargo.quantity,
                'description': cargo.cargo_description,
                'sender_name': cargo.sender.full_name if cargo.sender else 'N/A',
                'receiver_name': cargo.receiver.full_name if cargo.receiver else 'N/A',
            })
        
        return JsonResponse({
            'success': True,
            'group_id': cargo_group.group_id,
            'total_cargos': cargos.count(),
            'cargos': cargo_list
        })
        
    except CargoGroup.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo group not found. Please check the QR code.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error searching cargo group: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def bulk_onboard_cargos(request):
    """API endpoint to onboard multiple cargos at once"""
    from cargo_management.models import Vehicle
    
    try:
        data = json.loads(request.body)
        cargo_ids = data.get('cargo_ids', [])
        vehicle_id = data.get('vehicle_id')
        
        if not cargo_ids:
            return JsonResponse({
                'success': False,
                'message': 'At least one cargo ID is required'
            }, status=400)
        
        if not vehicle_id:
            return JsonResponse({
                'success': False,
                'message': 'Vehicle selection is required'
            }, status=400)
        
        # Get vehicle
        vehicle = Vehicle.objects.get(id=vehicle_id, is_active=True)
        
        # Get conductor's agent profile
        conductor = request.user
        conductor_agent = conductor.agent_profile if hasattr(conductor, 'agent_profile') else None
        
        if not conductor_agent:
            return JsonResponse({
                'success': False,
                'message': 'Conductor profile not found'
            }, status=400)
        
        # Get all cargos
        cargos = Cargo.objects.filter(id__in=cargo_ids)
        
        if cargos.count() != len(cargo_ids):
            return JsonResponse({
                'success': False,
                'message': 'Some cargos were not found'
            }, status=404)
        
        # Check if all cargos are in registered status
        non_registered = cargos.exclude(status='registered')
        if non_registered.exists():
            non_registered_list = ', '.join([c.cargo_number for c in non_registered])
            return JsonResponse({
                'success': False,
                'message': f'Some cargos are not in registered status: {non_registered_list}'
            }, status=400)
        
        # Update all cargos to shipped status
        onboarded_count = 0
        onboarded_numbers = []
        
        for cargo in cargos:
            cargo.status = 'shipped'
            cargo.shipped_by = conductor_agent
            cargo.shipped_at = timezone.now()
            cargo.assigned_vehicle = vehicle
            cargo.save()
            onboarded_count += 1
            onboarded_numbers.append(cargo.cargo_number)
        
        return JsonResponse({
            'success': True,
            'message': f'{onboarded_count} cargo(s) onboarded to vehicle {vehicle.plate_number} successfully!',
            'onboarded_count': onboarded_count,
            'cargo_numbers': onboarded_numbers
        })
        
    except Vehicle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Vehicle not found or inactive'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error onboarding cargos: {str(e)}'
        }, status=500)
