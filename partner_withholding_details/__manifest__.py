# -*- coding: utf-8 -*-
{
    'name': 'Partner Withholding Rate Details',
    'version': '1.0',
    'summary': 'Partner Withholding Rate Details',
    'description': '''
        Partner Withholding Rate Details
    ''',
    'category': 'Accounting',
    'author': 'Infotech Consulting Services (ICS)',
    'company': 'Infotech Consulting Services (ICS)',
    'maintainer': 'Infotech Consulting Services (ICS)',
    'website': 'https://www.ics-tn.com',
    'depends': ['base', 'account_move_withholding', 'partner_accounting_account'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}