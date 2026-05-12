from odoo import api, fields, models, _

class CustomerClamReportWizard(models.TransientModel):
    _name = 'customer.clam.report.wizard'
    _description = 'Analyse de Réclamation Wizard'

    date_start = fields.Date(string='Date de début', required=True, default=fields.Date.context_today)
    date_end = fields.Date(string='Date de fin', required=True, default=fields.Date.context_today)

    def action_generate_xlsx(self):
        return self.env.ref('ics_qms.action_report_customer_clam_xlsx').report_action(self)
