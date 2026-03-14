from django.contrib import admin
from .models import CargoGroup, Cargo

# Register your models here.

@admin.register(CargoGroup)
class CargoGroupAdmin(admin.ModelAdmin):
    list_display = ['group_id', 'get_cargo_count', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['group_id', 'qr_code_data']
    readonly_fields = ['group_id', 'qr_code_data', 'created_at', 'created_by']
    filter_horizontal = ['cargos']
    
    def get_cargo_count(self, obj):
        return obj.cargos.count()
    get_cargo_count.short_description = 'Cargo Count'
