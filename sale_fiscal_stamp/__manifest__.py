{
    'name': 'Timbre Fiscal pour Ventes (Sans Facturation)',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Ajoute un timbre fiscal au devis basé sur la position fiscale',
    'description': """
        Ce module permet d'ajouter dynamiquement un timbre fiscal dans le récapitulatif des taxes
        du devis/bon de commande, sans créer de ligne de produit et sans impact sur la comptabilité
        (le timbre n'est pas transféré vers la facture).
    """,
    'author': 'Infotech Consulting Services (ICS)',
    'depends': ['sale', 'account'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
