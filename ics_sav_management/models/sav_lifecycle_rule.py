# -*- coding: utf-8 -*-
from odoo import fields, models


class SavLifecycleRule(models.Model):

    _name = 'sav.lifecycle.rule'
    _description = 'SAV Lifecycle Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sav_id = fields.Many2one(
        comodel_name='sav.record',
        string='SAV Record',
        required=True,
        ondelete='cascade',
    )
    maintenance_type = fields.Selection(
        selection=[
            ('preventive', 'Preventive'),
            ('corrective', 'Corrective'),
        ],
        string='Maintenance Type',
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
        relation='sav_lifecycle_spare_parts_rel',
        column1='lifecycle_rule_id',
        column2='product_id',
        string='Spare Parts',
        domain=[('type', '=', 'product'), ('tracking', '!=', 'none')],
    )
    odometer_value = fields.Float(string='Target Odometer Value')
    odometer_real_value = fields.Float(string='Actual Odometer Value')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='draft',
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
