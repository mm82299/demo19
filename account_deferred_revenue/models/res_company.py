# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Deferred Revenue (matching Enterprise field names exactly) ─────────────

    deferred_revenue_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Deferred Revenue Journal',
    )

    deferred_revenue_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Deferred Revenue Account',
    )

    generate_deferred_revenue_entries_method = fields.Selection(
        string='Generate Deferred Revenue Entries',
        selection=[
            ('on_validation', 'On invoice validation'),
            ('manual', 'Manually & Grouped'),
        ],
        default='on_validation',
        required=True,
    )

    deferred_revenue_amount_computation_method = fields.Selection(
        string='Deferred Revenue Based on',
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('full_months', 'Full Months'),
        ],
        default='month',
        required=True,
    )
