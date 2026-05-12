# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    """ This model represents stock.move."""
    _inherit = 'stock.move'

    def _action_assign(self):
        res = super()._action_assign()
        print('res',res)

        for move in self:
            picking = move.picking_id
            print('picking', picking.sale_id)
            print('picking', picking.company_id.implement_sav_module)
            print('picking', move.sale_line_id)
            print('picking', move.sale_line_id.lot_id)
            print('picking', move.move_line_ids)

            if not (
                    picking
                    and picking.sale_id
                    and picking.company_id.implement_sav_module
                    and move.sale_line_id
                    and move.sale_line_id.lot_id
            ):
                continue

            move.write({
                'lot_ids': [(4, move.sale_line_id.lot_id.id)]
            })

        return res

