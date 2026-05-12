# -*- coding: utf-8 -*-
{
    'name': "Retenue à la Source Tunisien Pour Odoo 19.0",
    'summary': """
        l10n_tn - Retenue à la Source Tunisien Pour Odoo 19.0""",
    'description': """
        l10n_tn - Retenue à la Source Tunisien Pour Odoo 19.0
    """,
    'category': 'Accounting',
    'version': '1.1.0',
    'license': "OPL-1",
    'author': "Infotech Consulting Services Tunisie",
    'website': "http://www.ics-tunisie.com",
    'depends': ['base', 'account', 'l10n_tn'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_withholding_sequence.xml',
        'views/l10n_tn_withholding_tax_views.xml',
        'views/withholding_tax_view.xml',
        'views/journal_custom_form.xml',
        'views/account_move_view.xml',
        'reports/report_invoice.xml',
    ],
    'images': [
        'static/description/ics_retunue.png'
    ],
    'live_test_url': 'https://youtu.be/sTDEKqBv8kA',
    'price': 150.00,
    'currency': 'USD',
    'installable': True,
    'application': True,
    'auto_install': False,
    "pre_init_hook":  "pre_init_check",
}
