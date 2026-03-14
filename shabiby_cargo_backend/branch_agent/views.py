from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from cargo_management.models import Cargo, Customer, CargoCenter, Vehicle
from django.utils import timezone
import random
import string
from datetime import datetime
import qrcode
import io
import base64
from xhtml2pdf import pisa

@login_required
def all_cargos_view(request):
    """View for all cargos related to the agent's branch"""
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    if agent_branch:
        # Get all cargos where this branch is either origin or destination
        cargos = Cargo.objects.filter(
            models.Q(origin_branch=agent_branch) | models.Q(destination_branch=agent_branch)
        ).select_related('sender', 'receiver', 'origin_branch', 'destination_branch', 'assigned_vehicle', 'registered_by').order_by('-created_at')
    else:
        cargos = Cargo.objects.none()
    
    context = {
        'cargos': cargos,
    }
    return render(request, 'branch-all-cargos.html', context)

@login_required
def registered_cargos_view(request):
    """View for registered cargos at the agent's branch"""
    from cargo_management.models import CargoCenter, Vehicle
    
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    if agent_branch:
        # Get registered cargos originating from this branch
        cargos = Cargo.objects.filter(
            origin_branch=agent_branch,
            status='registered'
        ).select_related('sender', 'receiver', 'destination_branch', 'registered_by').order_by('-created_at')
    else:
        cargos = Cargo.objects.none()
    
    # Get all branches for destination dropdown
    branches = CargoCenter.objects.all().order_by('location')
    
    # Get all active vehicles for shipping
    vehicles = Vehicle.objects.filter(is_active=True).order_by('plate_number')
    
    context = {
        'cargos': cargos,
        'branches': branches,
        'vehicles': vehicles,
    }
    return render(request, 'cargo_registered.html', context)

@login_required
def in_transit_cargos_view(request):
    """View for cargos in transit related to the agent's branch"""
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    if agent_branch:
        # Get in-transit cargos from or to this branch
        cargos = Cargo.objects.filter(
            models.Q(origin_branch=agent_branch) | models.Q(destination_branch=agent_branch),
            status='shipped'
        ).select_related('origin_branch', 'destination_branch', 'assigned_vehicle', 'registered_by').order_by('-updated_at')
    else:
        cargos = Cargo.objects.none()
    
    context = {
        'cargos': cargos,
    }
    return render(request, 'in-transit.html', context)

@login_required
def arrived_cargos_view(request):
    """View for cargos that have arrived at the agent's branch"""
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    if agent_branch:
        # Get arrived cargos at this branch (destination)
        cargos = Cargo.objects.filter(
            destination_branch=agent_branch,
            status='arrived'
        ).select_related('sender', 'receiver', 'origin_branch').order_by('-updated_at')
    else:
        cargos = Cargo.objects.none()
    
    context = {
        'cargos': cargos,
    }
    return render(request, 'arrived.html', context)

@login_required
def delivered_cargos_view(request):
    """View for delivered cargos from the agent's branch"""
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    if agent_branch:
        # Get delivered cargos from or to this branch
        cargos = Cargo.objects.filter(
            models.Q(origin_branch=agent_branch) | models.Q(destination_branch=agent_branch),
            status='delivered'
        ).select_related('sender', 'receiver', 'origin_branch', 'destination_branch', 'delivered_by_agent', 'delivered_by_agent__user').order_by('-delivered_at')
    else:
        cargos = Cargo.objects.none()
    
    context = {
        'cargos': cargos,
    }
    return render(request, 'delivered.html', context)

@login_required
def customer_delivery_view(request):
    """View for customer delivery page with QR scanner"""
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    context = {
        'agent': agent,
        'agent_branch': agent_branch,
    }
    return render(request, 'customer_delivery.html', context)

