# -*- coding: utf-8 -*-
{
    'name': 'Tunisia E-Invoicing (TEIF Elfatoora)',
    'version': '19.0.1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Tunisian Electronic Invoice Format (TEIF) with ANCE Integration',
    'description': """
Tunisia E-Invoicing - TEIF Format & NGSign Integration
=======================================================
* Generate TEIF XML v1.8.9 compliant invoices
* Sign invoices with NGSign API (SEAL method)
* Submit to TTN (Tunisie TradeNet)
* Retrieve QR Code and TTN Reference
* Full compliance with Tunisian e-invoicing regulations

Requirements:
-------------
- ANCE enterprise account with API access
- Valid Tunisian fiscal matricule
    """,
    'author': 'Infotech Cosnulting Services (ICS)',
    'website': 'https://www.ics-tn.com',
    'depends': ['base', 'account', 'l10n_tn', 'custom_exemption_certificate'],
    'data': [
        'security/ir.model.access.csv',
        'data/teif_codes_data.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_term_views.xml',
        'views/account_tax_views.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/res_company_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
    "price": 250.0,
    "currency": 'EUR',
}
