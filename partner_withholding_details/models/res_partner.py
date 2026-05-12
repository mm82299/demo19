# -*- coding: utf-8 -*-

from odoo import _,api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    customer_account_withholding = fields.Many2one('account.withholding.tax', string="Customer Withholding tax", domain="[('type_withholding', '=', 'vente')]")
    vendor_account_withholding = fields.Many2one('account.withholding.tax', string="Vendor Withholding tax", domain="[('type_withholding', '=', 'achat')]")

