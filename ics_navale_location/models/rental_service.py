# -*- coding: utf-8 -*-
from odoo import api, fields, models


class RentalService(models.Model):
    _name = 'rental.service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Rental Service'

    rental_id = fields.Many2one('location.rental', string='Rental', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='rental_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency', readonly=True)
    product_id = fields.Many2one('product.product', string='Service', domain="[('type', '=', 'service')]")
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Monetary(string='Unit Price', currency_field='currency_id')
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_price_subtotal', store=True, currency_field='currency_id')

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
