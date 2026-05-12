from odoo import models, fields, api, _

class IsoIndicator(models.Model):
    _name = 'iso.indicator'
    _description = 'ISO Quality Indicator (KPI)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Indicator Name', required=True, tracking=True)
    process_id = fields.Many2one('iso.process', string='Process', required=True)
    
    target_value = fields.Float(string='Target Value', default=0.0)
    target_operator = fields.Selection([
        ('gt', 'Greater than (>)'),
        ('lt', 'Less than (<)'),
        ('ge', 'Greater than or equal (>=)'),
        ('le', 'Less than or equal (<=)'),
        ('eq', 'Equal (=)')
    ], string='Target Operator', required=True, default='ge')
    unit = fields.Char(string='Unit (e.g. %, Days, Count)')
    
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semestrial', 'Semestrial'),
        ('annual', 'Annual')
    ], string='Measurement Frequency', required=True, default='monthly')
    
    calculation_method = fields.Text(string='Calculation Method (Formula)')
    
    measurement_ids = fields.One2many('iso.indicator.measurement', 'indicator_id', string='Measurements')
    
    active = fields.Boolean(default=True)

class IsoIndicatorMeasurement(models.Model):
    _name = 'iso.indicator.measurement'
    _description = 'ISO Indicator Measurement Value'

    indicator_id = fields.Many2one('iso.indicator', string='Indicator', ondelete='cascade')
    date = fields.Date(string='Measurement Date', default=fields.Date.context_today)
    value = fields.Float(string='Measured Value', required=True)
    
    target_value = fields.Float(related='indicator_id.target_value', string='Target Used')
    
    comment = fields.Text(string='Comment / Observations')
    achieved = fields.Boolean(compute='_compute_achieved', string='Target Achieved', store=True)

    @api.depends('value', 'indicator_id.target_value', 'indicator_id.target_operator')
    def _compute_achieved(self):
        for rec in self:
            op = rec.indicator_id.target_operator
            target = rec.indicator_id.target_value
            val = rec.value
            if op == 'gt':
                rec.achieved = val > target
            elif op == 'lt':
                rec.achieved = val < target
            elif op == 'ge':
                rec.achieved = val >= target
            elif op == 'le':
                rec.achieved = val <= target
            elif op == 'eq':
                rec.achieved = val == target
            else:
                rec.achieved = False
