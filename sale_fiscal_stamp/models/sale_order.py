from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    display_stamp = fields.Boolean(
        string="Ajouter Timbre Fiscal",
        default=True,
    )

    fiscal_stamp_amount = fields.Monetary(
        string="Timbre Fiscal",
        compute='_compute_fiscal_stamp',
        store=True
    )

    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id_stamp(self):
        if self.fiscal_position_id and self.fiscal_position_id.stamp_sale:
            self.display_stamp = True
        else:
            self.display_stamp = False

    @api.depends('fiscal_position_id', 'display_stamp')
    def _compute_fiscal_stamp(self):
        for order in self:
            if order.display_stamp and order.fiscal_position_id and order.fiscal_position_id.stamp_sale:
                order.fiscal_stamp_amount = order.fiscal_position_id.stamp_sale.amount
            else:
                order.fiscal_stamp_amount = 0.0

    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'payment_term_id', 'fiscal_stamp_amount')
    def _compute_tax_totals(self):
        # 1. Exécuter le code natif
        super(SaleOrder, self)._compute_tax_totals()

        # 2. Intercepter et modifier le dictionnaire JSON des totaux
        for order in self:
            if order.fiscal_stamp_amount > 0 and order.tax_totals:
                totals = dict(order.tax_totals)
                stamp_amount = order.fiscal_stamp_amount

                # Update main totals (Odoo 17+ naming: tax_amount_currency, total_amount_currency)
                totals['tax_amount_currency'] = totals.get('tax_amount_currency', 0.0) + stamp_amount
                totals['total_amount_currency'] = totals.get('total_amount_currency', 0.0) + stamp_amount
                
                if 'tax_amount' in totals:
                    totals['tax_amount'] += stamp_amount
                if 'total_amount' in totals:
                    totals['total_amount'] += stamp_amount

                stamp_group = {
                    'id': 999999,
                    'group_name': 'Timbre Fiscal',
                    'tax_amount_currency': stamp_amount,
                    'tax_amount': stamp_amount,
                    'base_amount_currency': 0.0,
                    'base_amount': 0.0,
                    'display_base_amount_currency': False,
                    'display_base_amount': False,
                }

                if totals.get('subtotals'):
                    # On ajoute le timbre au premier sous-total
                    subtotal = totals['subtotals'][0]
                    if 'tax_groups' not in subtotal:
                        subtotal['tax_groups'] = []
                    
                    subtotal['tax_groups'].append(stamp_group)
                    subtotal['tax_amount_currency'] = subtotal.get('tax_amount_currency', 0.0) + stamp_amount
                    if 'tax_amount' in subtotal:
                        subtotal['tax_amount'] += stamp_amount

                order.tax_totals = totals
