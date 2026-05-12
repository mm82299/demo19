# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class SavRecord(models.Model):
    """SAV (After-Sales Service) record — created automatically on delivery validation."""
    _name = 'sav.record'
    _description = 'SAV Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Serial Number',
        required=True,
        tracking=True,
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        readonly=True,
        tracking=True,
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Delivery Order',
        readonly=True,
        tracking=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        readonly=True,
        tracking=True,
    )
    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Lot/Serial Number',
        readonly=True,
        tracking=True,
    )
    warranty_type = fields.Many2one('warranty.type', string='Warranty Type', related='product_id.product_tmpl_id.warranty_type', store=True, readonly=True)
    warranty_limit = fields.Float(
        related='product_id.product_tmpl_id.warranty_limit',
        string='Warranty Limit',
        store=True,
    )
    warranty_validity = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('expired', 'Expired'),
        ],
        string='Warranty Status',
        compute='_compute_warranty_validity',
        store=True,
        tracking=True,
    )
    odometer_current = fields.Float(
        string='Current Odometer',
        help='Fill in if warranty type is Hours or Kilometers.',
        tracking=True,
    )
    warranty_deadline = fields.Date(
        string='Warranty Deadline',
        compute='_compute_warranty_deadline',
        store=True,
        readonly=False,
        tracking=True,
        help='Computed automatically when warranty type is Days or Years.',
    )
    delivery_date = fields.Date(
        string='Delivery Date',
        readonly=True,
        help='Date on which the delivery order was validated.',
    )
    notes = fields.Html(string='Notes')
    sav_lifecycle_ids = fields.One2many(
        comodel_name='sav.lifecycle.rule',
        inverse_name='sav_id',
        string='SAV Lifecycle Rules',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
    )

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------

    @api.depends('delivery_date', 'warranty_type', 'warranty_limit')
    def _compute_warranty_deadline(self):
        for rec in self:
            if rec.delivery_date and rec.warranty_type in ('year', 'day') and rec.warranty_limit:
                if rec.warranty_type == 'year':
                    rec.warranty_deadline = rec.delivery_date + relativedelta(
                        years=int(rec.warranty_limit)
                    )
                elif rec.warranty_type == 'day':
                    rec.warranty_deadline = rec.delivery_date + relativedelta(
                        days=int(rec.warranty_limit)
                    )
            else:
                if not rec.warranty_deadline:
                    rec.warranty_deadline = False

    @api.depends('warranty_deadline', 'warranty_type', 'warranty_limit', 'odometer_current')
    def _compute_warranty_validity(self):
        today = fields.Date.today()
        for rec in self:
            if rec.warranty_type in ('year', 'day'):
                if rec.warranty_deadline:
                    rec.warranty_validity = (
                        'valid' if rec.warranty_deadline >= today else 'expired'
                    )
                else:
                    rec.warranty_validity = False
            elif rec.warranty_type in ('hour', 'km'):
                if rec.warranty_limit:
                    rec.warranty_validity = (
                        'valid' if rec.odometer_current <= rec.warranty_limit else 'expired'
                    )
                else:
                    rec.warranty_validity = False
            else:
                rec.warranty_validity = False
