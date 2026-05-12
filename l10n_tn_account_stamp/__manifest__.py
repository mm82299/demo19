# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Tunisian Stamp Tax",
    "version": "19.0.1.0.0",
    "category": "Localization/Tunisia",
    "summary": "Automatic management of the Stamp Tax",
    "author": "Infotech Cnsulting Services, "
    "Montassar Ben Abdelkader",
    "website": "https://ics-tunisie.com",
    "license": "OPL-1",
    "depends": [
        "account",
        "l10n_tn",
    ],
    "data": [
        "views/account_move_view.xml",
        "views/account_tax_views.xml",
        "views/account_account_views.xml",
    ],
    'images': [
        'static/description/stamp_tax.png'
    ],
    'price': 50.00,
    'currency': 'USD',
    "installable": True,
}
