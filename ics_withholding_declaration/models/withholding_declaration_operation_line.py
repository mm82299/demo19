from odoo import fields, models, api


class TaxAdditionalCode(models.Model):
    _name = 'tax.additional.code'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Tax Additional Code'

    name = fields.Char('Code')
    rate = fields.Integer('Rate')

class WithholdingDeclarationOperationLine(models.Model):
    _name = 'withholding.declaration.operation.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Withholding Declaration Operation Line'

    name = fields.Char(string='Name')
    declaration_line_id = fields.Many2one('withholding.declaration.line', string='Withholding Declaration Line', ondelete='cascade')
    invoice_date = fields.Date(string='Invoice Date')
    cnpc = fields.Boolean(string='CNPC')
    p_charge = fields.Boolean(string='P Charge')
    amount_ht = fields.Float(string='Amount HT', digits="Product Price")
    rs_rate = fields.Float(string='RS Rate', digits="Product Price")
    tva_rate = fields.Float(string='TVA Rate', digits="Product Price")
    tva_amount = fields.Float(string='TVA Amount', digits="Product Price")
    amount_ttc = fields.Float(string='Amount TTC', digits="Product Price")
    amount_rs = fields.Float(string='Amount RS', digits="Product Price")
    taxe_additionnelle_code = fields.Many2one('tax.additional.code', string='Taxe Additionnelle')
    taxe_additionnelle_rate = fields.Integer(string='Taxe Additionnelle Rate', related='taxe_additionnelle_code.rate')
    amount_net_servi = fields.Float(string='Amount Net Servi', digits="Product Price")
    devise_code = fields.Many2one('withholding.declaration.country', string='Devise Code')
    devise_rate = fields.Float(string='Devise Rate', digits="Product Price")
    devise_rs = fields.Float(string='Devise RS', digits="Product Price")
    devise_ttc = fields.Float(string='Devise TTC', digits="Product Price")
    devise_servi = fields.Float(string='Devise Servi', digits="Product Price")
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company , readonly=True)
    operation_type_category = fields.Many2one('withholding.declaration.operation.type.category', string="Operation Type Category", related="declaration_line_id.operation_type_category")
    operation_type = fields.Many2one('withholding.declaration.operation.type', string="Operation Type", related="declaration_line_id.operation_type")






