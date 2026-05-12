# -*- coding: utf-8 -*-
"""
Manual & Grouped Deferral Entry Generation Wizard.

Mirrors the Enterprise approach for the 'Manually & Grouped' mode:
At the end of each month the accountant clicks "Generate Entries" which creates:

  Entry 1 (dated = last day of month):
    - Line: Expense account   CREDIT = sum of all bill totals
    - Line: Expense account   DEBIT  = amounts recognized this month
    - Line: Deferred account  DEBIT  = amounts still to be deferred

  Entry 2 (dated = first day of next month): Full reversal of Entry 1
"""
import calendar
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round, groupby as tools_groupby


class AccountDeferredGenerateWizard(models.TransientModel):
    _name = 'account.deferred.generate.wizard'
    _description = 'Generate Grouped Deferred Expense Entries'

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
        Generate two grouped entries for all deferred expense lines in the period.
        Returns an action opening the two created journal entries.
        """
        self.ensure_one()
        company = self.company_id
        if company.generate_deferred_expense_entries_method != 'manual':
            raise UserError(_("This wizard is only available in 'Manually & Grouped' mode."))

        journal = company.deferred_expense_journal_id
        deferred_account = company.deferred_expense_account_id
        method = company.deferred_expense_amount_computation_method

        if not journal:
            raise UserError(_("Please configure a Deferred Expense Journal in Accounting Settings."))
        if not deferred_account:
            raise UserError(_("Please configure a Deferred Expense Account in Accounting Settings."))

        period_end = self.date_end
        period_start = period_end.replace(day=1)
        reversal_date = period_end + relativedelta(days=1)

        # ── Fetch all qualifying lines ─────────────────────────────────────────
        # A qualifying line is one on a posted purchase bill with deferred dates
        # that overlap the current month.
        all_lines = self.env['account.move.line'].search([
            ('move_id.company_id', '=', company.id),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ('in_invoice', 'in_refund')),
            ('account_id.internal_group', '=', 'expense'),
            ('deferred_start_date', '<=', period_end),
            ('deferred_end_date', '>=', period_start),
        ])

        if not all_lines:
            raise UserError(_(
                "No deferred expense lines found for the period ending %s."
            ) % period_end)

        # ── Aggregate by (expense_account, deferred_account) ──────────────────
        # For each group:
        #   total_amount  = sum of all line balances
        #   period_amount = what is recognized this period

        Move = self.env['account.move']
        AML = self.env['account.move.line']

        groups = {}  # key: (expense_account_id, deferred_account_id)
        for line in all_lines:
            key = (line.account_id.id, deferred_account.id)
            if key not in groups:
                groups[key] = {
                    'expense_account_id': line.account_id.id,
                    'deferred_account_id': deferred_account.id,
                    'total_balance': 0.0,
                    'period_balance': 0.0,
                }
            groups[key]['total_balance'] += line.balance
            period_balance = Move._get_deferred_period_amount(
                Move,
                method,
                max(line.deferred_start_date, period_start),
                min(line.deferred_end_date, period_end) + relativedelta(days=1),
                line.deferred_start_date,
                line.deferred_end_date + relativedelta(days=1),
                line.balance,
            )
            groups[key]['period_balance'] += period_balance

        # ── Build journal entry lines ──────────────────────────────────────────
        entry1_lines = []
        for key, data in groups.items():
            total = data['total_balance']
            recognized = float_round(data['period_balance'], precision_digits=2)
            remaining = float_round(total - recognized, precision_digits=2)

            # Line 1: Cancel totals (credit expense)
            entry1_lines.append(Command.create({
                'name': _('Deferred Expense – Cancellation'),
                'account_id': data['expense_account_id'],
                'balance': -total,
            }))
            # Line 2: Recognize this period (debit expense)
            if recognized:
                entry1_lines.append(Command.create({
                    'name': _('Deferred Expense – Recognition'),
                    'account_id': data['expense_account_id'],
                    'balance': recognized,
                }))
            # Line 3: Park the remainder in the deferred account
            if remaining:
                entry1_lines.append(Command.create({
                    'name': _('Deferred Expense – Deferred Balance'),
                    'account_id': data['deferred_account_id'],
                    'balance': remaining,
                }))

        if not entry1_lines:
            raise UserError(_("Nothing to process for this period."))

        ref1 = _("Grouped Deferred Expenses – %s") % period_end.strftime('%B %Y')
        ref2 = _("Reversal – Grouped Deferred Expenses – %s") % period_end.strftime('%B %Y')

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
            vals = cmd[2]  # (0, 0, {vals})
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
            'name': _('Generated Deferred Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', [entry1.id, entry2.id])],
        }
