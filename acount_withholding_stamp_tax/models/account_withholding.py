from odoo import fields, models, api


class AccountWithholding(models.Model):
    _inherit = 'account.withholding'
    _description = 'Withholding tax'

    stamp_tax = fields.Selection([('with_stamp', 'With Stamp tax'), ('without_stamp', 'Without Stamp tax')], string="Stamp tax", default="without_stamp")

    @api.depends('stamp_tax', 'account_invoice_ids')
    def _compute_amount_total_rs(self):
        for record in self :
            if record.withholding_advance:
                lst_price = 0.0
                lst_price_rs = 0.0
                if record.account_withholding_tax_ids:
                    invoice_sum = 0.0
                    for invoice in record.account_invoice_ids:
                        print('invoice.amount_stamp_tax', invoice.amount_stamp_tax)
                        if invoice.move_type == 'out_refund':
                            invoice_sum += (invoice.amount_total_signed + invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                        if invoice.move_type == 'out_invoice':
                            invoice_sum += (invoice.amount_total_signed - invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                        if invoice.move_type == 'in_refund':
                            invoice_sum += (invoice.amount_total_signed - invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                        if invoice.move_type == 'in_invoice':
                            invoice_sum += (invoice.amount_total_signed + invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                    lst_price += invoice_sum
                    lst_price_rs = lst_price + record.amount_advance
                record.amount_total_rs = round(lst_price_rs, 3)
            else:
                lst_price = 0.0
                if record.account_withholding_tax_ids:
                    invoice_sum = 0.0

                    for invoice in record.account_invoice_ids:
                        print('Timbre', invoice.tax_stamp)
                        print('invoice.amount_stamp_tax', invoice.amount_stamp_tax)
                        if invoice.move_type == 'out_refund':
                            invoice_sum += (invoice.amount_total_signed + invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                        if invoice.move_type == 'out_invoice':
                            invoice_sum += (invoice.amount_total_signed - invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                        if invoice.move_type == 'in_refund':
                            invoice_sum += (invoice.amount_total_signed - invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                        if invoice.move_type == 'in_invoice':
                            invoice_sum += (invoice.amount_total_signed + invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                    lst_price += invoice_sum
                record.amount_total_rs = round(lst_price, 3)


    @api.depends('amount_total_rs')
    def _compute_amount(self):
        for record in self:
            sum = 0.0
            record.retenue_amount = 0.0
            for tax in record.account_withholding_tax_ids:
                invoice_sum = 0.0
                for invoice in record.account_invoice_ids:
                    if invoice.move_type == 'out_refund':
                        invoice_sum += (invoice.amount_total_signed + invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                    if invoice.move_type == 'out_invoice':
                        invoice_sum += (invoice.amount_total_signed - invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                    if invoice.move_type == 'in_refund':
                        invoice_sum += (invoice.amount_total_signed - invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                    if invoice.move_type == 'in_invoice':
                        invoice_sum += (invoice.amount_total_signed + invoice.amount_stamp_tax)  if invoice.tax_stamp and record.stamp_tax == 'without_stamp' else invoice.amount_total_signed
                sum += invoice_sum * 0.01 * tax.rate
                if record.withholding_advance:
                    rs_sum = 0.0
                    rs_sum = sum + (record.amount_advance * 0.01 * tax.rate)
                    record.retenue_amount = round(rs_sum, 3)
                else:
                    record.retenue_amount = round(sum, 3)