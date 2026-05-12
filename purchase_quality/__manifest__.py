{
    'name': 'Purchase Date Quality',
    'version': '1.0',
    'category': 'Purchases',
    'summary': 'Tracks date quality delays in Purchase Requests and Purchase Orders.',
    'depends': ['purchase', 'purchase_stock', 'purchase_request'],
    'data': [
        'views/purchase_request_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
