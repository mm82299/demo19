# -*- coding: utf-8 -*-
"""
Deferred Revenue management on account.move and account.move.line.

Architecture: mirrors Odoo Enterprise account_accountant approach (revenue side):
  - No dedicated model — deferral entries ARE account.move records.
  - Originating invoice → deferred_revenue_move_ids (Many2many via account_move_deferred_revenue_rel)
  - Deferral moves      → deferred_revenue_original_move_ids (inverse)
  - Dates live on account.move.line: deferred_start_date / deferred_end_date
    (same fields as the expense module — reused if both modules are installed)
  - auto_post='at_date' lets Odoo's native scheduler post moves when due.

Revenue flow (mirror of expense, opposite signs):
  Move 0 (dated = invoice date):
      DR income_account   (balance)   ← cancel the revenue immediately
      CR deferred_account (balance)   ← park in liability until earned

  Moves 1..N (dated = end of each period):
      DR deferred_account (amount)    ← release from liability
      CR income_account   (amount)    ← recognize the revenue
"""
import calendar
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_compare


# ─────────────────────────────────────────────────────────────────────────────
# AccountMove
# ─────────────────────────────────────────────────────────────────────────────

class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Deferred Revenue fields ───────────────────────────────────────────────

    deferred_revenue_move_ids = fields.Many2many(
        string='Deferred Revenue Entries',
        comodel_name='account.move',
        relation='account_move_deferred_revenue_rel',
        column1='original_move_id',
        column2='deferred_move_id',
        help='The deferred revenue entries created by this invoice.',
        copy=False,
    )

    deferred_revenue_original_move_ids = fields.Many2many(
        string='Original Invoices',
        comodel_name='account.move',
        relation='account_move_deferred_revenue_rel',
        column1='deferred_move_id',
        column2='original_move_id',
        help='The original invoices that created these deferred revenue entries.',
        copy=False,
    )

    is_deferred_revenue_entry = fields.Boolean(
        string='Is Deferred Revenue Entry',
        compute='_compute_is_deferred_revenue_entry',
        copy=False,
    )

    # ── Compute ───────────────────────────────────────────────────────────────

    @api.depends('deferred_revenue_original_move_ids')
    def _compute_is_deferred_revenue_entry(self):
        for move in self:
            move.is_deferred_revenue_entry = bool(move.deferred_revenue_original_move_ids)

    # ── Override _post to auto-generate on validation ─────────────────────────

    def _post(self, soft=True):
        posted = super()._post(soft)
        for move in self:
            if (
                move.is_sale_document(include_receipts=True)
                and move.company_id.generate_deferred_revenue_entries_method == 'on_validation'
                and any(move.line_ids.mapped('deferred_start_date'))
            ):
                move._generate_deferred_revenue_entries()
        return posted

    def button_draft(self):
        """When resetting to draft, unlink or reverse any deferred revenue moves."""
        if any(
            len(dm.deferred_revenue_original_move_ids) > 1
            for dm in self.deferred_revenue_move_ids
        ):
            raise UserError(_(
                "You cannot reset to draft an invoice that is grouped in a deferred revenue entry. "
                "Create a credit note instead."
            ))
        reversed_moves = self.deferred_revenue_move_ids._unlink_or_reverse_revenue()
        if reversed_moves:
            self.deferred_revenue_move_ids |= reversed_moves
        return super().button_draft()

    def _unlink_or_reverse_revenue(self):
        """Unlink draft moves; reverse posted ones."""
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
    # Deferred Revenue Core (mirrors expense logic, opposite account sign)
    # ═════════════════════════════════════════════════════════════════════════

    @api.model
    def _get_deferred_revenue_diff_dates(self, start, end):
        """
        Returns the number of months between two dates [start, end[.
        Uses 30-day months (same algorithm as Enterprise).
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
    def _get_deferred_revenue_period_amount(self, method, period_start, period_end, line_start, line_end, balance):
        """
        Amount to recognize for [period_start, period_end] given the computation method.
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
            line_diff = self._get_deferred_revenue_diff_dates(line_end, line_start)
            period_diff = self._get_deferred_revenue_diff_dates(period_end, period_start)
            return period_diff / line_diff * balance if line_diff else balance
        return 0

    def _generate_deferred_revenue_entries(self):
        """
        Generate deferred revenue journal entries for all qualifying lines.

        For each income line with deferred dates:
          Move 0 (bill date, auto_post=at_date):
              DR income_account   (balance) — cancel the revenue
              CR deferred_account (balance) — park in deferred liability

          Moves 1..N (end of each period, auto_post=at_date):
              DR deferred_account (period_amount) — release from liability
              CR income_account   (period_amount) — recognize the revenue
        """
        self.ensure_one()
        if self.state != 'posted':
            return

        company = self.company_id
        deferred_account = company.deferred_revenue_account_id
        deferred_journal = company.deferred_revenue_journal_id
        method = company.deferred_revenue_amount_computation_method

        if not deferred_journal:
            raise UserError(_("Please set the Deferred Revenue Journal in Accounting Settings."))
        if not deferred_account:
            raise UserError(_("Please set the Deferred Revenue Account in Accounting Settings."))

        lines = self.line_ids.filtered(lambda l: (
            l.account_id.internal_group == 'income'
            and l.deferred_start_date
            and l.deferred_end_date
        ))
        if not lines:
            return

        all_deferral_moves = self.env['account.move']

        for line in lines:
            periods = line._get_deferred_revenue_periods()
            if not periods:
                continue

            ref = _("Deferral of %s", line.move_id.name or '')
            start_date = line.deferred_start_date
            end_date = line.deferred_end_date

            if method == 'full_months':
                if self._get_deferred_revenue_diff_dates(
                    start_date.replace(day=1), end_date + relativedelta(days=1)
                ) < 2:
                    end_date += relativedelta(months=-1)
            if start_date.replace(day=1) == end_date.replace(day=1) == line.date.replace(day=1):
                continue

            base_move_vals = {
                'move_type': 'entry',
                'deferred_revenue_original_move_ids': [Command.set(self.ids)],
                'journal_id': deferred_journal.id,
                'company_id': company.id,
                'partner_id': line.partner_id.id,
                'auto_post': 'at_date',
                'ref': ref,
                'name': False,
            }

            # ── Move 0: Transfer income → deferred liability ───────────────────
            m0 = self.env['account.move'].create({
                **base_move_vals,
                'date': self.date,
            })
            self.env['account.move.line'].create([
                {
                    'move_id': m0.id,
                    'account_id': line.account_id.id,
                    'balance': -line.balance,   # DR income (reverse credit)
                    'name': ref,
                    'analytic_distribution': line.analytic_distribution,
                    'product_id': line.product_id.id,
                    'partner_id': line.partner_id.id,
                },
                {
                    'move_id': m0.id,
                    'account_id': deferred_account.id,
                    'balance': line.balance,    # CR deferred liability
                    'name': ref,
                    'analytic_distribution': line.analytic_distribution,
                    'product_id': line.product_id.id,
                    'partner_id': line.partner_id.id,
                },
            ])
            self.deferred_revenue_move_ids |= m0

            # ── Moves 1..N: Periodic recognition (deferred → income) ──────────
            remaining_balance = line.balance
            for i, period in enumerate(periods):
                is_last = (i == len(periods) - 1)
                if is_last:
                    period_amount = remaining_balance
                else:
                    period_amount = self._get_deferred_revenue_period_amount(
                        method,
                        period[0],
                        period[1] + relativedelta(days=1),
                        line.deferred_start_date,
                        line.deferred_end_date + relativedelta(days=1),
                        line.balance,
                    )
                    period_amount = line.currency_id.round(period_amount)
                    remaining_balance -= period_amount

                dm = self.env['account.move'].create({
                    **base_move_vals,
                    'date': period[1],
                })
                self.env['account.move.line'].create([
                    {
                        'move_id': dm.id,
                        'account_id': deferred_account.id,
                        'balance': -period_amount,  # DR deferred liability
                        'name': ref,
                        'analytic_distribution': line.analytic_distribution,
                        'product_id': line.product_id.id,
                        'partner_id': line.partner_id.id,
                    },
                    {
                        'move_id': dm.id,
                        'account_id': line.account_id.id,
                        'balance': period_amount,   # CR income (recognize)
                        'name': ref,
                        'analytic_distribution': line.analytic_distribution,
                        'product_id': line.product_id.id,
                        'partner_id': line.partner_id.id,
                    },
                ])
                all_deferral_moves |= dm
                self.deferred_revenue_move_ids |= dm

        # Remove zero-amount moves
        zero_moves = all_deferral_moves.filtered(
            lambda m: m.currency_id.is_zero(m.amount_total)
        )
        zero_moves.unlink()

        # Post move0s immediately
        moves_to_post = self.deferred_revenue_move_ids.filtered(
            lambda m: m.exists() and m.date == self.date and m.state == 'draft'
        )
        if moves_to_post:
            moves_to_post._post(soft=True)

    # ── Smart button actions ──────────────────────────────────────────────────

    def open_deferred_revenue_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deferred Revenue Entries'),
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.deferred_revenue_move_ids.line_ids.ids)],
            'context': {
                'search_default_group_by_move': True,
                'expand': True,
            },
        }

    def open_deferred_revenue_original_entry(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Original Invoice'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.deferred_revenue_original_move_ids.ids)],
        }
        if len(self.deferred_revenue_original_move_ids) == 1:
            action.update({
                'res_id': self.deferred_revenue_original_move_ids[0].id,
                'view_mode': 'form',
            })
        return action


