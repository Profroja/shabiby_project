from django.contrib import admin
from cargo_management.models import Agent, CargoCenter, Vehicle, Customer, Cargo, ShippingRate


@admin.register(CargoCenter)
class CargoCenterAdmin(admin.ModelAdmin):
    list_display = ('center_name', 'location', 'is_active', 'created_at')
    list_filter = ('is_active', 'location')
    search_fields = ('center_name', 'location')
    ordering = ('location', 'center_name')
    list_editable = ('is_active',)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'get_username', 'get_role', 'office', 'created_at')
    list_filter = ('user__role', 'office')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    raw_id_fields = ('user',)
    autocomplete_fields = ('office',)
    ordering = ('-created_at',)
    
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'Full Name'
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    
    def get_role(self, obj):
        return obj.user.get_role_display()
    get_role.short_description = 'Role'


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('plate_number', 'vehicle_type', 'vehicle_model', 'company_owner', 'max_weight', 'is_active', 'created_at')
    list_filter = ('vehicle_type', 'is_active', 'created_at')
    search_fields = ('plate_number', 'registration_number', 'vehicle_model', 'company_owner', 'chassis_number')
    ordering = ('-created_at',)
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Vehicle Information', {
            'fields': ('vehicle_type', 'vehicle_model', 'company_owner')
        }),
        ('Registration Details', {
            'fields': ('registration_number', 'plate_number', 'chassis_number')
        }),
        ('Capacity & Status', {
            'fields': ('max_weight', 'is_active')
        }),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile_number', 'location', 'created_at')
    list_filter = ('location', 'created_at')
    search_fields = ('full_name', 'mobile_number')
    ordering = ('-created_at',)
    autocomplete_fields = ('location',)


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'status', 'origin_branch', 'destination_branch', 'shipping_amount', 'created_at')
    list_filter = ('status', 'origin_branch', 'destination_branch', 'created_at')
    search_fields = ('sender__full_name', 'receiver__full_name', 'cargo_description')
    ordering = ('-created_at',)
    list_editable = ('status',)
    autocomplete_fields = ('sender', 'receiver', 'origin_branch', 'destination_branch', 'current_branch', 'registered_by', 'assigned_vehicle')
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('sender', 'receiver')
        }),
        ('Cargo Details', {
            'fields': ('cargo_description', 'cargo_value', 'quantity', 'shipping_amount')
        }),
        ('Branch Information', {
            'fields': ('origin_branch', 'destination_branch', 'current_branch')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'registered_by', 'assigned_vehicle')
        }),
        ('Timestamps', {
            'fields': ('shipped_at', 'arrived_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ('origin_branch', 'destination_branch', 'base_rate', 'rate_per_kg', 'is_active', 'created_at')
    list_filter = ('is_active', 'origin_branch', 'destination_branch', 'created_at')
    search_fields = ('origin_branch__center_name', 'destination_branch__center_name', 'origin_branch__location', 'destination_branch__location')
    ordering = ('origin_branch', 'destination_branch')
    list_editable = ('is_active',)
    autocomplete_fields = ('origin_branch', 'destination_branch')
    
    fieldsets = (
        ('Route Information', {
            'fields': ('origin_branch', 'destination_branch')
        }),
        ('Pricing', {
            'fields': ('base_rate', 'rate_per_kg')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
