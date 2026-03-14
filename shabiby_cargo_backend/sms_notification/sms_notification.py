"""
SMS Notification Module for Shabiby Cargo
Handles sending SMS notifications via Beem Africa API
"""

import base64
import requests
import re
from django.utils import timezone


def _normalize_msisdn_tz(phone_number):
    """
    Normalize Tanzanian phone numbers to international format
    Accepts: 0712345678, 712345678, +255712345678, 255712345678
    Returns: 255712345678
    """
    if not phone_number:
        return None
    
    # Remove all non-digit characters except +
    phone = re.sub(r'[^\d+]', '', str(phone_number))
    
    # Remove leading +
    phone = phone.lstrip('+')
    
    # Handle different formats
    if phone.startswith('255'):
        # Already in international format
        return phone
    elif phone.startswith('0'):
        # Remove leading 0 and add country code
        return '255' + phone[1:]
    elif len(phone) == 9:
        # Missing country code and leading 0
        return '255' + phone
    else:
        # Invalid format
        return None


def send_sms_notification(phone_number, message):
    """Helper function to send SMS via Beem Africa API"""
    try:
        # SMS API Configuration
        api_key = 'fc4c4dd2f7efa4b4'  # TODO: Move to .env after testing
        secret_key = 'MWQ5NmVhNTU4ZDgxMGVkNGRhYjg0NjRiYmFmYWZhOTBiOTMxMzRiOWM1MjRkY2U5M2JkMTQyNmQ3MDA3YzNhNg=='  # TODO: Move to .env after testing
        
        if not api_key or not secret_key:
            print("Missing Beem Africa API credentials")
            return False
            
        # Normalize phone number
        normalized_phone = _normalize_msisdn_tz(phone_number)
        if not normalized_phone:
            print(f"Invalid phone number for SMS: {phone_number}")
            return False
            
        # Prepare API request
        url = "https://apisms.beem.africa/v1/send"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:{secret_key}'.encode()).decode()}"
        }
        
        payload = {
            "source_addr": "ELOHIM LTD",
            "schedule_time": "",
            "encoding": 0,
            "message": message,
            "recipients": [
                {
                    "recipient_id": 1,
                    "dest_addr": normalized_phone
                }
            ]
        }
        
        # Send SMS
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # Log SMS attempt
        try:
            with open("/tmp/sms_debug.log", "a") as sms_file:
                now = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                sms_file.write(f"=== SMS Attempt at {now} ===\n")
                sms_file.write(f"Phone: {normalized_phone}\n")
                sms_file.write(f"Message: {message}\n")
                sms_file.write(f"Status Code: {response.status_code}\n")
                sms_file.write(f"Response: {response.text}\n")
                if response.status_code == 200:
                    sms_file.write("■ SUCCESS\n")
                else:
                    sms_file.write("■ FAILED\n")
                sms_file.write("\n")
        except Exception as log_error:
            print(f"Error writing to SMS log: {str(log_error)}")
            
        if response.status_code == 200:
            print(f"■ SMS sent successfully to {normalized_phone}: {message}")
            return True
        else:
            print(f"■ Failed to send SMS to {normalized_phone}. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        # Log error
        try:
            with open("/tmp/sms_debug.log", "a") as sms_file:
                now = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                sms_file.write(f"=== SMS Error at {now} ===\n")
                sms_file.write(f"Phone: {phone_number}\n")
                sms_file.write(f"Error: {str(e)}\n")
                sms_file.write("■ ERROR\n\n")
        except Exception as log_error:
            print(f"Error writing to SMS log: {str(log_error)}")
            
        print(f"■ Error sending SMS to {phone_number}: {str(e)}")
        return False


def send_cargo_registration_sms(cargo):
    """
    Send SMS notification when cargo is registered
    Sends to both sender and receiver
    """
    try:
        # SMS message in Swahili for sender
        sender_message = (
            f"SHABIBY CARGO\n"
            f"Parcel No: {cargo.cargo_number}\n"
            f"Habari {cargo.sender.name}, tunapenda kukujulisha kuwa mzigo wako "
            f"kutoka {cargo.origin_branch.name} kwenda {cargo.destination_branch.name} "
            f"umepokelewa katika ghala letu. "
            f"Gharama ya usafirishaji: TZS {float(cargo.shipping_amount):,.0f}. "
            f"Mzigo utaondoka haraka iwezekanavyo. "
            f"Asante kwa kusafirisha na SHABIBY CARGO. "
        )
        
        # SMS message in Swahili for receiver
        receiver_message = (
            f"SHABIBY CARGO\n"
            f"Parcel No: {cargo.cargo_number}\n"
            f"Habari {cargo.receiver.name}, tunapenda kukujulisha kuwa mzigo wako "
            f"kutoka {cargo.origin_branch.name} kwenda {cargo.destination_branch.name} "
            f"umepokelewa katika ghala letu. "
            f"Gharama ya usafirishaji: TZS {float(cargo.shipping_amount):,.0f}. "
            f"Mzigo utaondoka haraka iwezekanavyo. "
            f"Asante kwa kusafirisha na SHABIBY CARGO. "
        )
        
        # Send to sender
        sender_sent = False
        if cargo.sender.phone:
            sender_sent = send_sms_notification(cargo.sender.phone, sender_message)
        
        # Send to receiver
        receiver_sent = False
        if cargo.receiver.phone:
            receiver_sent = send_sms_notification(cargo.receiver.phone, receiver_message)
        
        return sender_sent or receiver_sent
        
    except Exception as e:
        print(f"Error sending cargo registration SMS: {str(e)}")
        return False


def send_cargo_arrival_sms(cargo):
    """
    Send SMS notification when cargo arrives at destination branch
    Sends to receiver only
    """
    try:
        # SMS message in Swahili for receiver
        receiver_message = (
            f"SHABIBY CARGO\n"
            f"Parcel No: {cargo.cargo_number}\n"
            f"Habari {cargo.receiver.name}, tunapenda kukujulisha kuwa mzigo wako "
            f"kutoka {cargo.origin_branch.name} kwenda {cargo.destination_branch.name} "
            f"umefika salama katika ofisi yetu ya {cargo.destination_branch.name}. "
            f"Tafadhali njoo kuchukua mzigo wako."
            f"Asante kwa kusafirisha na SHABIBY CARGO. "
        )
        
        # Send to receiver
        if cargo.receiver.phone:
            return send_sms_notification(cargo.receiver.phone, receiver_message)
        
        return False
        
    except Exception as e:
        print(f"Error sending cargo arrival SMS: {str(e)}")
        return False


def send_cargo_pickup_sms(cargo):
    """
    Send SMS notification when cargo is picked up/delivered
    Sends to both sender and receiver
    """
    try:
        # Get the actual person who picked up the cargo
        pickup_person = cargo.pickup_customer_name if cargo.pickup_customer_name else cargo.receiver.name
        
        # SMS message in Swahili for sender
        sender_message = (
            f"SHABIBY CARGO\n"
            f"Parcel No: {cargo.cargo_number}\n"
            f"Habari {cargo.sender.name}, tunapenda kukujulisha kuwa mzigo wako "
            f"kutoka {cargo.origin_branch.name} kwenda {cargo.destination_branch.name} "
            f"umepokelewa leo tarehe {timezone.now().strftime('%d/%m/%Y')} saa {timezone.now().strftime('%H:%M')}. "
            f"Asante kwa kusafirisha na SHABIBY CARGO. "
        )
        
        # SMS message in Swahili for receiver
        receiver_message = (
            f"SHABIBY CARGO\n"
            f"Shipment No: {cargo.cargo_number}\n"
            f"Message: Habari {cargo.receiver.name}, tunapenda kukujulisha kuwa mzigo wako "
            f"kutoka {cargo.origin_branch.name} kwenda {cargo.destination_branch.name} "
            f"umepokelewa na {pickup_person} leo tarehe {timezone.now().strftime('%d/%m/%Y')} saa {timezone.now().strftime('%H:%M')}. "
            f"Asante kwa kusafirisha na SHABIBY CARGO. "
        )
        
        # Send to sender
        sender_sent = False
        if cargo.sender.phone:
            sender_sent = send_sms_notification(cargo.sender.phone, sender_message)
        
        # Send to receiver
        receiver_sent = False
        if cargo.receiver.phone:
            receiver_sent = send_sms_notification(cargo.receiver.phone, receiver_message)
        
        return sender_sent or receiver_sent
        
    except Exception as e:
        print(f"Error sending cargo pickup SMS: {str(e)}")
        return False
