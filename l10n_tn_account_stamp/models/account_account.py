# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    is_stamp_account = fields.Boolean('Is Stamp Account', default=False)