# ─────────────────────────────────────────────────────────────────────────────
# AccountMoveLine
# ─────────────────────────────────────────────────────────────────────────────

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    has_deferred_revenue_moves = fields.Boolean(
        compute='_compute_has_deferred_revenue_moves',
    )

    # ── Computed ──────────────────────────────────────────────────────────────

    def _compute_has_deferred_revenue_moves(self):
        for line in self:
            line.has_deferred_revenue_moves = bool(line.move_id.deferred_revenue_move_ids)

    # Note: deferred_start_date / deferred_end_date are already defined in the
    # account_deferred_expense module (or they are defined here if that module
    # is not installed). We add them defensively only if not yet present.

    def _has_deferred_revenue_compatible_account(self):
        """Only income accounts on sale documents are eligible."""
        self.ensure_one()
        return (
            self.move_id.is_sale_document(include_receipts=True)
            and self.account_id.internal_group == 'income'
        ) or (
            self.move_id.is_entry()
            and self.account_id.internal_group == 'income'
        )

    # ── Period helpers ────────────────────────────────────────────────────────

    @api.model
    def _get_deferred_revenue_ends_of_month(self, start_date, end_date):
        dates = []
        while start_date <= end_date:
            start_date = start_date + relativedelta(day=31)
            dates.append(start_date)
            start_date = start_date + relativedelta(days=1)
        return dates

    def _get_deferred_revenue_periods(self):
        """
        Returns list of (period_start, period_end, 'current') tuples
        for each calendar month in [deferred_start_date, deferred_end_date].
        Returns [] if only one period coinciding with the invoice date.
        """
        self.ensure_one()
        periods = [
            (
                max(self.deferred_start_date, d.replace(day=1)),
                min(d, self.deferred_end_date),
                'current',
            )
            for d in self._get_deferred_revenue_ends_of_month(
                self.deferred_start_date, self.deferred_end_date
            )
        ]
        if not periods:
            return []
        if len(periods) == 1 and periods[0][0].replace(day=1) == self.date.replace(day=1):
            return []
        return periods
