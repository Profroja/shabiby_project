from django.urls import path
from .views import LoginView, admin_dashboard, branchagent_dashboard, logout_view, calculate_shipping_fee
from conductor.views import (
    conductor_dashboard, 
    conductor_onboard, 
    conductor_offboard,
    search_cargo,
    onboard_cargo,
    offboard_cargo,
    conductor_registered_cargos_view, 
    conductor_onboarded_cargos_view, 
    conductor_offboarded_cargos_view,
    search_cargo_group,
    search_cargo_group_for_offboard,
    bulk_onboard_cargos,
    bulk_offboard_cargos
)
from admin.views import (
    agents_list_view, create_agent, update_agent, delete_agent, get_agent,
    cargo_centers_list_view, create_cargo_center, update_cargo_center, delete_cargo_center, get_cargo_center,
    vehicles_list_view, create_vehicle, update_vehicle, delete_vehicle, get_vehicle,
    shipping_fee_configs_view, create_shipping_fee_config, update_shipping_fee_config, delete_shipping_fee_config,
    all_cargos_view, delete_cargo_admin
)

urlpatterns = [
    path('api/login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('branchagent-dashboard/', branchagent_dashboard, name='branchagent_dashboard'),
    path('conductor-dashboard/', conductor_dashboard, name='conductor_dashboard'),
    path('conductor/onboard/', conductor_onboard, name='conductor_onboard'),
    path('conductor/offboard/', conductor_offboard, name='conductor_offboard'),
    path('conductor/registered-cargos/', conductor_registered_cargos_view, name='conductor_registered_cargos'),
    path('conductor/onboarded-cargos/', conductor_onboarded_cargos_view, name='conductor_onboarded_cargos'),
    path('conductor/offboarded-cargos/', conductor_offboarded_cargos_view, name='conductor_offboarded_cargos'),
    
    # Cargo API endpoints
    path('api/cargo/search/', search_cargo, name='search_cargo'),
    path('api/cargo/onboard/', onboard_cargo, name='onboard_cargo'),
    path('api/cargo/offboard/', offboard_cargo, name='offboard_cargo'),
    path('api/cargo-group/search/', search_cargo_group, name='search_cargo_group'),
    path('api/cargo-group/search-offboard/', search_cargo_group_for_offboard, name='search_cargo_group_for_offboard'),
    path('api/cargo/bulk-onboard/', bulk_onboard_cargos, name='bulk_onboard_cargos'),
    path('api/cargo/bulk-offboard/', bulk_offboard_cargos, name='bulk_offboard_cargos'),
    path('api/calculate-shipping-fee/', calculate_shipping_fee, name='calculate_shipping_fee'),
    
    path('agents/', agents_list_view, name='agents'),
    path('cargo-centers/', cargo_centers_list_view, name='cargo_centers'),
    path('vehicles/', vehicles_list_view, name='vehicles'),
    path('all-cargos/', all_cargos_view, name='admin_all_cargos'),
    
    # Admin Cargo API endpoints
    path('api/admin/cargo/delete/<int:cargo_id>/', delete_cargo_admin, name='delete_cargo_admin'),
    
    # Agent API endpoints
    path('api/agents/create/', create_agent, name='create_agent'),
    path('api/agents/<int:agent_id>/', get_agent, name='get_agent'),
    path('api/agents/<int:agent_id>/update/', update_agent, name='update_agent'),
    path('api/agents/<int:agent_id>/delete/', delete_agent, name='delete_agent'),
    
    # Cargo Center API endpoints
    path('api/cargo-centers/create/', create_cargo_center, name='create_cargo_center'),
    path('api/cargo-centers/<int:center_id>/', get_cargo_center, name='get_cargo_center'),
    path('api/cargo-centers/<int:center_id>/update/', update_cargo_center, name='update_cargo_center'),
    path('api/cargo-centers/<int:center_id>/delete/', delete_cargo_center, name='delete_cargo_center'),
    
    # Vehicle API endpoints
    path('api/vehicles/create/', create_vehicle, name='create_vehicle'),
    path('api/vehicles/<int:vehicle_id>/', get_vehicle, name='get_vehicle'),
    path('api/vehicles/<int:vehicle_id>/update/', update_vehicle, name='update_vehicle'),
    path('api/vehicles/<int:vehicle_id>/delete/', delete_vehicle, name='delete_vehicle'),
    
    # Shipping Fee Configuration
    path('shipping-fee-configs/', shipping_fee_configs_view, name='shipping_fee_configs'),
    path('api/shipping-fee-configs/create/', create_shipping_fee_config, name='create_shipping_fee_config'),
    path('api/shipping-fee-configs/update/<int:config_id>/', update_shipping_fee_config, name='update_shipping_fee_config'),
    path('api/shipping-fee-configs/delete/<int:config_id>/', delete_shipping_fee_config, name='delete_shipping_fee_config'),
]
