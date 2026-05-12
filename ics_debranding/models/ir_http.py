from odoo import models
from odoo.http import request

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super(IrHttp, self).session_info()
        
        # Get brand name from settings
        brand_name = self.env['ir.config_parameter'].sudo().get_param('ics_debranding.brand_name', 'ICS')
        
        # Remove version info or brand it as custom
        if 'server_version' in res:
            res['server_version'] = brand_name
        if 'server_version_info' in res:
            res['server_version_info'] = [19, 0, 0, 'final', 0, '']
        
        return res
