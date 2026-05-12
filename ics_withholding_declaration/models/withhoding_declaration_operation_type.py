from odoo import fields, models, api


class WithhodingDeclarationOperationType(models.Model):
    _name = 'withholding.declaration.operation.type'
    _description = 'Withholding Declaration Operation Type'
    _rec_name = 'complete_name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code TEJ', store=True)
    rate = fields.Float('Rate (%)', digits=(16, 2), default=0.0, store=True)
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True)
    description = fields.Text(string='Description', store=True)
    category_id = fields.Many2one('withholding.declaration.operation.type.category', string='Category')
    active = fields.Boolean('Active', default=True)

    @api.depends('name', 'description', 'rate', 'category_id.name')
    def _compute_complete_name(self):
        for rs in self:
            if rs.category_id and rs.description and rs.rate and rs.name:
                rs.complete_name = '%s - RS %s%s - %s - %s' % (rs.category_id.name, rs.rate, "%", rs.name, rs.description)
            else:
                rs.complete_name = rs.name

