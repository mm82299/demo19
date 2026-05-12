# -*- coding: utf-8 -*-
"""
Deferred Expense management on account.move and account.move.line.

Architecture: mirrors Odoo Enterprise account_accountant approach:
  - No dedicated model — deferral entries ARE account.move records.
  - Originating bill → deferred_move_ids (Many2many via account_move_deferred_expense_rel)
  - Deferral moves   → deferred_original_move_ids (inverse of the above)
  - Dates live on account.move.line: deferred_start_date / deferred_end_date
  - auto_post='at_date' lets Odoo's native scheduler post moves when due.
"""
import calendar
from contextlib import contextmanager
from itertools import chain
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command


# ─────────────────────────────────────────────────────────────────────────────
# AccountMove
# ─────────────────────────────────────────────────────────────────────────────

class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Deferred management fields ────────────────────────────────────────────

    deferred_move_ids = fields.Many2many(
        string='Deferred Entries',
        comodel_name='account.move',
        relation='account_move_deferred_expense_rel',
        column1='original_move_id',
        column2='deferred_move_id',
        help='The deferred entries created by this invoice.',
        copy=False,
    )

    deferred_original_move_ids = fields.Many2many(
        string='Original Invoices',
        comodel_name='account.move',
        relation='account_move_deferred_expense_rel',
        column1='deferred_move_id',
        column2='original_move_id',
        help='The original invoices that created these deferred entries.',
        copy=False,
    )

    deferred_entry_type = fields.Selection(
        string='Deferred Entry Type',
        selection=[('expense', 'Deferred Expense')],
        compute='_compute_deferred_entry_type',
        copy=False,
    )

    # ── Compute ───────────────────────────────────────────────────────────────

    @api.depends('deferred_original_move_ids')
    def _compute_deferred_entry_type(self):
        for move in self:
            if move.deferred_original_move_ids:
                move.deferred_entry_type = 'expense'
            else:
                move.deferred_entry_type = False

    # ── Override _post to auto-generate on validation ─────────────────────────

    def _post(self, soft=True):
        posted = super()._post(soft)
        for move in self:
            if (
                move.is_purchase_document(include_receipts=True)
                and move.company_id.generate_deferred_expense_entries_method == 'on_validation'
                and any(move.line_ids.mapped('deferred_start_date'))
            ):
                move._generate_deferred_expense_entries()
        return posted

    def button_draft(self):
        """When resetting to draft, unlink or reverse any deferral moves."""
        if any(
            len(deferral_move.deferred_original_move_ids) > 1
            for deferral_move in self.deferred_move_ids
        ):
            raise UserError(_(
                "You cannot reset to draft an invoice that is grouped in a deferral entry. "
                "Create a credit note instead."
            ))
        reversed_moves = self.deferred_move_ids._unlink_or_reverse()
        if reversed_moves:
            self.deferred_move_ids |= reversed_moves
        return super().button_draft()

    def _unlink_or_reverse(self):
        """
        Unlink draft deferral moves; reverse posted ones so ledger stays clean.
        Returns any reversal moves created.
        """
        draft_moves = self.filtered(lambda m: m.state == 'draft')
        posted_moves = self - draft_moves
        draft_moves.unlink()
        reversed_moves = self.env['account.move']
        if posted_moves:
            reversed_moves = posted_moves._reverse_moves(
                default_values_list=[{'date': m.date} for m in posted_moves]
            )
            reversed_moves.action_post()
        return reversed_moves

    # ═════════════════════════════════════════════════════════════════════════
    # Deferred Management Core
    # ═════════════════════════════════════════════════════════════════════════

    @api.model
    def _get_deferred_diff_dates(self, start, end):
        """
        Returns the number of months between two dates [start, end[.
        Uses 30-day months so Feb, Mar, Apr all get the same share.
        Identical to Enterprise implementation.
        """
        if start > end:
            start, end = end, start
        nb_months = end.month - start.month + 12 * (end.year - start.year)
        start_day = start.day
        end_day = end.day
        if start_day == calendar.monthrange(start.year, start.month)[1]:
            start_day = 30
        if end_day == calendar.monthrange(end.year, end.month)[1]:
            end_day = 30
        nb_days = end_day - start_day
        return (nb_months * 30 + nb_days) / 30

    @api.model
    def _get_deferred_period_amount(self, method, period_start, period_end, line_start, line_end, balance):
        """
        Amount to recognize for [period_start, period_end] given the computation method.
        Mirrors Enterprise _get_deferred_period_amount exactly.
        """
        if period_end <= line_start or period_end <= period_start:
            return 0
        if method == 'day':
            amount_per_day = balance / (line_end - line_start).days
            return (period_end - period_start).days * amount_per_day
        elif method in ('month', 'full_months'):
            if method == 'full_months':
                reset_day_1 = relativedelta(day=1)
                line_start = line_start + reset_day_1
                line_end = line_end + reset_day_1
                period_start = period_start + reset_day_1
                period_end = period_end + reset_day_1
            line_diff = self._get_deferred_diff_dates(line_end, line_start)
            period_diff = self._get_deferred_diff_dates(period_end, period_start)
            return period_diff / line_diff * balance if line_diff else balance
        return 0

    def _generate_deferred_expense_entries(self):
        """
        Generate deferral journal entries for all qualifying lines on this bill.

        For each qualifying line:
          Move 0 (dated = bill date, auto_post = at_date):
              DR deferred_account   (balance)
              CR expense_account    (balance)
          Moves 1..N (dated = end of each period, auto_post = at_date):
              DR expense_account    (period_amount)
              CR deferred_account   (period_amount)

        The `auto_post = 'at_date'` field causes Odoo's native daily cron
        (_cron_account_move_post) to post each move on its scheduled date.
        """
        self.ensure_one()
        if self.state != 'posted':
            return

        company = self.company_id
        deferred_account = company.deferred_expense_account_id
        deferred_journal = company.deferred_expense_journal_id
        method = company.deferred_expense_amount_computation_method

        if not deferred_journal:
            raise UserError(_("Please set the Deferred Expense Journal in Accounting Settings."))
        if not deferred_account:
            raise UserError(_("Please set the Deferred Expense Account in Accounting Settings."))

        lines = self.line_ids.filtered(lambda l: (
            l.account_id.internal_group == 'expense'
            and l.deferred_start_date
            and l.deferred_end_date
        ))
        if not lines:
            return

        moves_to_create = []
        lines_to_create = []  # parallel list of line vals lists

        for line in lines:
            periods = line._get_deferred_periods()
            if not periods:
                continue  # all in same month as bill → skip

            ref = _("Deferral of %s", line.move_id.name or '')
            start_date = line.deferred_start_date
            end_date = line.deferred_end_date

            # When full_months: check if effective period is < 2 months
            if method == 'full_months':
                if self._get_deferred_diff_dates(start_date.replace(day=1), end_date + relativedelta(days=1)) < 2:
                    end_date += relativedelta(months=-1)
            # If after adjustment all dates fall in same month, skip
            if start_date.replace(day=1) == end_date.replace(day=1) == line.date.replace(day=1):
                continue

            # ── Move 0: full deferral (expense → deferred account) ────────────
            move0_vals = {
                'move_type': 'entry',
                'deferred_original_move_ids': [Command.set(self.ids)],
                'journal_id': deferred_journal.id,
                'company_id': company.id,
                'partner_id': line.partner_id.id,
                'auto_post': 'at_date',
                'ref': ref,
                'name': False,
                'date': self.date,
            }
            move0_line_vals = [
                {
                    'account_id': line.account_id.id,
                    'balance': -line.balance,
                    'name': ref,
                    'analytic_distribution': line.analytic_distribution,
                    'product_id': line.product_id.id,
                    'partner_id': line.partner_id.id,
                },
                {
                    'account_id': deferred_account.id,
                    'balance': line.balance,
                    'name': ref,
                    'analytic_distribution': line.analytic_distribution,
                    'product_id': line.product_id.id,
                    'partner_id': line.partner_id.id,
                },
            ]
            moves_to_create.append((move0_vals, move0_line_vals, line, periods))

        if not moves_to_create:
            return

        # Create all move0 records
        created_move0s = []
        for (mv_vals, mv_line_vals, line, periods) in moves_to_create:
            m0 = self.env['account.move'].create(mv_vals)
            for lv in mv_line_vals:
                lv['move_id'] = m0.id
            self.env['account.move.line'].create(mv_line_vals)
            created_move0s.append((m0, line, periods))

        # Create period recognition moves (deferred → expense)
        all_deferral_moves = self.env['account.move']
        for (m0, line, periods) in created_move0s:
            remaining_balance = line.balance
            for i, period in enumerate(periods):
                is_last = (i == len(periods) - 1)
                if is_last:
                    period_amount = remaining_balance
                else:
                    period_amount = self._get_deferred_period_amount(
                        method,
                        period[0],
                        period[1] + relativedelta(days=1),
                        line.deferred_start_date,
                        line.deferred_end_date + relativedelta(days=1),
                        line.balance,
                    )
                    period_amount = line.currency_id.round(period_amount)
                    remaining_balance -= period_amount

                ref = _("Deferral of %s", line.move_id.name or '')
                dm = self.env['account.move'].create({
                    'move_type': 'entry',
                    'deferred_original_move_ids': [Command.set(self.ids)],
                    'journal_id': deferred_journal.id,
                    'company_id': company.id,
                    'partner_id': line.partner_id.id,
                    'auto_post': 'at_date',
                    'ref': ref,
                    'name': False,
                    'date': period[1],
                })
                self.env['account.move.line'].create([
                    {
                        'move_id': dm.id,
                        'account_id': deferred_account.id,
                        'balance': -period_amount,
                        'name': ref,
                        'analytic_distribution': line.analytic_distribution,
                        'product_id': line.product_id.id,
                        'partner_id': line.partner_id.id,
                    },
                    {
                        'move_id': dm.id,
                        'account_id': line.account_id.id,
                        'balance': period_amount,
                        'name': ref,
                        'analytic_distribution': line.analytic_distribution,
                        'product_id': line.product_id.id,
                        'partner_id': line.partner_id.id,
                    },
                ])
                all_deferral_moves |= dm

            # Link move0 to the original invoice
            self.deferred_move_ids |= m0
            self.deferred_move_ids |= all_deferral_moves

        # Remove zero-amount deferral moves
        zero_moves = all_deferral_moves.filtered(
            lambda m: m.currency_id.is_zero(m.amount_total)
        )
        zero_moves.unlink()

        # Post move0s immediately (they are dated = bill date)
        moves_to_post = self.env['account.move']
        for (m0, line, periods) in created_move0s:
            if m0.exists():
                moves_to_post |= m0
        if moves_to_post:
            moves_to_post._post(soft=True)

    # ── Smart button actions ──────────────────────────────────────────────────

    def open_deferred_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deferred Entries'),
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.deferred_move_ids.line_ids.ids)],
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            },
        }

    def open_deferred_original_entry(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Original Invoice'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.deferred_original_move_ids.ids)],
        }
        if len(self.deferred_original_move_ids) == 1:
            action.update({
                'res_id': self.deferred_original_move_ids[0].id,
                'view_mode': 'form',
            })
        return action


