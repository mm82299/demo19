from odoo import api, fields, models,_
from odoo.exceptions import ValidationError

class LocationRental(models.Model):
    _name = 'location.rental'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Shipyard Rental'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    boat_id = fields.Many2one('res.boat', string='Boat', required=True, domain="[('partner_id', '=', partner_id)]")
    location_id = fields.Many2one('location.zone', string='Location', required=True)
    
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    duration = fields.Integer(string='Duration (Days)', compute='_compute_duration', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', required=True)

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency', readonly=True)
    price_per_day = fields.Monetary(string='Price Per Day', required=True, currency_field='currency_id')
    amount_total = fields.Monetary(string='Rental Subtotal', compute='_compute_amount_total', store=True, currency_field='currency_id')
    services_total = fields.Monetary(string='Services Total', compute='_compute_services_total', store=True, currency_field='currency_id')
    total_amount = fields.Monetary(string='Total', compute='_compute_total_amount', store=True, required=True, currency_field='currency_id')
    
    service_line_ids = fields.One2many('rental.service', 'rental_id', string='Additional Services')

    invoice_ids = fields.Many2many('account.move', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
    ], string='Payment Status', compute='_compute_payment_state', store=True)
    deposit_required = fields.Boolean(string='Deposit Required', default=False)
    deposit_amount = fields.Monetary(string='Deposit Amount', currency_field='currency_id')
    deposit_invoice_id = fields.Many2one('account.move', string='Deposit Invoice', copy=False)
    deposit_paid = fields.Boolean(string='Deposit Paid', compute='_compute_deposit_paid')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('location.rental') or _('New')
        return super().create(vals_list)

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                delta = rec.end_date - rec.start_date
                rec.duration = max(1, delta.days + 1)
            else:
                rec.duration = 0

    @api.depends('duration', 'price_per_day')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.duration * rec.price_per_day

    @api.depends('service_line_ids.price_subtotal')
    def _compute_services_total(self):
        for rec in self:
            rec.services_total = sum(rec.service_line_ids.mapped('price_subtotal'))

    @api.depends('amount_total', 'services_total')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.amount_total + rec.services_total

    @api.onchange('boat_id', 'location_id')
    def _onchange_compute_price(self):
        for rec in self:
            price = 0.0
            if rec.location_id:
                price += rec.location_id.base_price
            if rec.boat_id and rec.location_id:
                price += rec.boat_id.length * rec.location_id.price_per_meter
            rec.price_per_day = price

    @api.constrains('start_date', 'end_date', 'location_id', 'state')
    def _check_overlap(self):
        for rec in self:
            if rec.state in ['cancel', 'draft']:
                continue
            if not rec.start_date or not rec.end_date or not rec.location_id:
                continue
            domain = [
                ('id', '!=', rec.id),
                ('location_id', '=', rec.location_id.id),
                ('state', 'in', ['confirmed', 'in_progress']),
                ('start_date', '<', rec.end_date),
                ('end_date', '>', rec.start_date),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(_("The location is already booked for these dates."))

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.depends('invoice_ids.payment_state')
    def _compute_payment_state(self):
        for rec in self:
            states = rec.invoice_ids.filtered(lambda i: i.move_type == 'out_invoice').mapped('payment_state')
            if not states:
                rec.payment_state = 'not_paid'
            elif all(s == 'paid' for s in states):
                rec.payment_state = 'paid'
            elif any(s == 'reversed' for s in states):
                rec.payment_state = 'reversed'
            elif any(s == 'in_payment' for s in states):
                rec.payment_state = 'in_payment'
            elif any(s == 'partial' for s in states):
                rec.payment_state = 'partial'
            else:
                rec.payment_state = 'not_paid'

    @api.depends('deposit_invoice_id.payment_state')
    def _compute_deposit_paid(self):
        for rec in self:
            rec.deposit_paid = rec.deposit_invoice_id.payment_state == 'paid' if rec.deposit_invoice_id else False

    def action_confirm(self):
        self.state = 'confirmed'

    def action_in_progress(self):
        self.state = 'in_progress'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def action_create_invoice(self):
        self.ensure_one()
        rental_product = self.env.ref('ics_navale_location.product_location_rental', raise_if_not_found=False)
        
        invoice_lines = []
        if rental_product:
            invoice_lines.append((0, 0, {
                'product_id': rental_product.id,
                'name': f"Rental of {self.location_id.name}",
                'quantity': self.duration,
                'price_unit': self.price_per_day,
            }))
            
        for service in self.service_line_ids:
            invoice_lines.append((0, 0, {
                'product_id': service.product_id.id,
                'name': service.product_id.name,
                'quantity': service.quantity,
                'price_unit': service.price_unit,
            }))
            
        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': invoice_lines,
        }
        
        move = self.env['account.move'].create(move_vals)
        self.invoice_ids = [(4, move.id)]
        
        return {
            'name': _('Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': move.id,
            'type': 'ir.actions.act_window',
        }

    def action_create_deposit_invoice(self):
        self.ensure_one()
        rental_product = self.env.ref('ics_navale_location.product_location_rental', raise_if_not_found=False)
        if not rental_product or not self.deposit_amount:
            return
        invoice_lines = [(0, 0, {
            'product_id': rental_product.id,
            'name': _("Deposit for %s - %s") % (self.name, self.location_id.name),
            'quantity': 1.0,
            'price_unit': self.deposit_amount,
        })]
        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': invoice_lines,
        }
        move = self.env['account.move'].create(move_vals)
        self.deposit_invoice_id = move.id
        self.invoice_ids = [(4, move.id)]
        return {
            'name': _('Deposit Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': move.id,
            'type': 'ir.actions.act_window',
        }

    def action_view_deposit_invoice(self):
        self.ensure_one()
        return {
            'name': _('Deposit Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.deposit_invoice_id.id,
            'type': 'ir.actions.act_window',
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'type': 'ir.actions.act_window',
        }

