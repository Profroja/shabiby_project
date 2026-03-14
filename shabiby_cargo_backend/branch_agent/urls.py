from django.urls import path
from . import views

urlpatterns = [
    path('all-cargos/', views.all_cargos_view, name='branchagent_all_cargos'),
    path('registered-cargos/', views.registered_cargos_view, name='branchagent_registerd'),
    path('in-transit/', views.in_transit_cargos_view, name='in_transit_cargos'),
    path('onboarded/', views.onboarded_cargos_view, name='onboarded_cargos'),
    path('offboarded/', views.offboarded_cargos_view, name='branchagent_offboarded_cargos'),
    path('arrived/', views.arrived_cargos_view, name='arrived_cargos'),
    path('delivered/', views.delivered_cargos_view, name='branchagent_delivered_cargos'),
    path('customer-delivery/', views.customer_delivery_view, name='customer_delivery'),
    path('register-cargo/', views.register_cargo, name='register_cargo'),
    path('ship-cargo/', views.ship_cargo, name='ship_cargo'),
    path('thermal-receipt/<int:cargo_id>/', views.generate_thermal_receipt, name='thermal_receipt'),
    path('thermal-receipt-pdf/<int:cargo_id>/', views.generate_thermal_receipt_pdf, name='thermal_receipt_pdf'),
    
    # API endpoints
    path('api/cargo/deliver/', views.deliver_cargo_api, name='api_deliver_cargo'),
    path('api/cargo/search/', views.search_cargo_api, name='api_search_cargo'),
    path('api/cargo/details/<int:cargo_id>/', views.cargo_details_api, name='api_cargo_details'),
    path('api/cargo/delete/<int:cargo_id>/', views.delete_cargo_api, name='api_delete_cargo'),
    path('api/create-cargo-group/', views.create_cargo_group_api, name='api_create_cargo_group'),
    path('cargo-group-pdf/<str:group_id>/', views.generate_cargo_group_pdf, name='cargo_group_pdf'),
    path('multiple-cargo-print/<str:group_id>/', views.multiple_cargo_print_view, name='multiple_cargo_print'),
]