@login_required
@require_http_methods(["POST"])
def register_cargo(request):
    """Handle cargo registration from the modal form"""
    try:
        agent = request.user.agent_profile
        agent_branch = agent.office
        
        if not agent_branch:
            return JsonResponse({
                'success': False,
                'message': 'Agent branch not assigned'
            })
        
        # Get sender branch
        sender_branch = CargoCenter.objects.get(id=request.POST.get('sender_branch'))
        
        # Get or create sender
        sender, created = Customer.objects.get_or_create(
            mobile_number=request.POST.get('sender_phone'),
            defaults={
                'full_name': request.POST.get('sender_name'),
                'location': sender_branch,
            }
        )
        
        # Get receiver branch
        receiver_branch = CargoCenter.objects.get(id=request.POST.get('receiver_branch'))
        
        # Get or create receiver
        receiver, created = Customer.objects.get_or_create(
            mobile_number=request.POST.get('receiver_phone'),
            defaults={
                'full_name': request.POST.get('receiver_name'),
                'location': receiver_branch,
            }
        )
        
        # Generate cargo number: SHB{day_of_year}-{8_random_chars}-{branch_code}
        # Example: SHB098-7T63JOBG-DSM
        day_of_year = timezone.now().timetuple().tm_yday  # Day of year (1-366)
        day_str = str(day_of_year).zfill(3)  # Pad with zeros to make it 3 digits (001-366)
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        branch_code = receiver_branch.branch_code.upper()  # 3-letter branch code
        cargo_number = f'SHB{day_str}-{random_code}-{branch_code}'
        
        # Generate tracking number: 6 mixed characters (uppercase letters and digits)
        tracking_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Generate receipt number: RCP + 6 random alphanumeric
        receipt_random = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        receipt_number = f'RCP{receipt_random}'
        
        # Create cargo
        cargo = Cargo.objects.create(
            cargo_number=cargo_number,
            tracking_number=tracking_number,
            receipt_number=receipt_number,
            sender=sender,
            receiver=receiver,
            origin_branch=sender_branch,
            destination_branch=receiver_branch,
            cargo_description=request.POST.get('cargo_description'),
            quantity=request.POST.get('quantity'),
            weight=request.POST.get('weight'),
            cargo_value=request.POST.get('cargo_value'),
            shipping_amount=request.POST.get('shipping_amount'),
            status='registered',
            registered_by=agent,
        )
        
        # Handle image upload if provided
        if request.FILES.get('cargo_image'):
            cargo.cargo_image = request.FILES['cargo_image']
            cargo.save()
        
        # Send SMS notification to sender and receiver
        from sms_notification.sms_notification import send_cargo_registration_sms
        send_cargo_registration_sms(cargo)
        
        return JsonResponse({
            'success': True,
            'message': f'Cargo registered successfully!\nCargo Number: {cargo_number}\nReceipt Number: {receipt_number}',
            'cargo_number': cargo_number,
            'tracking_number': tracking_number,
            'receipt_number': receipt_number,
            'cargo_id': cargo.id
        })
        
    except CargoCenter.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Invalid destination branch selected'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error registering cargo: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def ship_cargo(request):
    """Handle cargo shipping with vehicle assignment"""
    try:
        cargo_id = request.POST.get('cargo_id')
        vehicle_id = request.POST.get('vehicle_id')
        
        # Get cargo
        cargo = Cargo.objects.get(id=cargo_id, status='registered')
        
        # Get vehicle
        vehicle = Vehicle.objects.get(id=vehicle_id, is_active=True)
        
        # Get the user who is shipping (conductor/agent)
        user = request.user
        shipped_by_agent = user.agent_profile if hasattr(user, 'agent_profile') else None
        
        # Update cargo status and assign vehicle
        cargo.status = 'shipped'
        cargo.assigned_vehicle = vehicle
        cargo.shipped_by = shipped_by_agent
        cargo.shipped_at = timezone.now()
        cargo.current_branch = cargo.origin_branch
        cargo.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Cargo {cargo.cargo_number} has been shipped successfully with vehicle {vehicle.plate_number}!'
        })
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found or already shipped'
        })
    except Vehicle.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Invalid vehicle selected'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error shipping cargo: {str(e)}'
        })

