from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    debranding_brand_name = fields.Char(
        string='Brand Name',
        config_parameter='ics_debranding.brand_name',
        default='ICS'
    )
