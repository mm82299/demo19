# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    tax_stamp = fields.Boolean(readonly=False, compute="_compute_tax_stamp", store=True)
    auto_compute_stamp = fields.Boolean(default=True)
    manually_apply_tax_stamp = fields.Boolean("Apply tax stamp")
    amount_stamp_tax = fields.Float(readonly=False, compute="compute_amount_stamp_tax")

    def is_tax_stamp_applicable(self):
        for inv in self:
            if inv.move_type in ('out_invoice', 'in_invoice') and inv.fiscal_position_id and inv.fiscal_position_id.stamp_sale and inv.fiscal_position_id.stamp_purchase:
                return True
            else:
                return False

    @api.depends(
        "invoice_line_ids.price_subtotal",
        "line_ids.price_total",
        "currency_id",
        "company_id",
        "invoice_date",
        "move_type",
        "manually_apply_tax_stamp",
        "invoice_line_ids.tax_ids",
    )
    def _compute_tax_stamp(self):
        for inv in self:
            inv.tax_stamp = False
            if inv.move_type == 'out_invoice' and inv.fiscal_position_id and inv.fiscal_position_id.stamp_sale:
                inv.tax_stamp = True
            elif inv.move_type == 'in_invoice' and inv.fiscal_position_id and inv.fiscal_position_id.stamp_purchase:
                inv.tax_stamp = True
                if inv.manually_apply_tax_stamp:
                    inv.tax_stamp = True

    @api.depends(
        "invoice_line_ids.price_subtotal",
        "line_ids.price_total",
        "currency_id",
        "company_id",
        "invoice_date",
        "move_type",
        "manually_apply_tax_stamp",
        "invoice_line_ids.tax_ids",
    )
    def compute_amount_stamp_tax(self):
        for inv in self:
            amount_stamp_tax = 0.0
            if inv.fiscal_position_id and (inv.fiscal_position_id.stamp_sale or inv.fiscal_position_id.stamp_purchase):
                if inv.move_type == 'out_invoice':
                    inv.amount_stamp_tax = inv.fiscal_position_id.stamp_sale.amount
                elif inv.move_type == 'in_invoice':
                    inv.amount_stamp_tax = inv.fiscal_position_id.stamp_purchase.amount
                else:
                    inv.amount_stamp_tax = amount_stamp_tax
            else:
                inv.amount_stamp_tax = amount_stamp_tax

    def action_post(self):
        for inv in self:
            if inv.move_type in ('in_invoice', 'out_invoice'):
                inv.auto_applicability_tax_stamp()
        res = super(AccountMove, self).action_post()
        return res

    @api.depends('fiscal_position_id')
    def auto_applicability_tax_stamp(self):
        for inv in self:
            if inv.fiscal_position_id and (inv.fiscal_position_id.stamp_sale or inv.fiscal_position_id.stamp_purchase) and len(inv.invoice_line_ids) != 0:
                print("Stamp tax", inv.tax_stamp)
                if inv.tax_stamp:
                    inv.add_tax_stamp_line()

    def add_tax_stamp_line(self):
        for inv in self:
            if inv.move_type == 'out_invoice' :
                tax_repartition_lines = inv.fiscal_position_id.stamp_sale.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax') if inv.fiscal_position_id.stamp_sale else None
                print('refund_tax_repartition_lines', tax_repartition_lines)
                stamp_account_sale = tax_repartition_lines.account_id.id if tax_repartition_lines else None
                if not stamp_account_sale:
                    raise UserError(
                        _("Missing account income configuration for %s") % inv.fiscal_position_id.stamp_sale.name
                    )
                print('Stampc', inv.fiscal_position_id.stamp_sale.ids)
                print('Stampc', inv.fiscal_position_id.stamp_sale.ids)
                line_vals = {
                    "move_id": inv.id,
                    "name": inv.fiscal_position_id.stamp_sale.name,
                    "account_id": stamp_account_sale,
                    "credit": inv.fiscal_position_id.stamp_sale.amount,
                    "debit": 0.0,
                    "tax_ids": [(6, 0, inv.fiscal_position_id.stamp_sale.ids)],
                    "tax_line_id": inv.fiscal_position_id.stamp_sale.id,
                    "display_type": 'tax',
                    "is_stamp_line": True,
                }
                inv.with_context(skip_readonly_check=True).write({"line_ids": [(0, 0, line_vals)]})
                inv.line_ids.filtered(lambda line: line.is_stamp_line).sudo().write({
                    'tax_line_id': inv.fiscal_position_id.stamp_sale.id,
                })
            if inv.move_type == 'in_invoice':
                refund_tax_repartition_lines = inv.fiscal_position_id.stamp_purchase.invoice_repartition_line_ids.filtered(
                    lambda x: x.repartition_type == 'tax') if inv.fiscal_position_id.stamp_purchase else None
                print('refund_tax_repartition_lines', refund_tax_repartition_lines)
                stamp_account_purchase = refund_tax_repartition_lines.account_id.id if refund_tax_repartition_lines else None
                if not stamp_account_purchase:
                    raise UserError(
                        _("Missing account income configuration for %s") % inv.fiscal_position_id.stamp_purchase.name
                    )
                line_vals = {
                    "move_id": inv.id,
                    "name": inv.fiscal_position_id.stamp_purchase.name,
                    "account_id": stamp_account_purchase,
                    "debit": inv.fiscal_position_id.stamp_purchase.amount,
                    "credit": 0.0,
                    "tax_ids": [(6, 0, inv.fiscal_position_id.stamp_purchase.ids)],
                    "tax_line_id": inv.fiscal_position_id.stamp_purchase.id,
                    "display_type": 'tax',
                    "is_stamp_line": True
                }
                inv.with_context(skip_readonly_check=True).write({"line_ids": [(0, 0, line_vals)]})
                inv.line_ids.filtered(lambda line: line.is_stamp_line).sudo().write({
                    'tax_line_id': inv.fiscal_position_id.stamp_purchase.id,
                })
    def is_tax_stamp_line_present(self):
        for line in self.line_ids:
            if line.is_stamp_line:
                return True
        return False

    def is_tax_stamp_product_present(self):
        product_stamp = self.invoice_line_ids.filtered(
            lambda line: line.product_id.is_stamp
        )
        if product_stamp:
            return True
        return False

    def _build_tax_stamp_lines(self, product):
        if (
                not product.property_account_income_id
                or not product.property_account_expense_id
        ):
            raise UserError(
                _("Product %s must have income and expense accounts") % product.name
            )
        income_vals = {
            "name": _("Tax Stamp Income"),
            "is_stamp_line": True,
            "partner_id": self.partner_id.id,
            "account_id": product.property_account_income_id.id,
            "journal_id": self.journal_id.id,
            "date": self.invoice_date,
            "debit": 0,
            "credit": product.list_price,
            "display_type": "cogs",
            "currency_id": self.currency_id.id,
        }
        if self.move_type == "out_refund":
            income_vals["debit"] = product.list_price
            income_vals["credit"] = 0

        expense_vals = {
            # "name": _("Tax Stamp Expense"),
            "is_stamp_line": True,
            "partner_id": self.partner_id.id,
            "account_id": self.partner_id.property_account_receivable_id.id,
            "journal_id": self.journal_id.id,
            "date": self.invoice_date,
            "debit": product.list_price,
            "credit": 0,
            "display_type": "cogs",
            "currency_id": self.currency_id.id,
        }
        if self.move_type == "out_refund":
            income_vals["debit"] = 0
            income_vals["credit"] = product.list_price

        return income_vals, expense_vals

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        return res

    def _build_tax_stamp_lines(self, product):
        if (
                not product.property_account_income_id
                or not product.property_account_expense_id
        ):
            raise UserError(
                _("Product %s must have income and expense accounts") % product.name
            )
        income_vals = {
            "name": _("Tax Stamp Income"),
            "is_stamp_line": True,
            "partner_id": self.partner_id.id,
            "account_id": product.property_account_income_id.id,
            "journal_id": self.journal_id.id,
            "date": self.invoice_date,
            "debit": 0,
            "credit": product.list_price,
            "display_type": "cogs",
            "currency_id": self.currency_id.id,
        }
        if self.move_type == "out_refund":
            income_vals["debit"] = product.list_price
            income_vals["credit"] = 0

        expense_vals = {
            # "name": _("Tax Stamp Expense"),
            "is_stamp_line": True,
            "partner_id": self.partner_id.id,
            "account_id": self.partner_id.property_account_receivable_id.id,
            "journal_id": self.journal_id.id,
            "date": self.invoice_date,
            "debit": product.list_price,
            "credit": 0,
            "display_type": "cogs",
            "currency_id": self.currency_id.id,
        }
        if self.move_type == "out_refund":
            income_vals["debit"] = 0
            income_vals["credit"] = product.list_price

        return income_vals, expense_vals

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for account_move in self:
            move_line_tax_stamp_ids = account_move.line_ids.filtered(
                lambda line: line.is_stamp_line
            )
            move_line_tax_stamp_ids.unlink()
        return res

    @api.depends('amount_total')
    def get_amount_letter(self):
        amount = self.currency_id.amount_to_text(self.amount_total)
        return amount


    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
                tax_totals = self.env['account.tax']._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=move.currency_id,
                    company=move.company_id,
                    cash_rounding=move.invoice_cash_rounding_id,
                )
                tax_sale = self.env['account.tax'].sudo().search([('is_stamp_sale', '=', True)], limit=1)
                tax_purchase = self.env['account.tax'].sudo().search([('is_stamp_purchase', '=', True)], limit=1)
                if move.move_type == 'out_invoice' and tax_sale:
                    for subtotal in tax_totals.get('subtotals', []):
                        for tax_group in subtotal.get('tax_groups', []):
                            if tax_sale.id in tax_group.get('involved_tax_ids', []):
                                tax_group['tax_amount'] = tax_sale.amount
                                tax_group['tax_amount_currency'] = tax_sale.amount  # Update both if needed
                                tax_totals['tax_amount_currency'] += tax_group['tax_amount_currency']
                                tax_totals['tax_amount'] += tax_group['tax_amount']
                                tax_totals['total_amount_currency'] += tax_group['tax_amount']
                                tax_totals['total_amount'] += tax_group['tax_amount']

                if move.move_type == 'in_invoice' and tax_purchase:
                    for subtotal in tax_totals.get('subtotals', []):
                        for tax_group in subtotal.get('tax_groups', []):
                            if tax_purchase.id in tax_group.get('involved_tax_ids', []):
                                tax_group['tax_amount'] = tax_purchase.amount
                                tax_group['tax_amount_currency'] = tax_purchase.amount  # Update both if needed
                                tax_totals['tax_amount_currency'] += tax_group['tax_amount_currency']
                                tax_totals['tax_amount'] += tax_group['tax_amount']
                                tax_totals['total_amount_currency'] += tax_group['tax_amount']
                                tax_totals['total_amount'] += tax_group['tax_amount']


                move.tax_totals = tax_totals
                move.tax_totals['display_in_company_currency'] = (
                    move.company_id.display_invoice_tax_company_currency
                    and move.company_currency_id != move.currency_id
                    and move.tax_totals['has_tax_groups']
                    and move.is_sale_document(include_receipts=True)
                )
            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals = None

    def _get_rounded_base_and_tax_lines(self, round_from_tax_lines=True):
        """ Small helper to extract the base and tax lines for the taxes computation from the current move.
        The move could be stored or not and could have some features generating extra journal items acting as
        base lines for the taxes computation (e.g. epd, rounding lines).

        :param round_from_tax_lines:    Indicate if the manual tax amounts of tax journal items should be kept or not.
                                        It only works when the move is stored.
        :return:                        A tuple <base_lines, tax_lines> for the taxes computation.
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        is_invoice = self.is_invoice(include_receipts=True)

        if self.id or not is_invoice:
            base_amls = self.line_ids.filtered(lambda line: line.display_type == 'product')
        else:
            base_amls = self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')

        base_lines = [self._prepare_product_base_line_for_taxes_computation(line) for line in base_amls]


    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
                tax_totals = self.env['account.tax']._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=move.currency_id,
                    company=move.company_id,
                    cash_rounding=move.invoice_cash_rounding_id,
                )
                tax_sale = self.env['account.tax'].sudo().search([('is_stamp_sale', '=', True)], limit=1)
                tax_purchase = self.env['account.tax'].sudo().search([('is_stamp_purchase', '=', True)], limit=1)
                if move.move_type == 'out_invoice' and tax_sale:
                    for subtotal in tax_totals.get('subtotals', []):
                        for tax_group in subtotal.get('tax_groups', []):
                            if tax_sale.id in tax_group.get('involved_tax_ids', []):
                                tax_group['tax_amount'] = tax_sale.amount
                                tax_group['tax_amount_currency'] = tax_sale.amount  # Update both if needed
                                tax_totals['tax_amount_currency'] += tax_group['tax_amount_currency']
                                tax_totals['tax_amount'] += tax_group['tax_amount']
                                tax_totals['total_amount_currency'] += tax_group['tax_amount']
                                tax_totals['total_amount'] += tax_group['tax_amount']

                if move.move_type == 'in_invoice' and tax_purchase:
                    for subtotal in tax_totals.get('subtotals', []):
                        for tax_group in subtotal.get('tax_groups', []):
                            if tax_purchase.id in tax_group.get('involved_tax_ids', []):
                                tax_group['tax_amount'] = tax_purchase.amount
                                tax_group['tax_amount_currency'] = tax_purchase.amount  # Update both if needed
                                tax_totals['tax_amount_currency'] += tax_group['tax_amount_currency']
                                tax_totals['tax_amount'] += tax_group['tax_amount']
                                tax_totals['total_amount_currency'] += tax_group['tax_amount']
                                tax_totals['total_amount'] += tax_group['tax_amount']


                move.tax_totals = tax_totals
                move.tax_totals['display_in_company_currency'] = (
                    move.company_id.display_invoice_tax_company_currency
                    and move.company_currency_id != move.currency_id
                    and move.tax_totals['has_tax_groups']
                    and move.is_sale_document(include_receipts=True)
                )
            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals = None

    def _get_rounded_base_and_tax_lines(self, round_from_tax_lines=True):
        """ Small helper to extract the base and tax lines for the taxes computation from the current move.
        The move could be stored or not and could have some features generating extra journal items acting as
        base lines for the taxes computation (e.g. epd, rounding lines).

        :param round_from_tax_lines:    Indicate if the manual tax amounts of tax journal items should be kept or not.
                                        It only works when the move is stored.
        :return:                        A tuple <base_lines, tax_lines> for the taxes computation.
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        is_invoice = self.is_invoice(include_receipts=True)

        if self.id or not is_invoice:
            base_amls = self.line_ids.filtered(lambda line: line.display_type == 'product')
        else:
            base_amls = self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')

        base_lines = [self._prepare_product_base_line_for_taxes_computation(line) for line in base_amls]

        tax_lines = []
        if self.id:
            # The move is stored so we can add the early payment discount lines directly to reduce the
            # tax amount without touching the untaxed amount.
            stamp_tax_amls = self.line_ids \
                .filtered(lambda line: line.display_type == 'tax' and line.account_id.is_stamp_account)
            base_lines += [self._prepare_product_base_line_for_taxes_computation(line) for line in stamp_tax_amls]
            epd_amls = self.line_ids.filtered(lambda line: line.display_type == 'epd')
            base_lines += [self._prepare_epd_base_line_for_taxes_computation(line) for line in epd_amls]
            cash_rounding_amls = self.line_ids \
                .filtered(lambda line: line.display_type == 'rounding' and not line.tax_repartition_line_id)
            base_lines += [self._prepare_cash_rounding_base_line_for_taxes_computation(line) for line in
                           cash_rounding_amls]
            non_deductible_base_lines = self.line_ids.filtered(lambda line: line.display_type in ('non_deductible_product', 'non_deductible_product_total'))
            base_lines += [self._prepare_non_deductible_base_line_for_taxes_computation(line) for line in non_deductible_base_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            tax_amls = self.line_ids.filtered('tax_repartition_line_id')
            tax_lines = [self._prepare_tax_line_for_taxes_computation(tax_line) for tax_line in tax_amls]
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id,
                                                     tax_lines=tax_lines if round_from_tax_lines else [])
        else:
            # The move is not stored yet so the only thing we have is the invoice lines.
            base_lines += self._prepare_epd_base_lines_for_taxes_computation_from_base_lines(base_amls)
            base_lines += self._prepare_non_deductible_base_lines_for_taxes_computation_from_base_lines(base_amls)
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        return base_lines, tax_lines
        tax_lines = []
        if self.id:
            # The move is stored so we can add the early payment discount lines directly to reduce the
            # tax amount without touching the untaxed amount.
            stamp_tax_amls = self.line_ids \
                .filtered(lambda line: line.display_type == 'tax' and line.account_id.is_stamp_account)
            base_lines += [self._prepare_product_base_line_for_taxes_computation(line) for line in stamp_tax_amls]
            epd_amls = self.line_ids.filtered(lambda line: line.display_type == 'epd')
            base_lines += [self._prepare_epd_base_line_for_taxes_computation(line) for line in epd_amls]
            cash_rounding_amls = self.line_ids \
                .filtered(lambda line: line.display_type == 'rounding' and not line.tax_repartition_line_id)
            base_lines += [self._prepare_cash_rounding_base_line_for_taxes_computation(line) for line in
                           cash_rounding_amls]
            non_deductible_base_lines = self.line_ids.filtered(lambda line: line.display_type in ('non_deductible_product', 'non_deductible_product_total'))
            base_lines += [self._prepare_non_deductible_base_line_for_taxes_computation(line) for line in non_deductible_base_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            tax_amls = self.line_ids.filtered('tax_repartition_line_id')
            tax_lines = [self._prepare_tax_line_for_taxes_computation(tax_line) for tax_line in tax_amls]
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id,
                                                     tax_lines=tax_lines if round_from_tax_lines else [])
        else:
            # The move is not stored yet so the only thing we have is the invoice lines.
            base_lines += self._prepare_epd_base_lines_for_taxes_computation_from_base_lines(base_amls)
            base_lines += self._prepare_non_deductible_base_lines_for_taxes_computation_from_base_lines(base_amls)
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        return base_lines, tax_lines

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    is_stamp_line = fields.Boolean(
        readonly=True
    )  # used only with automatic tax stamp active

    @api.ondelete(at_uninstall=False)
    def _prevent_automatic_line_deletion(self):
        if not self.env.context.get('dynamic_unlink'):
            for line in self:
                if line.display_type == 'tax' and line.move_id.line_ids.tax_ids and not line.is_stamp_line:
                    raise ValidationError(_(
                        "You cannot delete a tax line as it would impact the tax report"
                    ))
                elif line.display_type == 'payment_term':
                    raise ValidationError(_(
                        "You cannot delete a payable/receivable line as it would not be consistent "
                        "with the payment terms"
                    ))
