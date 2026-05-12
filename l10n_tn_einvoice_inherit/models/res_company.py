# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCompany(models.Model):
    """ This model represents res.company."""
    _inherit = 'res.company'

    ttn_vat_number_type = fields.Selection([
        ('vat13', 'Matricule fiscal sur 13 chiffres'),
        ('vat8', 'Matricule fiscal sur 8 chiffres')
    ], string='Type de matricule fiscal', default='vat13')

    def get_tn_fiscal_id(self):
        """Get clean Tunisian fiscal ID without country prefix"""
        self.ensure_one()
        if self.vat:
            if self.ttn_vat_number_type == 'vat13':
                return self.vat.replace('TN', '').replace('tn', '')
            elif self.ttn_vat_number_type == 'vat8':
                return self.vat.replace('TN', '').replace('tn', '')[:8]
            else :
                return self.vat.replace('TN', '').replace('tn', '')
        return False
