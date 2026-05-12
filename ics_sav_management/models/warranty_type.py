# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WarrantyType(models.Model):
    """ This model represents warranty.type."""
    _name = 'warranty.type'
    _description = 'WarrantyType'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Warranty Type', required=True)
    warranty_value = fields.Float(string='Warranty Value')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)


