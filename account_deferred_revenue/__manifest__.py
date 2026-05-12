# -*- coding: utf-8 -*-
{
    'name': 'Account Deferred Revenue',
    'version': '19.0.1.0.0',
    'summary': 'Deferred Revenues for Odoo Community',
    'description': """
        Manage deferred revenues (unearned revenues).
        Spreads revenues across multiple journal entries posted periodically.
        Follows the same architecture as Odoo Enterprise account_accountant.
    """,
    'author': 'Infotech Consulting Services',
    'website': 'https://website.ics-tn.com/',
    'category': 'Accounting/Accounting',
    'sequence': 16,
    'license': 'OPL-1',
    'depends': ['account', 'account_deferred_expense'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/account_deferred_report_views.xml',
        'views/menu.xml',
        'wizard/account_deferred_revenue_generate_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
