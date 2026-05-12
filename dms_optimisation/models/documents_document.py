# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    sinistre_dossier_id = fields.Many2one(
        'dms.sinistre.dossier', string='Dossier Sinistre',
        index=True, ondelete='set null',
        help="Dossier sinistre CTAMA lié à ce document.")
    dms_document_type_id = fields.Many2one(
        'dms.document.type', string='Type de Document DMS',
        help="Classification du document (PV, Facture, Photo, etc.)")
