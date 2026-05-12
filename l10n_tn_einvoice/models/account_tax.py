# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountTax(models.Model):
    _inherit = 'account.tax'

    ttn_code = fields.Selection([

        ('I-160', 'I-160 - Taxes RB )non soumis à la TVA)'),
        ('I-161', 'I-161 - Droit de Consommation'),
        ('I-162', 'I-162 - Taxe professionnelle de compétitivité FODEC'),
        ('I-163', 'I-163 - Taxe sur les emballages métalliques'),
        ('I-164', 'I-164 - Taxe pour la protection de l’environnement TPE'),
        ('I-165', 'I-165 - TTaxe au profit du fonds de développement de la compétitivité dans le secteur du tourisme (FODET)'),
        ('I-166', 'I-166 - Taxe sur les climatiseurs'),
        ('I-167', 'I-167 - Taxes sur les lampes et les tubes'),
        ('I-168', 'I-168 - Taxes sur fruit et légumes (TFL) non soumis à la TVA'),
        ('I-169', 'I-169 - Taxes sur les produits de la pèche )non soumis à la TVA)'),
        ('I-1601', 'I-1601 - Droit de Timbre'),
        ('I-1602', 'I-1602 - TVA'),
        ('I-1603', 'I-1603 - Autres'),
        ('I-1604', 'I-1604 - Retenue à la Source'),
    ], string='Code TTN',
       help='Code de référence TTN pour la facture électronique TEIF')

    ttn_tax_category = fields.Char(
        string='Catégorie Taxe TTN',
        help='Code de catégorie pour la taxe (optionnel)'
    )

    @api.onchange('amount', 'amount_type')
    def _onchange_amount_ttn_code(self):
        """Auto-suggest TTN code based on tax configuration"""
        if self.amount_type == 'percent':
            if self.amount in [19.0, 13.0, 7.0]:
                self.ttn_code = 'I-1602'  # TVA
            elif self.amount == 1.0:
                self.ttn_code = 'I-161'  # FOPROLOS
            elif self.amount < 0:
                self.ttn_code = 'I-1604'  # Retenue à la source
        elif self.amount_type == 'fixed':
            if self.amount == 0.600 or self.amount == 1.000:
                self.ttn_code = 'I-1601'  # Droit de timbre

    def get_ttn_tax_name(self):
        """Get TTN tax name based on code"""
        self.ensure_one()
        tax_names = {
            'I-1601': 'Droit de Timbre',
            'I-1602': 'TVA',
            'I-1603': 'FOPROLOS',
            'I-1604': 'Retenue à la Source',
            'I-1605': 'TCL',
            'I-1606': 'Taxe Hôtelière',
            'I-1607': 'Taxe de Compensation',
            'I-1608': 'Droit de Consommation',
            'I-1609': 'TUC',
            'I-1610': 'Autre Taxe',
        }
        return tax_names.get(self.ttn_code, self.name)
