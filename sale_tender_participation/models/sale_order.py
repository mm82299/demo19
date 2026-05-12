from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tender_participation_id = fields.Many2one('sale.tender.participation', string="Appel d'offres / Consultation")
