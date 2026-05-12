# Copyright 2019 Tecnativa S.L. - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Exemption Certificate Custom',
    'version': '19.0.1.0',
    'category': 'Partner',
    'author': 'Mourad Meziou'
              'Infotech Consulting Services (ICS)',
    'website': 'https://www.ics-tunisie.com',
    'license': 'AGPL-3',
    'depends': [
        'exemption_certificate', 'account'
    ],
    'data': [
        'views/exemption_certificate.xml',
    ],
    'application': False,
    'installable': True,
    "price": 7,
    "currency": 'EUR',
    'images': ['static/description/banner.png'],
}
