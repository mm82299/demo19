# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class button_rs_view(models.Model):
    _inherit = 'account.move'

    def action_rs(self):
        if self.withholding_id:
            raise UserError(_('This invoice has already been withholiding'))

        vals = self.move_type
        print(vals)
        if vals == 'out_invoice':
            types = 'out_withholding'
            withholding_tax = self.env['account.withholding.tax'].search([('type_withholding', '=', 'vente')], limit=1)
        elif vals == 'in_invoice':
            types = 'in_withholding'
            withholding_tax = self.env['account.withholding.tax'].search(
                [('type_withholding', '=', 'achat'), ('rate', '=', 1.0)], limit=1)

        if types == 'out_withholding' and withholding_tax:
            res = {
                'name': ('Retenue à la Source'),
                'res_model': 'account.withholding',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': self.env.ref('l10n_tn_ras.account_withholding_customer_view_form').id,
                'context': {
                    'default_partner_id': self.partner_id.id,
                    'default_type': types,
                    'default_journal_id': withholding_tax.journal_id.id,
                    'default_account_withholding_tax_ids': withholding_tax.id
                },
                'target': 'new',
                'type': 'ir.actions.act_window',
            }
        elif types == 'in_withholding' and withholding_tax:
            res = {
                'name': ('Retenue à la Source'),
                'res_model': 'account.withholding',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': self.env.ref('l10n_tn_ras.account_withholding_vendor_view_form').id,
                'context': {
                    'default_partner_id': self.partner_id.id,
                    'default_type': types,
                    'default_journal_id': withholding_tax.journal_id.id,
                    'default_account_withholding_tax_ids': withholding_tax.id
                },
                'target': 'new',
                'type': 'ir.actions.act_window',
                }
        else:
            raise UserError(_("Vous ne pouvez pas accéder a ce document"))
        return res