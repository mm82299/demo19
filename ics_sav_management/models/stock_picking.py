# -*- coding: utf-8 -*-
import logging
from odoo import fields, models,api

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    customs_file_ref = fields.Char(
        string='Customs File Reference',
        help='Customs reference automatically copied from the reception move line.',
        tracking=True,
    )


    def button_validate(self):
        """Override validation to inject SAV and customs logic."""
        res = super().button_validate()
        for picking in self:
            if picking.state == 'done':
                if picking.picking_type_code == 'outgoing' and picking.company_id.implement_sav_module:
                    picking._create_sav_records()
                elif picking.picking_type_code == 'incoming':
                    picking._write_customs_ref_to_lots()
        return res


    def _create_sav_records(self):
        SavRecord = self.env['sav.record']
        sale = self.sale_id

        for ml in self.move_line_ids.filtered(
            lambda l: l.lot_id and l.product_id.product_tmpl_id.track_lifecycle
        ):
            # Avoid duplicates
            existing = SavRecord.search([
                ('lot_id', '=', ml.lot_id.id),
                ('picking_id', '=', self.id),
            ], limit=1)
            if existing:
                continue

            # Determine sale order line for this move line
            sol = ml.move_id.sale_line_id if ml.move_id else False

            # Build lifecycle lines from product template
            lifecycle_vals = []
            for rule in ml.product_id.product_tmpl_id.lifecycle_ids:
                lifecycle_vals.append((0, 0, {
                    'maintenance_type': rule.maintenance_type,
                    'odometer_type': rule.odometer_type,
                    'odometer_value': rule.odometer_value,
                    'spare_parts_ids': [(6 , 0, rule.spare_parts_ids.ids)],
                    'state': 'draft',
                }))

            sav_vals = {
                'name': ml.lot_id.name,
                'lot_id': ml.lot_id.id,
                'product_id': ml.product_id.id,
                'picking_id': self.id,
                'sale_order_id': sale.id if sale else False,
                'delivery_date': fields.Date.today(),
                'sav_lifecycle_ids': lifecycle_vals,
                'company_id': self.company_id.id,
            }
            try:
                SavRecord.create(sav_vals)
            except Exception as e:
                _logger.error(
                    "SAV: Failed to create sav.record for lot %s on picking %s: %s",
                    ml.lot_id.name, self.name, e
                )

    def _write_customs_ref_to_lots(self):
        for rec in self:
            for move in rec.move_ids:
                for move_line in move.move_line_ids:
                    if move_line.lot_id:
                        move_line.lot_id.sudo().customs_file_ref = rec.customs_file_ref
