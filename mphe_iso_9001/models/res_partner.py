from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_qualified_vendor = fields.Boolean(string='Qualified Vendor (ISO)')
    vendor_type = fields.Selection([
        ('critical', 'Critical / Major'),
        ('non_critical', 'Non-Critical / Secondary'),
        ('other', 'Other')
    ], string='Vendor criticality', default='non_critical')
    
    vendor_rating = fields.Selection([
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Poor / Need improvement'),
        ('D', 'D - Disqualified / Canceled')
    ], string='ISO Rating', tracking=True)
    
    last_evaluation_date = fields.Date(string='Last Evaluation Date')
    next_evaluation_date = fields.Date(string='Next Evaluation Date')
    
    evaluation_comment = fields.Text(string='Evaluation Observations')

    def action_evaluate_vendor(self):
        # Open a wizard for evaluation eventually or just navigate to this page
        pass
