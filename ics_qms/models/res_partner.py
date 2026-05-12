from odoo import models, fields, api


class ResPartner(models.Model):

    _inherit = 'res.partner'


    supplier_evaluation_ids = fields.One2many('supplier.evaluation', 'partner_id', string='Supplier Evaluation')
