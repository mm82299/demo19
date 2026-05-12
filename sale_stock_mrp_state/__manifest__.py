{
    'name': 'Sale Stock MRP State Tracking',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Add state_id related fields to Sale, Stock, and MRP',
    'description': """
        Adds a state_id field to:
        - Sale Order (related to shipping partner)
        - Stock Picking (related to partner)
        - MRP Production (related to sale order shipping partner)
    """,
    'author': 'Antigravity',
    'depends': ['sale', 'stock', 'mrp', 'sale_mrp', 'sale_stock'],
    'data': [
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
