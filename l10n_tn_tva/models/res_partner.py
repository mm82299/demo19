from odoo import fields, models, api


class ResParter(models.Model):
    _inherit = 'res.partner'
    _description = 'Description'

    is_state = fields.Boolean("Établisement de l'état", default=False, store=True)
