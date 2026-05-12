# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_apply_warranty_retention_ht(self):
        """ Applies 'Retenue de Garantie (10% HT)' to all invoice lines. """
        tax_ht = self.env.ref('mphe_account_warranty_retention.tax_warranty_retention_ht', raise_if_not_found=False)
        if not tax_ht:
            return
        
        for move in self:
            for line in move.invoice_line_ids:
                if tax_ht not in line.tax_ids:
                    line.tax_ids = [(4, tax_ht.id)]
    
    def action_apply_warranty_retention_ttc(self):
        """ Applies 'Retenue de Garantie (10% TTC)' to all invoice lines. """
        tax_ttc = self.env.ref('mphe_account_warranty_retention.tax_warranty_retention_ttc', raise_if_not_found=False)
        if not tax_ttc:
            return

        for move in self:
            for line in move.invoice_line_ids:
                if tax_ttc not in line.tax_ids:
                    line.tax_ids = [(4, tax_ttc.id)]
