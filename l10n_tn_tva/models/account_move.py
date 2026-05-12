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


from odoo import models, api, _, fields
from odoo.exceptions import UserError
from odoo.tools import format_date


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    has_withholding_tva = fields.Boolean('Has Withholding TVA', compute="account_move_withholding_tva")
    withholding_tva_id = fields.Many2one('account.withholding.tva', string='RS de TVA', copy=False)
    is_state = fields.Boolean('Etablissement Public', related="partner_id.is_state")

    @api.depends('withholding_tva_id')
    def account_move_withholding_tva(self):
        for rec in self:
            rec.has_withholding_tva = bool(rec.withholding_tva_id)

    def action_rs_tva(self):
        vals = self.move_type
        if vals == 'out_invoice':
            types = 'out_withholding'
            withholding_tax = self.env['account.withholding.tva.tax'].search(
                [('type_withholding', '=', 'vente'), ('rate', '=', 25.0)], limit=1)
            if types == 'out_withholding':
                res = {
                    'name': _('Withholding Tax'),
                    'res_model': 'account.withholding.tva',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'view_id': self.env.ref('l10n_tn_tva.account_withholding_tva_customer_view_form').id,
                    'context': {
                        'default_partner_id': self.partner_id.id,
                        'default_type': types,
                        'default_account_withholding_tax_ids': withholding_tax.id,
                        'default_journal_id': withholding_tax.journal_id.id,
                    },
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                }
                return res