@login_required
def onboarded_cargos_view(request):
    """View for cargos that have been shipped (onboarded) from this branch"""
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    # Get all shipped cargos from this branch (waiting to be onboarded or already onboarded by conductor)
    cargos = Cargo.objects.filter(
        origin_branch=agent_branch,
        status='shipped'
    ).select_related(
        'sender', 'receiver', 'origin_branch', 'destination_branch', 'assigned_vehicle', 'registered_by'
    ).order_by('-shipped_at')
    
    context = {
        'cargos': cargos,
        'page_title': 'Onboarded Cargo',
    }
    
    return render(request, 'onboarded.html', context)

@login_required
def offboarded_cargos_view(request):
    """View for cargos that have arrived (offboarded) at this branch"""
    agent = request.user.agent_profile
    agent_branch = agent.office
    
    # Get all arrived cargos at this branch (offboarded by conductor, waiting for customer pickup)
    cargos = Cargo.objects.filter(
        destination_branch=agent_branch,
        status='arrived'
    ).select_related(
        'sender', 'receiver', 'origin_branch', 'destination_branch', 'assigned_vehicle', 'registered_by'
    ).order_by('-arrived_at')
    
    context = {
        'cargos': cargos,
        'page_title': 'Offboarded Cargo',
    }
    
    return render(request, 'offboarded.html', context)

@login_required
def generate_thermal_receipt(request, cargo_id):
    """Generate thermal receipt with QR code for a cargo"""
    try:
        cargo = Cargo.objects.select_related(
            'sender', 'receiver', 'origin_branch', 'destination_branch', 'registered_by'
        ).get(id=cargo_id)
        
        # Generate QR code containing cargo information
        qr_data = f"CARGO:{cargo.cargo_number}|RECEIPT:{cargo.receipt_number}|FROM:{cargo.origin_branch.location}|TO:{cargo.destination_branch.location}|STATUS:{cargo.status}"
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Generate QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in HTML
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        context = {
            'cargo': cargo,
            'qr_code': qr_code_base64,
            'now': timezone.now()
        }
        
        return render(request, 'thermal_receipt.html', context)
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found'
        }, status=404)

@login_required
def generate_thermal_receipt_pdf(request, cargo_id):
    """Generate thermal receipt as PDF for download"""
    try:
        cargo = Cargo.objects.select_related(
            'sender', 'receiver', 'origin_branch', 'destination_branch', 'registered_by'
        ).get(id=cargo_id)
        
        # Generate QR code containing cargo information
        qr_data = f"CARGO:{cargo.cargo_number}|RECEIPT:{cargo.receipt_number}|FROM:{cargo.origin_branch.location}|TO:{cargo.destination_branch.location}|STATUS:{cargo.status}"
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Generate QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in HTML
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        context = {
            'cargo': cargo,
            'qr_code': qr_code_base64,
            'now': timezone.now()
        }
        
        # Render HTML template
        html_string = render_to_string('thermal_receipt.html', context)
        
        # Generate PDF using xhtml2pdf
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), result)
        
        if not pdf.err:
            # Create HTTP response with PDF
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="receipt_{cargo.receipt_number}.pdf"'
            return response
        else:
            return JsonResponse({
                'success': False,
                'message': 'Error generating PDF'
            }, status=500)
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found'
        }, status=404)


