# -*- coding: utf-8 -*-
{
    'name': 'ICS SAV Management',
    'version': '19.0.1.0.0',
    'summary': 'Gestion du Service Après-Vente (SAV)',
    'description': '''
        Module de gestion du Service Après-Vente (SAV) pour Odoo 19.
    ''',
    'category': 'Sales/After-Sales',
    'author': 'Infotech Consulting Services',
    'website': 'https://website.ics-tn.com/',
    'depends': ['sale','stock','mail'],
    'data': [
        'security/sav_security.xml',
        'security/multi_company.xml',
        'security/ir.model.access.csv',
        'views/sav_record.xml',
        'views/res_company.xml',
        'views/res_config_settings.xml',
        'views/product_template.xml',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/product_lifecycle_rule.xml',
		'views/warranty_type.xml',
        'views/menu.xml',
],
    'license': 'LGPL-3',
    'application': True,
}