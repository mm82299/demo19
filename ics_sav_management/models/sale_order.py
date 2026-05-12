# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        print("confirm")
        res = super(SaleOrder, self).action_confirm(),
        print('res',res)
        return res