@login_required
@require_http_methods(["POST"])
def deliver_cargo_api(request):
    """API endpoint to confirm cargo delivery with customer pickup details"""
    try:
        agent = request.user.agent_profile
        cargo_id = request.POST.get('cargo_id')
        
        if not cargo_id:
            return JsonResponse({
                'success': False,
                'message': 'Cargo ID is required'
            }, status=400)
        
        # Get the cargo
        cargo = Cargo.objects.get(id=cargo_id)
        
        # Verify cargo is at the agent's branch and ready for delivery
        if cargo.current_branch != agent.office:
            return JsonResponse({
                'success': False,
                'message': 'Cargo is not at your branch'
            }, status=400)
        
        if cargo.status == 'delivered':
            return JsonResponse({
                'success': False,
                'message': 'Cargo has already been delivered'
            }, status=400)
        
        # Get customer pickup details
        pickup_customer_name = request.POST.get('customer_name', '').strip()
        pickup_customer_mobile = request.POST.get('customer_mobile', '').strip()
        pickup_customer_location = request.POST.get('customer_id', '').strip()  # Using customer_id as location
        delivery_signature = request.POST.get('signature', '')
        
        # Validate required fields
        if not all([pickup_customer_name, pickup_customer_mobile, pickup_customer_location, delivery_signature]):
            return JsonResponse({
                'success': False,
                'message': 'All customer pickup details and signature are required'
            }, status=400)
        
        # Update cargo with delivery information
        cargo.status = 'delivered'
        cargo.delivered_at = timezone.now()
        cargo.delivered_by_agent = agent
        cargo.pickup_customer_name = pickup_customer_name
        cargo.pickup_customer_mobile = pickup_customer_mobile
        cargo.pickup_customer_location = pickup_customer_location
        cargo.delivery_signature = delivery_signature
        cargo.save()
        
        # Send SMS notification to both sender and receiver
        from sms_notification.sms_notification import send_cargo_pickup_sms
        send_cargo_pickup_sms(cargo)
        
        return JsonResponse({
            'success': True,
            'message': f'Cargo {cargo.cargo_number} has been successfully delivered to {pickup_customer_name}'
        })
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def search_cargo_api(request):
    """API endpoint to search for cargo by cargo number"""
    try:
        cargo_number = request.GET.get('cargo_number', '').strip()
        
        if not cargo_number:
            return JsonResponse({
                'success': False,
                'message': 'Cargo number is required'
            }, status=400)
        
        # Search for cargo
        cargo = Cargo.objects.select_related(
            'sender', 'receiver', 'origin_branch', 'destination_branch'
        ).get(cargo_number=cargo_number)
        
        # Return cargo details
        return JsonResponse({
            'success': True,
            'cargo': {
                'id': cargo.id,
                'cargo_number': cargo.cargo_number,
                'receipt_number': cargo.receipt_number,
                'sender_name': cargo.sender.full_name,
                'sender_phone': cargo.sender.mobile_number,
                'receiver_name': cargo.receiver.full_name,
                'receiver_phone': cargo.receiver.mobile_number,
                'origin': cargo.origin_branch.location,
                'destination': cargo.destination_branch.location,
                'description': cargo.cargo_description,
                'quantity': cargo.quantity,
                'weight': str(cargo.weight) if cargo.weight else 'N/A',
                'cargo_value': str(cargo.cargo_value),
                'shipping_fee': str(cargo.shipping_amount),
                'status': cargo.status
            }
        })
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found with this number'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)

