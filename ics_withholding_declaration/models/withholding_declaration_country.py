from odoo import fields, models, api


class WithholdingDeclarationCountry(models.Model):
    _name = 'withholding.declaration.country'
    _description = 'Withholding Declaration Country'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
