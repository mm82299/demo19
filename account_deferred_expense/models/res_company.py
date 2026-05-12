# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Deferred Expense (matching Enterprise field names exactly) ─────────────

    deferred_expense_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Deferred Expense Journal',
    )

    deferred_expense_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Deferred Expense Account',
    )

    generate_deferred_expense_entries_method = fields.Selection(
        string='Generate Deferred Expense Entries',
        selection=[
            ('on_validation', 'On bill validation'),
            ('manual', 'Manually & Grouped'),
        ],
        default='on_validation',
        required=True,
    )

    deferred_expense_amount_computation_method = fields.Selection(
        string='Deferred Expense Based on',
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('full_months', 'Full Months'),
        ],
        default='month',
        required=True,
    )
