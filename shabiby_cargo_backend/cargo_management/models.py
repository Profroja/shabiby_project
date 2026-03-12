from django.db import models
from django.conf import settings


class ShippingFeeConfig(models.Model):
    """Model for Shipping Fee Configuration based on cargo value ranges"""
    min_cargo_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Minimum cargo value for this fee range"
    )
    max_cargo_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Maximum cargo value for this fee range"
    )
    shipping_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Shipping fee for this cargo value range"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shipping_fee_configs'
        verbose_name = 'Shipping Fee Configuration'
        verbose_name_plural = 'Shipping Fee Configurations'
        ordering = ['min_cargo_value']
    
    def __str__(self):
        return f"TZS {self.min_cargo_value:,.0f} - {self.max_cargo_value:,.0f} → Fee: TZS {self.shipping_fee:,.0f}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.min_cargo_value >= self.max_cargo_value:
            raise ValidationError('Minimum cargo value must be less than maximum cargo value')


class CargoCenter(models.Model):
    """Model for Cargo Centers (Branches)"""
    center_name = models.CharField(max_length=200, unique=True)
    location = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cargo_centers'
        verbose_name = 'Cargo Center'
        verbose_name_plural = 'Cargo Centers'
        ordering = ['location', 'center_name']
    
    def __str__(self):
        return f"{self.center_name} - {self.location}"


class Agent(models.Model):
    """Model for Agents - extends User model with additional information"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_profile'
    )
    office = models.ForeignKey(
        CargoCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agents'
        verbose_name = 'Agent'
        verbose_name_plural = 'Agents'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.user.role}"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def role(self):
        return self.user.get_role_display()
    
    @property
    def branch(self):
        return self.office.location if self.office else 'No Office Assigned'


class Vehicle(models.Model):
    """Model for Vehicles used in cargo transportation"""
    
    VEHICLE_TYPE_CHOICES = [
        ('truck', 'Truck'),
        ('bus', 'Bus'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('pickup', 'Pickup'),
        ('trailer', 'Trailer'),
        ('motorcycle', 'Motorcycle'),
    ]
    
    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        help_text="Type of vehicle"
    )
    vehicle_model = models.CharField(
        max_length=100,
        help_text="Vehicle model (e.g., Toyota Hilux, Isuzu FRR)"
    )
    company_owner = models.CharField(
        max_length=200,
        help_text="Company or owner name"
    )
    registration_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Vehicle registration number"
    )
    plate_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Vehicle plate number"
    )
    max_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Maximum weight capacity in tons"
    )
    chassis_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Vehicle chassis number (optional)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the vehicle is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicles'
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.plate_number} - {self.vehicle_model} ({self.get_vehicle_type_display()})"
    
    @property
    def weight_capacity(self):
        """Return formatted weight capacity"""
        return f"{self.max_weight} tons"


class Customer(models.Model):
    """Model for Customers (Senders and Receivers)"""
    full_name = models.CharField(
        max_length=200,
        help_text="Customer's full name"
    )
    mobile_number = models.CharField(
        max_length=15,
        help_text="Customer's mobile number"
    )
    location = models.ForeignKey(
        CargoCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        help_text="Customer's branch/location"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.full_name} - {self.mobile_number}"
    
    @property
    def branch_location(self):
        """Return customer's branch location"""
        return self.location.location if self.location else 'No Location'


class Cargo(models.Model):
    """Model for Cargo shipments"""
    
    STATUS_CHOICES = [
        ('registered', 'Registered'),
        ('shipped', 'Shipped (On Way)'),
        ('arrived', 'Arrival at Branch'),
        ('delivered', 'Taken by Customer'),
    ]
    
    # Cargo and Tracking Numbers
    cargo_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Cargo/Parcel number (e.g., SHB03082026-64678D)"
    )
    tracking_number = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        help_text="Tracking ID (6 mixed characters)"
    )
    
    # Sender and Receiver information
    sender = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='sent_cargos',
        help_text="Customer sending the cargo"
    )
    receiver = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='received_cargos',
        help_text="Customer receiving the cargo"
    )
    
    # Cargo details
    cargo_description = models.TextField(
        help_text="Description of the cargo"
    )
    cargo_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Declared value of the cargo"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Number of items/packages"
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight of cargo in kilograms"
    )
    
    # Shipping information
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount charged for shipping"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='registered',
        help_text="Current status of the cargo"
    )
    
    # Branch information
    origin_branch = models.ForeignKey(
        CargoCenter,
        on_delete=models.PROTECT,
        related_name='origin_cargos',
        help_text="Branch where cargo was registered"
    )
    destination_branch = models.ForeignKey(
        CargoCenter,
        on_delete=models.PROTECT,
        related_name='destination_cargos',
        help_text="Branch where cargo will be delivered"
    )
    current_branch = models.ForeignKey(
        CargoCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_cargos',
        help_text="Current location of the cargo"
    )
    
    # Agent who registered the cargo
    registered_by = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_cargos',
        help_text="Agent who registered this cargo"
    )
    
    # Agent/Conductor who shipped the cargo
    shipped_by = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipped_cargos',
        help_text="Conductor/Agent who shipped this cargo"
    )
    
    # Receipt number for thermal printer
    receipt_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique receipt number for thermal printer"
    )
    
    # Vehicle assigned (optional)
    assigned_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cargos',
        help_text="Vehicle assigned for transportation"
    )
    
    # Customer Pickup Details (who actually picked up the parcel)
    pickup_customer_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Name of person who picked up the cargo"
    )
    pickup_customer_mobile = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Mobile number of person who picked up the cargo"
    )
    pickup_customer_location = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Location/address of person who picked up the cargo"
    )
    delivery_signature = models.TextField(
        null=True,
        blank=True,
        help_text="Base64 encoded signature of person who picked up the cargo"
    )
    delivered_by_agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivered_cargos',
        help_text="Agent who handed over the cargo to customer"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'cargos'
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Cargo #{self.id} - {self.sender.full_name} to {self.receiver.full_name}"
    
    @property
    def status_display(self):
        """Return formatted status"""
        return self.get_status_display()
    
    @property
    def total_value(self):
        """Return total cargo value"""
        return self.cargo_value * self.quantity


class ShippingRate(models.Model):
    """Model for Shipping Rates between branches"""
    origin_branch = models.ForeignKey(
        CargoCenter,
        on_delete=models.CASCADE,
        related_name='origin_rates',
        help_text="Origin branch"
    )
    destination_branch = models.ForeignKey(
        CargoCenter,
        on_delete=models.CASCADE,
        related_name='destination_rates',
        help_text="Destination branch"
    )
    rate_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Shipping rate per kilogram"
    )
    base_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Base/minimum shipping rate"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rate is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shipping_rates'
        verbose_name = 'Shipping Rate'
        verbose_name_plural = 'Shipping Rates'
        ordering = ['origin_branch', 'destination_branch']
        unique_together = ['origin_branch', 'destination_branch']
    
    def __str__(self):
        return f"{self.origin_branch.location} → {self.destination_branch.location}: {self.base_rate} TZS (base) + {self.rate_per_kg} TZS/kg"
    
    def calculate_shipping_cost(self, weight_kg):
        """Calculate shipping cost based on weight"""
        return self.base_rate + (self.rate_per_kg * weight_kg)
