# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Deferred Revenue (matching Enterprise field names exactly) ─────────────

    deferred_revenue_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Deferred Revenue Journal',
        related='company_id.deferred_revenue_journal_id',
        readonly=False,
        help='Journal used for deferred revenue entries.',
    )

    deferred_revenue_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Deferred Revenue Account',
        related='company_id.deferred_revenue_account_id',
        readonly=False,
        help='Account used for deferred revenues.',
    )

    generate_deferred_revenue_entries_method = fields.Selection(
        related='company_id.generate_deferred_revenue_entries_method',
        readonly=False,
        required=True,
        help='Method used to generate deferred revenue entries.',
    )

    deferred_revenue_amount_computation_method = fields.Selection(
        related='company_id.deferred_revenue_amount_computation_method',
        readonly=False,
        required=True,
        help='Method used to compute the amount of deferred revenue entries.',
    )
