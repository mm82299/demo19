from odoo import api, fields, models


class LocationFloorType(models.Model):
    _name = 'location.floor.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Floor Type'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
