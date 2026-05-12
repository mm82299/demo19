# -*- coding: utf-8 -*-
{
    'name': 'Account Deferred Expense',
    'version': '19.0.1.0.0',
    'summary': 'Deferred Expenses & Prepaid Expenses',
    'description': """
        Manage deferred expenses and prepaid expenses.
        Spreads costs across multiple journal entries posted periodically.
        Follows the same architecture as Odoo Enterprise account_accountant.
    """,
    'author': 'Infotech Consulting Services',
    'website': 'https://website.ics-tn.com/',
    'category': 'Accounting/Accounting',
    'sequence': 15,
    'license': 'OPL-1',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/account_deferred_report_views.xml',
        'views/menu.xml',
        'wizard/account_deferred_generate_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
