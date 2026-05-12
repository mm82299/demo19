# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Deferred Expense (matching Enterprise field names exactly) ─────────────

    deferred_expense_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Deferred Expense Journal',
        related='company_id.deferred_expense_journal_id',
        readonly=False,
        help='Journal used for deferred entries.',
    )

    deferred_expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Deferred Expense Account',
        related='company_id.deferred_expense_account_id',
        readonly=False,
        help='Account used for deferred expenses.',
    )

    generate_deferred_expense_entries_method = fields.Selection(
        related='company_id.generate_deferred_expense_entries_method',
        readonly=False,
        required=True,
        help='Method used to generate deferred entries.',
    )

    deferred_expense_amount_computation_method = fields.Selection(
        related='company_id.deferred_expense_amount_computation_method',
        readonly=False,
        required=True,
        help='Method used to compute the amount of deferred entries.',
    )
