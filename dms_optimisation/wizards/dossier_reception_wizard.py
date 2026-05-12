# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DmsDossierReceptionWizard(models.TransientModel):
    _name = 'dms.dossier.reception.wizard'
    _description = 'Assistant de Réception de Dossier'

    # ── Champs du wizard ────────────────────────────────────────────
    workflow_model = fields.Selection([
        ('A', 'Modèle A — Recours par Compagnie'),
        ('B', 'Modèle B — Défense par Compagnie'),
        ('C', 'Modèle C — Fonds Perdus'),
        ('D', 'Modèle D — Défense PEC'),
        ('E', 'Modèle E — Recours PEC'),
        ('F', 'Modèle F — Courrier Divers'),
        ('G', 'Modèle G — Honoraires Experts'),
        ('H', 'Modèle H — Documents Physiques / Archives'),
    ], string='Modèle de Workflow', required=True)

    type_sinistre = fields.Selection([
        ('corporel', 'Corporel'),
        ('materiel', 'Matériel'),
        ('mixte', 'Mixte'),
    ], string='Type de Sinistre', required=True)

    is_new_dossier = fields.Boolean(
        string='Nouveau Dossier', default=True,
        help="Décocher si le dossier existe déjà dans les archives.")
    existing_dossier_id = fields.Many2one(
        'dms.sinistre.dossier', string='Dossier Existant',
        help="Sélectionner le dossier existant à reprendre des archives.")

    partner_id = fields.Many2one('res.partner', string='Assuré')
    company_adverse_id = fields.Many2one(
        'dms.insurance.company', string='Compagnie Adverse')
    gestionnaire_id = fields.Many2one(
        'res.users', string='Gestionnaire')
    nature_fonds_perdus = fields.Selection([
        ('connexe', 'Connexe'),
        ('tous_risques_sans_tiers', 'Tous Risques sans Tiers'),
        ('bg', 'BG'),
        ('em_mp_cat', 'EM / MP / CAT'),
        ('defense_divers', 'Défense Divers'),
        ('vol', 'VOL'),
        ('incendie', 'Incendies'),
    ], string='Nature Fonds Perdus')
    document_type_ids = fields.Many2many(
        'dms.document.type', string='Types de Documents Reçus')
    amount = fields.Float(string='Montant (DT)')
    notes = fields.Text(string='Notes')

    # ── Actions ─────────────────────────────────────────────────────

    def action_create_or_resume_dossier(self):
        """Create a new dossier or resume an existing one from archive."""
        self.ensure_one()

        if self.is_new_dossier:
            # Create new dossier
            vals = {
                'type_sinistre': self.type_sinistre,
                'workflow_model': self.workflow_model,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'company_adverse_id': (
                    self.company_adverse_id.id
                    if self.company_adverse_id else False),
                'gestionnaire_id': (
                    self.gestionnaire_id.id
                    if self.gestionnaire_id else False),
                'nature_fonds_perdus': self.nature_fonds_perdus,
                'document_type_ids': [(6, 0, self.document_type_ids.ids)],
                'amount': self.amount,
                'notes': self.notes,
                'is_identified': False,
            }
            dossier = self.env['dms.sinistre.dossier'].create(vals)
            dossier.action_receive()
        else:
            # Resume existing dossier from archive
            dossier = self.existing_dossier_id
            if not dossier:
                return
            stage_gestionnaire = self.env.ref(
                'dms_optimisation.stage_gestionnaire',
                raise_if_not_found=False)
            update_vals = {
                'is_identified': True,
            }
            if self.gestionnaire_id:
                update_vals['gestionnaire_id'] = self.gestionnaire_id.id
            if stage_gestionnaire:
                update_vals['stage_id'] = stage_gestionnaire.id
            if self.notes:
                update_vals['notes'] = self.notes
            dossier.write(update_vals)

        # Return to the dossier form
        return {
            'name': _('Dossier Sinistre'),
            'type': 'ir.actions.act_window',
            'res_model': 'dms.sinistre.dossier',
            'view_mode': 'form',
            'res_id': dossier.id,
            'target': 'current',
        }
