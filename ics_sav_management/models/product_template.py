# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    """Extends product.template with lifecycle tracking and warranty fields."""
    _inherit = 'product.template'

    track_lifecycle = fields.Boolean(
        string='Track Product Lifecycle',
        default=False,
    )
    warranty_type = fields.Many2one('warranty.type', string='Warranty Type')
    warranty_limit = fields.Float(string='Warranty Limit')
    lifecycle_ids = fields.One2many(
        comodel_name='product.lifecycle.rule',
        inverse_name='product_id',
        string='Lifecycle Rules',
    )
