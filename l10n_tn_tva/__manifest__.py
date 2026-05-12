# -*- coding: utf-8 -*-
#############################################################################
#
#    Infotech Consulting Services Pvt. Ltd.
#
#    Copyright (C) 2020-TODAY Infotech Consulting Services(<https://www.ics-tunisie.com>)
#    Author: Infotech Consulting Services(<http://www.ics-tunisie.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

{
    'name': "Retenue à la Source TVA Tunisien",
    'summary': """
         Retenue à la Source TVA""",
    'description': """
        Retenue à la Source TVA
    """,
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['base', 'account', 'l10n_tn'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_withholding_sequence.xml',
        'views/res_partner_views.xml',
        'views/ics_withholding_tax_views.xml',
        'views/withholding_tax_view.xml',
        'views/account_move_view.xml',
    ],
    'license': 'OPL-1',
    'currency': 'EUR',
    'price': 100.0,
    'installable': True,
    'application': True,
    'auto_install': False,
}
