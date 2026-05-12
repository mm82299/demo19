{
    'name': 'Shipyard Rental Management',
    'version': '1.0',
    'category': 'Sales/Rental',
    'summary': 'Manage shipyard locations, boats, and rentals',
    'description': """
        Shipyard Rental Management System.
        - Manage locations (docks, dry docks, hangars)
        - Manage boats and their owners
        - Handle rentals/reservations
        - Invoice generation for rent and additional services
    """,
    'author': 'Infotech Consulting Services',
    'website': 'https://website.ics-tn.com/',
    'depends': ['base', 'account', 'product'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/product_data.xml',
        'data/floor_type_data.xml',
        'views/location_rental.xml',
        'views/location_zone.xml',
        'views/location_floor_type.xml',
        'views/res_boat.xml',
        'views/menu.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}