# ─────────────────────────────────────────────────────────────────────────────
# AccountMoveLine
# ─────────────────────────────────────────────────────────────────────────────

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # ── Deferred date fields (identical to Enterprise) ────────────────────────

    deferred_start_date = fields.Date(
        string='Start Date',
        compute='_compute_deferred_start_date',
        store=True,
        readonly=False,
        index='btree_not_null',
        copy=False,
        help='Date at which the deferred expense starts.',
    )

    deferred_end_date = fields.Date(
        string='End Date',
        index='btree_not_null',
        copy=False,
        help='Date at which the deferred expense ends.',
    )

    has_deferred_moves = fields.Boolean(compute='_compute_has_deferred_moves')

    has_abnormal_deferred_dates = fields.Boolean(compute='_compute_has_abnormal_deferred_dates')

    # ── Computed ──────────────────────────────────────────────────────────────

    def _compute_has_deferred_moves(self):
        for line in self:
            line.has_deferred_moves = bool(line.move_id.deferred_move_ids)

    @api.depends('deferred_start_date', 'deferred_end_date')
    def _compute_has_abnormal_deferred_dates(self):
        """
        Warn the user if the date range produces a non-round number of months
        (e.g. Jan 1 → Jan 1 next year = 12.03 months instead of 12).
        """
        from odoo.tools import float_compare
        for line in self:
            line.has_abnormal_deferred_dates = (
                line.deferred_start_date
                and line.deferred_end_date
                and line.deferred_start_date != line.deferred_end_date
                and float_compare(
                    self.env['account.move']._get_deferred_diff_dates(
                        line.deferred_start_date,
                        line.deferred_end_date + relativedelta(days=1),
                    ) % 1,
                    1 / 30,
                    precision_digits=2,
                ) == 0
            )

    @api.depends('deferred_end_date', 'move_id.invoice_date', 'move_id.state')
    def _compute_deferred_start_date(self):
        """Auto-fill start date from invoice date when only end date is set."""
        for line in self:
            if not line.deferred_start_date and line.move_id.invoice_date and line.deferred_end_date:
                line.deferred_start_date = line.move_id.invoice_date

    # ── Onchange ──────────────────────────────────────────────────────────────

    @api.onchange('deferred_start_date', 'account_id')
    def _onchange_deferred_start_date(self):
        if not self._has_deferred_compatible_account():
            self.deferred_start_date = False
        if self.deferred_start_date and not self.deferred_end_date:
            self.deferred_end_date = self.deferred_start_date

    @api.onchange('deferred_end_date', 'account_id')
    def _onchange_deferred_end_date(self):
        if not self._has_deferred_compatible_account():
            self.deferred_end_date = False
        if self.deferred_start_date and not self.deferred_end_date:
            self.deferred_end_date = self.deferred_start_date

    def _has_deferred_compatible_account(self):
        """Only expense accounts on purchase documents are eligible."""
        self.ensure_one()
        return (
            self.move_id.is_purchase_document(include_receipts=True)
            and self.account_id.internal_group == 'expense'
        ) or (
            self.move_id.is_entry()
            and self.account_id.internal_group == 'expense'
        )

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('deferred_start_date', 'deferred_end_date', 'account_id')
    def _check_deferred_dates(self):
        for line in self:
            if line.deferred_start_date and not line.deferred_end_date:
                raise UserError(_(
                    "You cannot create a deferred entry with a start date but no end date."
                ))
            if (
                line.deferred_start_date
                and line.deferred_end_date
                and line.deferred_start_date > line.deferred_end_date
            ):
                raise UserError(_(
                    "You cannot create a deferred entry with a start date later than the end date."
                ))

    def write(self, vals):
        """Prevent changing account of a deferred line that already has moves."""
        if 'account_id' in vals:
            for line in self:
                if (
                    line.has_deferred_moves
                    and line.deferred_start_date
                    and line.deferred_end_date
                    and vals['account_id'] != line.account_id.id
                ):
                    raise UserError(_(
                        "You cannot change the account for a deferred line in %(move_name)s "
                        "if it has already been deferred.",
                        move_name=line.move_id.display_name,
                    ))
        return super().write(vals)

    # ── Period helpers ────────────────────────────────────────────────────────

    @api.model
    def _get_deferred_ends_of_month(self, start_date, end_date):
        """
        Returns list of end-of-month dates from start_date to end_date (inclusive).
        Mirrors Enterprise _get_deferred_ends_of_month.
        """
        dates = []
        while start_date <= end_date:
            start_date = start_date + relativedelta(day=31)
            dates.append(start_date)
            start_date = start_date + relativedelta(days=1)
        return dates

    def _get_deferred_periods(self):
        """
        Returns list of (period_start, period_end, 'current') tuples
        for each calendar month in [deferred_start_date, deferred_end_date].
        Returns [] if only one period and it coincides with the move date
        (no deferral needed — bill and recognition are in same month).
        """
        self.ensure_one()
        periods = [
            (
                max(self.deferred_start_date, d.replace(day=1)),
                min(d, self.deferred_end_date),
                'current',
            )
            for d in self._get_deferred_ends_of_month(
                self.deferred_start_date, self.deferred_end_date
            )
        ]
        if not periods:
            return []
        if len(periods) == 1 and periods[0][0].replace(day=1) == self.date.replace(day=1):
            return []
        return periods
