# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    has_withholding_advance = fields.Boolean('Has Withholding Advance', compute="_compute_has_withholding_advance")
    withholding_advance_id = fields.Many2one('account.withholding.advance', string='Retenue d\'avance', copy=False)
    is_state = fields.Boolean('Etablissement Public', related="partner_id.is_state")

    @api.depends('withholding_advance_id')
    def _compute_has_withholding_advance(self):
        for rec in self:
            rec.has_withholding_advance = bool(rec.withholding_advance_id)

    def action_open_withholding_advance(self):
        self.ensure_one()
        if self.move_type != 'out_invoice':
            return
        
        withholding_tax = self.env['account.withholding.advance.tax'].search(
            [('type_withholding', '=', 'vente')], limit=1)
            
        return {
            'name': _('Retenue d\'avance'),
            'res_model': 'account.withholding.advance',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_type': 'out_withholding',
                'default_tax_id': withholding_tax.id,
                'default_invoice_ids': [(4, self.id)],
            },
            'target': 'new',
        }


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    is_tva = fields.Boolean('Est une TVA')
