from odoo import api, fields, models

class LocationZone(models.Model):
    _name = 'location.zone'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Shipyard Location'

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    image = fields.Image("Image", max_width=256, max_height=256)
    description = fields.Html(string='Description')
    max_length = fields.Float(string='Max Length (m)')
    max_width = fields.Float(string='Max Width (m)')
    floor_type = fields.Many2one('location.floor.type', string='Floor Type', required=True)
    has_electricity = fields.Boolean(string='Electricity Available')
    has_water = fields.Boolean(string='Water Available')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency', readonly=True)
    base_price = fields.Monetary(string='Base Price per Day', currency_field='currency_id')
    price_per_meter = fields.Monetary(string='Price per Meter (Boat Length)', currency_field='currency_id',
                                      help="Additional daily cost per meter of boat length")
    
    state = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
        ('maintenance', 'In Maintenance')
    ], string='Status', default='available', compute='_compute_state', store=True, readonly=False)

    rental_ids = fields.One2many('location.rental', 'location_id', string='Rentals')
    color = fields.Integer(string='Color', compute='_compute_color')

    @api.depends('rental_ids.state', 'rental_ids.start_date', 'rental_ids.end_date')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.state == 'maintenance':
                continue
            
            active_rentals = rec.rental_ids.filtered(
                lambda r: r.start_date and r.end_date and r.start_date <= today <= r.end_date and r.state in ['confirmed', 'in_progress']
            )
            if active_rentals:
                rec.state = 'occupied'
            else:
                future_rentals = rec.rental_ids.filtered(
                    lambda r: r.start_date and r.start_date > today and r.state == 'confirmed'
                )
                if future_rentals:
                    rec.state = 'reserved'
                else:
                    rec.state = 'available'

    @api.depends('state')
    def _compute_color(self):
        for rec in self:
            if rec.state == 'available':
                rec.color = 10  # Green
            elif rec.state == 'occupied':
                rec.color = 2   # Red / Orange
            elif rec.state == 'reserved':
                rec.color = 4   # Light Blue
            elif rec.state == 'maintenance':
                rec.color = 1   # Gray / Red
            else:
                rec.color = 0
