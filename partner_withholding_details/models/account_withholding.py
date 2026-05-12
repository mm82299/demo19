from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError


class AccountWithholding(models.Model):
    _inherit = 'account.withholding'

    account_withholding_tax_ids = fields.Many2one(
        'account.withholding.tax',
        string='Type de retenue',
        domain="[('company_id', '=', company_id)]",
        required=True,
        tracking=True,
        default=lambda self: self._get_default_withholding_tax()
    )

    @api.model
    def _get_default_withholding_tax(self):
        """Default value for account_withholding_tax_ids based on context."""
        partner_id = self._context.get('default_partner_id')
        type_val = self._context.get('default_type')
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            return self._compute_withholding_tax_id(partner, type_val)
        return False

    @api.model
    def _compute_withholding_tax_id(self, partner, type_val):
        """Helper method to get the correct withholding tax id."""
        if type_val == 'out_withholding' and partner.is_customer:
            return partner.customer_account_withholding.id
        elif type_val == 'in_withholding' and partner.is_supplier:
            return partner.vendor_account_withholding.id
        return False

    @api.onchange('partner_id', 'type')
    def _onchange_withholding_tax(self):
        """Update withholding tax when partner or type changes."""
        if self.partner_id and self.type:
            self.account_withholding_tax_ids = self.env['account.withholding.tax'].browse(
                self._compute_withholding_tax_id(self.partner_id, self.type)
            )
        else:
            self.account_withholding_tax_ids = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_rs(self):
        if self.withholding_id:
            raise UserError(_('This invoice has already a withholding deducted'))
        vals = self.move_type
        if vals == 'out_invoice':
            types = 'out_withholding'
            if not self.partner_id.customer_account_withholding:
                raise UserError(_('Please Define Withholding Account in customer details'))
            withholding_tax = self.partner_id.customer_account_withholding
        elif vals == 'in_invoice':
            types = 'in_withholding'
            if not self.partner_id.vendor_account_withholding:
                raise UserError(_('Please Define Withholding Account in customer details'))
            withholding_tax = self.partner_id.vendor_account_withholding
        if  vals == 'out_invoice' and types == 'out_withholding' and withholding_tax:
            res = {
                'name': ('Retenue à la Source'),
                'res_model': 'account.withholding',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': self.env.ref('l10n_tn_ras.account_withholding_customer_view_form').id,
                'context': {
                    'default_partner_id': self.partner_id.id,
                    'default_type': types,
                    'default_account_withholding_tax_ids': withholding_tax.id,
                },
                'target': 'new',
                'type': 'ir.actions.act_window',
            }
        elif vals == 'in_invoice' and types == 'in_withholding' and withholding_tax:
            res = {
                'name': ('Retenue à la Source'),
                'res_model': 'account.withholding',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': self.env.ref('l10n_tn_ras.account_withholding_vendor_view_form').id,
                'context': {
                    'default_partner_id': self.partner_id.id,
                    'default_type': types,
                    'default_account_withholding_tax_ids': withholding_tax.id,
                },
                'target': 'new',
                'type': 'ir.actions.act_window',
            }
        else:
            raise UserError(_("Please contact your administrator there is no withholding account defined for this type of invoice."))
        return res