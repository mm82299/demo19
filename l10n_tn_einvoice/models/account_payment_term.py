# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    ttn_payment_terms_code = fields.Selection([
        ('I-111', 'Basic'),
        ('I-112', 'A une date fixe'),
        ('I-113', 'Avec une période de grâce'),
        ('I-114', 'Par virement bancaire'),
        ('I-115', 'Exclusivement aux bureaux postaux'),
        ('I-116', 'Autre'),
        ('I-117', 'Par facilité'),
    ], string='Code Conditions de Paiement TTN',
        help='Code de référence TTN pour les conditions de paiement')

    ttn_payment_means_code = fields.Selection([
        ('I-131', 'Espèces'),
        ('I-132', 'Chèque'),
        ('I-133', 'Chèque certifié'),
        ('I-134', 'Prélèvement bancaire'),
        ('I-135', 'Virement bancaire'),
        ('I-136', 'Swift'),
        ('I-137', 'Autre'),
    ], string='Code Moyen de Paiement TTN',
        help='Code de référence TTN pour le moyen de paiement')

    ttn_payment_condition_code = fields.Selection([
        ('I-121', 'Paiement directe'),
        ('I-122', 'A travers une institution financière spécifique'),
        ('I-123', 'Quelle que soit la banque'),
        ('I-124', 'Autre'),
    ], string='Code Condition de Paiement TTN',
        default='I-121',
        help='Statut du paiement')

    ttn_payment_institution_code = fields.Selection([
        ('I-141', 'Poste'),
        ('I-142', 'Banque'),
        ('I-143', 'Autre'),
    ], string='Code Condition de Paiement TTN',
        default='I-142',
        help='Statut du paiement')

    ttn_financial_institution = fields.Many2one(
        'res.bank',
        string='Institution Financière',
        help='Banque ou institution pour le paiement'
    )

    @api.onchange('line_ids')
    def _onchange_line_ids_ttn_code(self):
        """Auto-suggest TTN payment code based on payment term configuration"""
        if self.line_ids:
            total_days = sum(line.days for line in self.line_ids)
            if total_days == 0:
                self.ttn_payment_terms_code = 'I-116'  # Paiement à la livraison
            elif total_days <= 30:
                self.ttn_payment_terms_code = 'I-112'  # Paiement total
            else:
                self.ttn_payment_terms_code = 'I-113'  # Paiement différé

    def get_ttn_payment_description(self):
        """Generate TTN payment description"""
        self.ensure_one()
        descriptions = []

        if self.ttn_payment_terms_code:
            terms_desc = dict(self._fields['ttn_payment_terms_code'].selection).get(self.ttn_payment_terms_code)
            descriptions.append(terms_desc)

        if self.ttn_payment_means_code:
            means_desc = dict(self._fields['ttn_payment_means_code'].selection).get(self.ttn_payment_means_code)
            descriptions.append(f"Moyen: {means_desc}")

        if self.note:
            descriptions.append(self.note)

        return ' - '.join(filter(None, descriptions))
