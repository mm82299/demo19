# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    """ This model represents account.move."""
    _inherit = 'account.move'

    has_guarantee_withholding = fields.Boolean('Retenu De Garantie', compute='_compute_has_guarantee_withholding')
    guarantee_based_on = fields.Selection([('ttc', 'Base on TTC'), ('ht', 'Base on HT')], string='Retenue de garantie basée sur', default='ttc')

    @api.depends('invoice_line_ids.tax_ids', 'partner_id.is_state')
    def _compute_has_guarantee_withholding(self):
        for rec in self:
            rec.has_guarantee_withholding = rec.partner_id.is_state and any(
                tax.is_guarantee_withholding
                for line in rec.invoice_line_ids
                for tax in line.tax_ids
            )

    def extract_tax_groups(self,totals):
        positive_taxes = []
        negative_taxes = []

        for subtotal in totals.get('subtotals', []):
            for tax in subtotal.get('tax_groups', []):
                tax_data = {
                    'id': tax.get('id'),
                    'name': tax.get('group_name'),
                    'rate': (
                        tax.get('tax_amount') / tax.get('base_amount')
                        if tax.get('base_amount') else 0
                    ),
                    'base': tax.get('base_amount'),
                    'amount': tax.get('tax_amount'),
                }

                if tax_data['rate'] >= 0:
                    positive_taxes.append(tax_data)
                else:
                    negative_taxes.append(tax_data)

        return {
            'positive_taxes': positive_taxes,
            'negative_taxes': negative_taxes
        }

    @api.depends('has_guarantee_withholding', 'guarantee_based_on', 'invoice_line_ids.tax_ids', 'partner_id.is_state')
    def _compute_tax_totals(self):
        super(AccountMove, self)._compute_tax_totals()
        for move in self:
            if not (move.has_guarantee_withholding and move.partner_id.is_state and move.tax_totals):
                continue

            totals = dict(move.tax_totals)
            currency = move.currency_id

            # ── 1. Collect VAT and RG tax groups from Odoo's standard totals ────────
            vat_groups = []   # positive rates  (e.g. TVA 19%)
            rg_groups  = []   # negative rates  (Retenue de Garantie)

            for subtotal in totals.get('subtotals', []):
                for tg in subtotal.get('tax_groups', []):
                    if tg.get('tax_amount_currency', 0) >= 0:
                        vat_groups.append(tg)
                    else:
                        rg_groups.append(tg)

            # ── 2. Key raw amounts from Odoo (before any override) ───────────────
            # base_amount_currency  = untaxed (HT) amount as reported by Odoo
            original_ht  = totals.get('base_amount_currency', 0.0)          # 49 240
            original_vat = sum(g.get('tax_amount_currency', 0.0) for g in vat_groups)  # sum of positive taxes

            # ── 3. Recalculate VAT on the *full* HT (in case Odoo already reduced it)
            #       We use the rate stored in each VAT group.
            recalc_vat = 0.0
            for g in vat_groups:
                base = g.get('base_amount_currency', 0.0) or original_ht
                rate = g.get('tax_amount_currency', 0.0) / base if base else 0.0
                recalc_vat += original_ht * rate

            # If Odoo's own vat amount is close to the recalc, trust it; otherwise use recalc.
            # (When guarantee_based_on == 'ttc' the original HT is the correct full base.)
            if abs(recalc_vat - original_vat) > 0.01:
                display_vat = recalc_vat
            else:
                display_vat = original_vat

            # ── 4. TTC before guarantee deduction ───────────────────────────────
            ttc_before_rg = original_ht + display_vat                        # 49 240 + 9 355.6

            # ── 5. Guarantee (RG) amount ─────────────────────────────────────────
            rg_total = sum(g.get('tax_amount_currency', 0.0) for g in rg_groups)  # negative
            rg_abs   = abs(rg_total)                                          # 5 859.56

            # If guarantee_based_on == 'ttc', ensure RG = rate × TTC_before_RG
            if move.guarantee_based_on == 'ttc' and rg_groups:
                # derive the rate from the stored RG group(s) base amount vs its amount
                rg_rate_parts = []
                for g in rg_groups:
                    stored_base = g.get('base_amount_currency', 0.0)
                    stored_amt  = abs(g.get('tax_amount_currency', 0.0))
                    if stored_base:
                        rg_rate_parts.append(stored_amt / stored_base)
                if rg_rate_parts:
                    rg_rate = sum(rg_rate_parts) / len(rg_rate_parts)
                    rg_abs  = ttc_before_rg * rg_rate                        # 58 595.6 × 0.10

            # ── 6. Final TTC ──────────────────────────────────────────────────────
            total_ttc = ttc_before_rg - rg_abs                               # 52 736.04

            # ── 7. Pro-rate RG into HT and VAT portions ───────────────────────────
            if ttc_before_rg:
                rg_ht_portion  = rg_abs * (original_ht  / ttc_before_rg)    # 4 924
                rg_vat_portion = rg_abs * (display_vat  / ttc_before_rg)    # 935.56
            else:
                rg_ht_portion  = rg_abs
                rg_vat_portion = 0.0

            net_ht  = original_ht  - rg_ht_portion                           # 44 316
            net_vat = display_vat  - rg_vat_portion                          # 8 420.04

            # ── 8. Build custom_guarantee_info for the PDF report ────────────────
            def fmt(amount):
                return formatLang(self.env, amount, currency_obj=currency)

            rg_name = rg_groups[0].get('group_name', 'Retenue de Garantie') if rg_groups else 'Retenue de Garantie'
            vat_name = vat_groups[0].get('group_name', 'TVA') if vat_groups else 'TVA'
            

            totals['custom_guarantee_info'] = {
                # ── original bloc ──────────────────────────────────────────────
                'vat_name'                      : vat_name,
                'rg_name'                       : rg_name,

                'total_ht_original'             : original_ht,
                'formatted_total_ht_original'   : fmt(original_ht),

                'total_vat_original'            : display_vat,
                'formatted_total_vat_original'  : fmt(display_vat),

                'total_ttc_before_rg'           : ttc_before_rg,
                'formatted_total_ttc_before_rg' : fmt(ttc_before_rg),

                'rg_amount'                     : rg_abs,
                'formatted_rg_amount'           : fmt(rg_abs),

                # ── final TTC ──────────────────────────────────────────────────
                'total_ttc_after_rg'            : total_ttc,
                'formatted_total_ttc_after_rg'  : fmt(total_ttc),

                # ── net (after pro-rating) bloc ────────────────────────────────
                'net_ht'                        : net_ht,
                'formatted_net_ht'              : fmt(net_ht),

                'net_vat'                       : net_vat,
                'formatted_net_vat'             : fmt(net_vat),
            }
            print(totals)
            move.tax_totals = totals






                # # We will split existing groups into VAT and RG
                # vat_groups = []
                # rg_groups = []
                #
                # base_untaxed_currency = totals.get('amount_untaxed', 0.0)
                # other_taxes_sum_currency = 0.0
                #

                #
                # # Determine total TTC before RG
                # total_ttc_before_rg = base_untaxed_currency + other_taxes_sum_currency
                #
                # # Recalculate RG if in TTC mode
                # tax = rg_taxes[0]
                # rate = abs(tax.amount) / 100.0 if tax.amount_type == 'percent' else 0.0
                #
                # rg_amount_currency = 0.0
                # if move.guarantee_based_on == 'ttc':
                #     rg_amount_currency = -(total_ttc_before_rg * rate)
                # else:
                #     rg_amount_currency = -(base_untaxed_currency * rate)
                #
                # rg_amount_company = move.currency_id._convert(
                #     rg_amount_currency, move.company_id.currency_id, move.company_id, move.invoice_date or move.date
                # )
                #
                # # Formatting helper
                # def format_num(amount):
                #     return formatLang(self.env, amount, currency_obj=currency)
                #
                # # Update the RG group objects with correct values
                # for group in rg_groups:
                #     group.update({
                #         'tax_amount_currency': rg_amount_currency,
                #         'tax_amount': rg_amount_company,
                #         'formatted_tax_group_amount': format_num(rg_amount_currency),
                #     })
                #
                # # If no RG groups were found in standard totals but we have taxes, create one
                # if not rg_groups and rg_taxes:
                #     rg_groups.append({
                #         'id': rg_tax_group_ids[0],
                #         'group_name': rg_taxes[0].name,
                #         'tax_amount_currency': rg_amount_currency,
                #         'tax_amount': rg_amount_company,
                #         'formatted_tax_group_amount': format_num(rg_amount_currency),
                #         'base_amount_currency': base_untaxed_currency,
                #         'base_amount': move.currency_id._convert(base_untaxed_currency, move.company_id.currency_id, move.company_id, move.invoice_date or move.date),
                #         'display_base_amount_currency': False,
                #         'display_base_amount': False,
                #     })
                #
                # # Construct DUAL SUBTOTALS structure
                # # Widget template reads: subtotal.name, subtotal.base_amount_currency, taxGroup.group_name, taxGroup.tax_amount_currency
                # # 1. "MONTANT HTVA" + VAT groups  → shows HT amount with TVA lines below
                # # 2. "MONTANT TTC"  + RG groups   → shows TTC amount with RG deduction below
                #
                # new_subtotals = []
                #
                # # Subtotal 1: Untaxed amount label + VAT lines below
                # new_subtotals.append({
                #     'name': 'MONTANT HTVA',
                #     'base_amount_currency': base_untaxed_currency,       # key used by widget (line 53 of template)
                #     'base_amount': move.currency_id._convert(
                #         base_untaxed_currency, move.company_id.currency_id, move.company_id, move.invoice_date or move.date
                #     ),
                #     'tax_groups': vat_groups,
                # })
                #
                # # Subtotal 2: TTC amount label + RG deduction line below
                # new_subtotals.append({
                #     'name': 'MONTANT TTC',
                #     'base_amount_currency': total_ttc_before_rg,         # key used by widget (line 53 of template)
                #     'base_amount': move.currency_id._convert(
                #         total_ttc_before_rg, move.company_id.currency_id, move.company_id, move.invoice_date or move.date
                #     ),
                #     'tax_groups': rg_groups,
                # })
                #
                # totals['subtotals'] = new_subtotals
                #
                # # Update final total amounts
                # totals['tax_amount_currency'] = other_taxes_sum_currency + rg_amount_currency
                # totals['total_amount_currency'] = base_untaxed_currency + totals['tax_amount_currency']
                # totals['formatted_tax_amount_currency'] = format_num(totals['tax_amount_currency'])
                # totals['formatted_total_amount_currency'] = format_num(totals['total_amount_currency'])
                #
                # if 'tax_amount' in totals:
                #     totals['tax_amount'] = sum(g['tax_amount'] for s in totals['subtotals'] for g in s['tax_groups'])
                #     totals['total_amount'] = totals.get('amount_untaxed', 0.0) + totals.get('tax_amount', 0.0)
                #
                # # PDF Report Data Pro-rating
                # if total_ttc_before_rg > 0:
                #     rg_ht_portion = rg_amount_currency * (base_untaxed_currency / total_ttc_before_rg)
                #     rg_tva_portion = rg_amount_currency * (other_taxes_sum_currency / total_ttc_before_rg)
                # else:
                #     rg_ht_portion = rg_amount_currency
                #     rg_tva_portion = 0.0
                #
                # remaining_ht = base_untaxed_currency + rg_ht_portion
                # remaining_tva = other_taxes_sum_currency + rg_tva_portion
                #
                # totals['custom_guarantee_info'] = {
                #     'rg_name': rg_taxes[0].name,
                #     'total_ht_original': base_untaxed_currency,
                #     'formatted_total_ht_original': format_num(base_untaxed_currency),
                #     'total_vat_original': other_taxes_sum_currency,
                #     'formatted_total_vat_original': format_num(other_taxes_sum_currency),
                #     'total_ttc_before_rg': total_ttc_before_rg,
                #     'formatted_total_ttc_before_rg': format_num(total_ttc_before_rg),
                #     'rg_amount': abs(rg_amount_currency),
                #     'formatted_rg_amount': format_num(abs(rg_amount_currency)),
                #     'total_ttc_after_rg': totals['total_amount_currency'],
                #     'formatted_total_ttc_after_rg': format_num(totals['total_amount_currency']),
                #     'remaining_ht': remaining_ht,
                #     'formatted_remaining_ht': format_num(remaining_ht),
                #     'remaining_tva': remaining_tva,
                #     'formatted_remaining_tva': format_num(remaining_tva),
                # }
                #
                # move.tax_totals = totals