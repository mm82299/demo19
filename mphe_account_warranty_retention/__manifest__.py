# -*- coding: utf-8 -*-
{
    'name': 'MPHE Account Warranty Retention',
    'version': '19.0.1.0',
    'summary': 'Adds Retenue de Garantie (HT and TTC) taxes and buttons to apply them to invoices.',
    'description': """
        This module allows adding two types of warranty retention taxes:
        - Retenue de Garantie (10% HT)
        - Retenue de Garantie (10% TTC)
        It adds two buttons in the account.move form to apply these taxes to all invoice lines.
    """,
    'author': 'Infotech Consulting Services (ICS)',
    'website': 'https://www.ics-tn.com',
    'category': 'Accounting',
    'depends': ['account', 'account_tax_python'],
    'data': [
        'data/account_tax_data.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
