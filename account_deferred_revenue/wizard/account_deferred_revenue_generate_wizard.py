# -*- coding: utf-8 -*-
"""
Manual & Grouped Deferred Revenue Entry Generation Wizard.

At the end of each month the accountant clicks "Generate Entries":

  Entry 1 (dated = last day of month):
    - Line: Income account    DEBIT  = sum of all invoice totals (cancel)
    - Line: Income account    CREDIT = amounts recognized this month
    - Line: Deferred account  CREDIT = amounts still to be deferred

  Entry 2 (dated = first day of next month): Full reversal of Entry 1
"""
import calendar
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round
from odoo.fields import Command


class AccountDeferredRevenueGenerateWizard(models.TransientModel):
    _name = 'account.deferred.revenue.generate.wizard'
    _description = 'Generate Grouped Deferred Revenue Entries'

    date_end = fields.Date(
        string='End of Period',
        required=True,
        default=lambda self: date.today().replace(
            day=calendar.monthrange(date.today().year, date.today().month)[1]
        ),
        help='The last day of the month to generate entries for.',
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    def action_generate_entries(self):
        """
        Generate two grouped deferred revenue entries for the period.
        Returns an action opening the two created journal entries.
        """
        self.ensure_one()
        company = self.company_id

        if company.generate_deferred_revenue_entries_method != 'manual':
            raise UserError(_("This wizard is only available in 'Manually & Grouped' mode."))

        journal = company.deferred_revenue_journal_id
        deferred_account = company.deferred_revenue_account_id
        method = company.deferred_revenue_amount_computation_method

        if not journal:
            raise UserError(_("Please configure a Deferred Revenue Journal in Accounting Settings."))
        if not deferred_account:
            raise UserError(_("Please configure a Deferred Revenue Account in Accounting Settings."))

        period_end = self.date_end
        period_start = period_end.replace(day=1)
        reversal_date = period_end + relativedelta(days=1)

        # ── Fetch all qualifying lines ─────────────────────────────────────────
        all_lines = self.env['account.move.line'].search([
            ('move_id.company_id', '=', company.id),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('account_id.internal_group', '=', 'income'),
            ('deferred_start_date', '<=', period_end),
            ('deferred_end_date', '>=', period_start),
        ])

        if not all_lines:
            raise UserError(_(
                "No deferred revenue lines found for the period ending %s."
            ) % period_end)

        # ── Aggregate by (income_account, deferred_account) ───────────────────
        Move = self.env['account.move']
        groups = {}
        for line in all_lines:
            key = (line.account_id.id, deferred_account.id)
            if key not in groups:
                groups[key] = {
                    'income_account_id': line.account_id.id,
                    'deferred_account_id': deferred_account.id,
                    'total_balance': 0.0,
                    'period_balance': 0.0,
                }
            groups[key]['total_balance'] += line.balance
            period_balance = Move._get_deferred_revenue_period_amount(
                Move,
                method,
                max(line.deferred_start_date, period_start),
                min(line.deferred_end_date, period_end) + relativedelta(days=1),
                line.deferred_start_date,
                line.deferred_end_date + relativedelta(days=1),
                line.balance,
            )
            groups[key]['period_balance'] += period_balance

        # ── Build Entry 1 lines ───────────────────────────────────────────────
        entry1_lines = []
        for key, data in groups.items():
            total = data['total_balance']
            recognized = float_round(data['period_balance'], precision_digits=2)
            remaining = float_round(total - recognized, precision_digits=2)

            # Line 1: Debit income (cancel all invoices)
            entry1_lines.append(Command.create({
                'name': _('Deferred Revenue – Cancellation'),
                'account_id': data['income_account_id'],
                'balance': -total,
            }))
            # Line 2: Credit income (recognize this period)
            if recognized:
                entry1_lines.append(Command.create({
                    'name': _('Deferred Revenue – Recognition'),
                    'account_id': data['income_account_id'],
                    'balance': recognized,
                }))
            # Line 3: Credit deferred account (park remainder)
            if remaining:
                entry1_lines.append(Command.create({
                    'name': _('Deferred Revenue – Deferred Balance'),
                    'account_id': data['deferred_account_id'],
                    'balance': remaining,
                }))

        if not entry1_lines:
            raise UserError(_("Nothing to process for this period."))

        ref1 = _("Grouped Deferred Revenues – %s") % period_end.strftime('%B %Y')
        ref2 = _("Reversal – Grouped Deferred Revenues – %s") % period_end.strftime('%B %Y')

        entry1 = Move.create({
            'journal_id': journal.id,
            'date': period_end,
            'ref': ref1,
            'company_id': company.id,
            'line_ids': entry1_lines,
        })
        entry1.action_post()

        # ── Reversal entry ─────────────────────────────────────────────────────
        entry2_lines = []
        for cmd in entry1_lines:
            vals = cmd[2]
            entry2_lines.append(Command.create({
                'name': vals['name'],
                'account_id': vals['account_id'],
                'balance': -vals['balance'],
            }))

        entry2 = Move.create({
            'journal_id': journal.id,
            'date': reversal_date,
            'ref': ref2,
            'company_id': company.id,
            'line_ids': entry2_lines,
        })
        entry2.action_post()

        return {
            'name': _('Generated Deferred Revenue Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', [entry1.id, entry2.id])],
        }
