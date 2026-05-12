from odoo import api, fields, models

class ResBoat(models.Model):
    _name = 'res.boat'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Boat'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    registration = fields.Char(string='Registration Number')
    length = fields.Float(string='Overall Length (m)')
    partner_id = fields.Many2one('res.partner', string='Owner', required=True)
    image = fields.Image("Image", max_width=256, max_height=256)
    description = fields.Html(string='Description')
    rental_ids = fields.One2many('location.rental', 'boat_id', string='Rentals')
    rental_count = fields.Integer(compute='_compute_rental_count')

    @api.depends('rental_ids')
    def _compute_rental_count(self):
        for rec in self:
            rec.rental_count = len(rec.rental_ids)