@login_required
def cargo_details_api(request, cargo_id):
    """API endpoint to get cargo details by ID"""
    try:
        # Get cargo by ID
        cargo = Cargo.objects.select_related(
            'sender', 'receiver', 'origin_branch', 'destination_branch'
        ).get(id=cargo_id)
        
        # Return cargo details
        return JsonResponse({
            'success': True,
            'cargo': {
                'id': cargo.id,
                'cargo_number': cargo.cargo_number,
                'receipt_number': cargo.receipt_number,
                'tracking_number': cargo.tracking_number,
                'sender_name': cargo.sender.full_name,
                'sender_phone': cargo.sender.mobile_number,
                'receiver_name': cargo.receiver.full_name,
                'receiver_phone': cargo.receiver.mobile_number,
                'origin': cargo.origin_branch.location,
                'destination': cargo.destination_branch.location,
                'description': cargo.cargo_description,
                'quantity': cargo.quantity,
                'weight': str(cargo.weight) if cargo.weight else 'N/A',
                'cargo_value': str(cargo.cargo_value),
                'shipping_amount': str(cargo.shipping_amount),
                'status': cargo.status,
                'cargo_image': cargo.cargo_image.url if cargo.cargo_image else None
            }
        })
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_cargo_api(request, cargo_id):
    """API endpoint to delete a cargo registration"""
    try:
        # Get cargo by ID
        cargo = Cargo.objects.get(id=cargo_id)
        
        # Check if cargo is still in registered status (not yet onboarded)
        if cargo.status != 'registered':
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete cargo. Current status: {cargo.status}'
            }, status=400)
        
        # Store cargo number for response
        cargo_number = cargo.cargo_number
        
        # Delete the cargo
        cargo.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Cargo {cargo_number} deleted successfully'
        })
        
    except Cargo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Cargo not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def create_cargo_group_api(request):
    """API endpoint to create a cargo group for multiple onboarding"""
    import json
    from cargo_management.models import CargoGroup
    
    try:
        data = json.loads(request.body)
        cargo_ids = data.get('cargo_ids', [])
        
        if not cargo_ids:
            return JsonResponse({
                'success': False,
                'message': 'No cargos selected'
            }, status=400)
        
        # Get the cargos
        cargos = Cargo.objects.filter(id__in=cargo_ids, status='registered')
        
        if cargos.count() != len(cargo_ids):
            return JsonResponse({
                'success': False,
                'message': 'Some cargos are not available or already onboarded'
            }, status=400)
        
        # Generate unique group ID
        group_id = f"CG-{timezone.now().strftime('%Y%m%d%H%M%S')}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        
        # Create QR code data (group ID)
        qr_code_data = group_id
        
        # Create cargo group
        cargo_group = CargoGroup.objects.create(
            group_id=group_id,
            qr_code_data=qr_code_data,
            created_by=request.user,
            status='pending'
        )
        
        # Add cargos to the group
        cargo_group.cargos.set(cargos)
        
        return JsonResponse({
            'success': True,
            'group_id': group_id,
            'cargo_count': cargos.count(),
            'message': f'Successfully created cargo group with {cargos.count()} cargos'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)

@login_required
def generate_cargo_group_pdf(request, group_id):
    """Generate landscape PDF for cargo group with QR code"""
    from cargo_management.models import CargoGroup
    from django.template.loader import get_template
    
    try:
        cargo_group = CargoGroup.objects.prefetch_related(
            'cargos__sender',
            'cargos__receiver',
            'cargos__origin_branch',
            'cargos__destination_branch'
        ).get(group_id=group_id)
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(cargo_group.qr_code_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert QR code to base64
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Prepare context
        context = {
            'cargo_group': cargo_group,
            'cargos': cargo_group.cargos.all(),
            'qr_code': qr_base64,
            'generated_date': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'agent_name': request.user.get_full_name()
        }
        
        # Render template
        template = get_template('cargo_group_pdf.html')
        html = template.render(context)
        
        # Create PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="cargo_group_{group_id}.pdf"'
        
        pisa_status = pisa.CreatePDF(html, dest=response)
        
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=500)
        
        return response
        
    except CargoGroup.DoesNotExist:
        return HttpResponse('Cargo group not found', status=404)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

@login_required
def multiple_cargo_print_view(request, group_id):
    """Render the print page for multiple cargo group"""
    from cargo_management.models import CargoGroup
    
    try:
        cargo_group = CargoGroup.objects.prefetch_related(
            'cargos__sender',
            'cargos__receiver',
            'cargos__origin_branch',
            'cargos__destination_branch',
            'cargos__registered_by__user'
        ).get(group_id=group_id)
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(cargo_group.qr_code_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert QR code to base64
        buffer = io.BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Prepare context
        context = {
            'cargo_group': cargo_group,
            'cargos': cargo_group.cargos.all(),
            'qr_code': qr_base64,
            'generated_date': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'agent_name': request.user.get_full_name()
        }
        
        return render(request, 'multiple_cargo_print.html', context)
        
    except CargoGroup.DoesNotExist:
        return HttpResponse('Cargo group not found', status=404)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)
