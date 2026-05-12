# Copyright 2019 Tecnativa S.L. - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Exemption Certificate',
    'version': '19.0.0.1',
    'category': 'Partner',
    'author': 'Infotech Consulting Services (ICS)',
    'website': 'https://www.ics-tunisie.com',
    'license': 'AGPL-3',
    'depends': [
        'base', 'account'
    ],
    'data': [
        'views/exemption_certificate.xml',
        'views/tax_exception.xml',
        'security/ir.model.access.csv',


    ],
    "price": 30.0,
    "currency": 'EUR',
    'application': False,
    'installable': True,
    'images': ['static/description/banner.png'],
}
