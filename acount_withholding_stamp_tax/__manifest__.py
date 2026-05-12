# -*- coding: utf-8 -*-
{
    'name': "Account Move withholding stamp tax",
    'summary': """
        Account Move withholding stamp tax""",

    'description': """
        Account Move withholding stamp tax
    """,
    'license': 'LGPL-3',
    'author': "Infotech Consulting Services (ICS)",
    'website': "http://www.ics-tn.com",
    'category': 'Accounting',
    'version': '19.0.0.1',
    'depends': ['base', 'account', 'l10n_tn_account_stamp', 'account_move_withholding'],
    'data': [
        'views/account_withholding_views.xml',
    ],
    'images': [
        'static/description/ics_retunue.png'
    ],
    'price': 15.00,
    'currency': 'USD',
    'auto_install': ['account_move_withholding'],
}
