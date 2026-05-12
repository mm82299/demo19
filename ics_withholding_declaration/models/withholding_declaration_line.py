from odoo import fields, models, api


class WithholdingDeclarationLine(models.Model):
    _name = 'withholding.declaration.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Withholding Declaration Line'

    name = fields.Char(string='Name')
    partner_id = fields.Many2one('res.partner', string="Fournisseur")
    declaration_id = fields.Many2one('withholding.declaration', string='Withholding Declaration', ondelete='cascade') #*
    declaration_id_edit = fields.Many2one('withholding.declaration', string='Withholding Declaration') #*
    declaration_id_delete = fields.Many2one('withholding.declaration', string='Withholding Declaration') #*
    withholding_id = fields.Many2one('account.withholding', string='Withholding Declaration') #
    account_move_id = fields.Many2one('account.move', string='Account Move', related="withholding_id.account_move_id") #
    operation_line_ids = fields.One2many('withholding.declaration.operation.line', 'declaration_line_id', string='Operation Lines')
    tax_id_type = fields.Selection(string='Tax ID Type', related="partner_id.tax_id_type", readonly=False)
    tax_id = fields.Char(string='Tax ID')
    birth_date = fields.Date(string='Birth Date', related="partner_id.date_of_birth", readonly=False)
    category_type = fields.Selection(string='Category Type', related="partner_id.category_type", readonly=False)
    country_id = fields.Many2one('res.country', string='Country')
    partner_tunisian = fields.Boolean(string='Partner Tunisian')
    partner_full_name = fields.Char(string='Partner Full Name')
    partner_address = fields.Char(string='Partner Address')
    partner_activity = fields.Char(string='Partner Activity')
    partner_mail = fields.Char(string='Partner Mail', related="partner_id.email", readonly=False)
    partner_phone = fields.Char(string='Partner Phone', related="partner_id.phone", readonly=False)
    payment_date = fields.Date(string='Payment Date')
    ref_certificate = fields.Char(string='Ref of Certificate')#*
    total_amount_ht = fields.Float(string='Total Amount HT', digits="Product Price")#*
    total_amount_tva = fields.Float(string='Total Amount TVA', digits="Product Price")
    total_amount_ttc = fields.Float(string='Total Amount TTC', digits="Product Price")#*
    total_amount_rs = fields.Float(string='Total Amount RS', digits="Product Price" )
    total_taxes = fields.Float(string='Total Taxes', digits="Product Price")
    total_amount_amount_servi = fields.Float(string='Total Amount Servi', digits="Product Price")
    total_amount_devise = fields.Float(string='Total Amount Devise', digits="Product Price")
    total_amount_devise_rs = fields.Float(string='Total Amount Devise RS', digits="Product Price")
    total_amount_devise_ttc = fields.Float(string='Total Amount Devise TVA', digits="Product Price")
    total_amount_devise_servi = fields.Float(string='Total Amount Devise HT', digits="Product Price")
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company , readonly=True)
    operation_type_category = fields.Many2one('withholding.declaration.operation.type.category', string="Operation Type Category", related="partner_id.operation_type_category", readonly=False)
    operation_type = fields.Many2one('withholding.declaration.operation.type', string="Operation Type", domain="[('category_id', '=', operation_type_category)]", related="partner_id.operation_type", readonly=False)

