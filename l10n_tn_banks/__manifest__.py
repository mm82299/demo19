# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Tunisia - Banks',
    'icon': '/l10n_tn_banks/static/description/icon.png',
    'countries': ['tn'],
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Automatic addition of Tunisian banks list',
    'description': """
This module adds the list of major Tunisian banks to the bank repository.
It includes names and BIC (SWIFT) codes for the primary financial institutions in Tunisia.
    """,
    'author': 'Antigravity',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'depends': ['base'],
    'data': [
        'data/res_bank_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
