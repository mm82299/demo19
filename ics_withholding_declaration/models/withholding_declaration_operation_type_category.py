from odoo import fields, models, api


class WithholdingDeclarationOperationTypeCategory(models.Model):
    _name = 'withholding.declaration.operation.type.category'
    _description = 'Withholding Declaration Operation Type Category'

    name = fields.Char('Category')
    code = fields.Char('Code')
