# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductLifecycleRule(models.Model):
    _name = 'product.lifecycle.rule'
    _description = 'Product Lifecycle Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
        ondelete='cascade',
    )
    maintenance_type = fields.Selection(
        selection=[
            ('preventive', 'Preventive'),
            ('corrective', 'Corrective'),
        ],
        string='Maintenance Type',
        required=True,
    )
    odometer_type = fields.Selection(
        selection=[
            ('hour', 'Hour'),
            ('km', 'Kilometer'),
            ('day', 'Day'),
        ],
        string='Odometer Type',
    )
    spare_parts_ids = fields.Many2many(
        comodel_name='product.product',
        string='Spare Parts',
        domain=[('type', '=', 'consu'), ('is_storable', '=', True)],
    )
    odometer_value = fields.Float(string='Odometer Value')  # The value at which the rule triggers
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
