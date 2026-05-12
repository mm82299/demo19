from odoo import fields, models
from odoo.exceptions import ValidationError, UserError
from odoo import api, _

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    stamp_sale = fields.Many2one('account.tax', "Stam Sale", domain="[('type_tax_use', '=', 'sale')]")
    stamp_purchase = fields.Many2one('account.tax', "Stam Purchase", domain="[('type_tax_use', '=', 'purchase')]")


class AccountTax(models.Model):
    _inherit = 'account.tax'

    is_stamp_sale = fields.Boolean("Is Stam Sale")
    is_stamp_purchase = fields.Boolean("Is Stam Purchase")

    @api.constrains('is_stamp_sale', 'is_stamp_purchase','company_id')
    def _check_unique_stamp_per_company(self):
        for record in self:
            if record.is_stamp_sale:
                domain = [
                    ('is_stamp_sale', '=', True),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_("A stamp sale tax already exists for this company!"))
            if record.is_stamp_purchase:
                domain = [
                    ('is_stamp_purchase', '=', True),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_("A stamp purchase tax already exists for this company!"))


    @api.model
    def create(self, vals):
        # The SQL constraints already handle the creation case for uniqueness.
        return super().create(vals)



    @api.onchange('is_stamp_sale')
    def _onchange_is_stamp_sale(self):
        if self.is_stamp_sale and self.type_tax_use != 'sale':
            self.type_tax_use = 'sale'

    @api.onchange('is_stamp_purchase')
    def _onchange_is_stamp_purchase(self):
        if self.is_stamp_purchase and self.type_tax_use != 'purchase':
            self.type_tax_use = 'purchase'
