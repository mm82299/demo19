from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    traite_due_date = fields.Date(string="Date d'échéance")
    traite_number = fields.Char(string="Numéro de traite")
    
    is_traite_payment = fields.Boolean(
        compute='_compute_is_traite_payment',
        string="Est une traite ?"
    )

    @api.depends('payment_method_line_id', 'payment_method_line_id.name')
    def _compute_is_traite_payment(self):
        for payment in self:
            payment.is_traite_payment = payment.payment_method_line_id.name == 'Traite'


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    traite_due_date = fields.Date(string="Date d'échéance")
    traite_number = fields.Char(string="Numéro de traite")
    
    is_traite_payment = fields.Boolean(
        compute='_compute_is_traite_payment_register',
        string="Est une traite ?"
    )

    @api.depends('payment_method_line_id', 'payment_method_line_id.name')
    def _compute_is_traite_payment_register(self):
        for wizard in self:
            wizard.is_traite_payment = wizard.payment_method_line_id.name == 'Traite'

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['traite_due_date'] = self.traite_due_date
        payment_vals['traite_number'] = self.traite_number
        return payment_vals
