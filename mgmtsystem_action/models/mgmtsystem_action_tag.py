# Copyright (C) 2010 Savoir-faire Linux (<http://www.savoirfairelinux.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MgmtsystemActionTag(models.Model):
    _name = "mgmtsystem.action.tag"
    _description = "Action Tags"

    name = fields.Char(required=True)
    color = fields.Integer(string="Color Index", default=10)


    @api.constrains('name')
    def _check_unique_name_company(self):
        for record in self:
            if record.name:
                domain = [
                    ('name', '=', record.name),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError(_("Tag name already exists !!"))
