# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class DmsSinistreDossier(models.Model):
    _name = 'dms.sinistre.dossier'
    _description = 'Dossier Sinistre'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_reception desc, id desc'

    # ── Identification ──────────────────────────────────────────────
    name = fields.Char(
        string='Référence', required=True, copy=False, readonly=True,
        default=lambda self: _('Nouveau'))
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Société', default=lambda self: self.env.company)

    # ── Classification ──────────────────────────────────────────────
    type_sinistre = fields.Selection([
        ('corporel', 'Corporel'),
        ('materiel', 'Matériel'),
        ('mixte', 'Mixte'),
    ], string='Type de Sinistre', required=True, tracking=True)

    workflow_model = fields.Selection([
        ('A', 'Modèle A — Recours par Compagnie'),
        ('B', 'Modèle B — Défense par Compagnie'),
        ('C', 'Modèle C — Fonds Perdus'),
        ('D', 'Modèle D — Défense PEC'),
        ('E', 'Modèle E — Recours PEC'),
        ('F', 'Modèle F — Courrier Divers'),
        ('G', 'Modèle G — Honoraires Experts'),
        ('H', 'Modèle H — Documents Physiques / Archives'),
    ], string='Modèle de Workflow', required=True, tracking=True)

    is_identified = fields.Boolean(
        string='Dossier Identifié', default=False, tracking=True,
        help="Indique si le dossier est identifié ou non-identifié à la réception.")

    nature_fonds_perdus = fields.Selection([
        ('connexe', 'Connexe'),
        ('tous_risques_sans_tiers', 'Tous Risques sans Tiers'),
        ('bg', 'BG'),
        ('em_mp_cat', 'EM / MP / CAT'),
        ('defense_divers', 'Défense Divers'),
        ('vol', 'VOL'),
        ('incendie', 'Incendies'),
    ], string='Nature Fonds Perdus',
       help="Applicable pour les Modèles C et D.")

    # ── Parties ─────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Assuré', tracking=True, index=True)
    company_adverse_id = fields.Many2one(
        'dms.insurance.company', string='Compagnie Adverse', tracking=True,
        help="Compagnie d'assurance adverse (pour recours / défense).")

    # ── Workflow & Étapes ───────────────────────────────────────────
    stage_id = fields.Many2one(
        'dms.workflow.stage', string='Étape', tracking=True,
        group_expand='_read_group_stage_ids',
        default=lambda self: self._default_stage_id(),
        copy=False, index=True)
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('reception', 'Réception'),
        ('en_cours', 'En cours'),
        ('approbation', 'Approbation'),
        ('termine', 'Terminé'),
        ('archive', 'Archivé'),
    ], string='État', compute='_compute_state', store=True, tracking=True)

    # ── Montant & Approbation ───────────────────────────────────────
    amount = fields.Float(string='Montant (DT)', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.company.currency_id)
    approval_level = fields.Selection([
        ('none', 'Aucune'),
        ('chef_pole', 'Chef de Pôle'),
        ('direction_generale', 'Direction Générale'),
    ], string="Niveau d'Approbation", compute='_compute_approval_level',
       store=True, tracking=True)
    is_approved = fields.Boolean(
        string='Approuvé', default=False, tracking=True, copy=False)
    approved_by_id = fields.Many2one(
        'res.users', string='Approuvé par', tracking=True, copy=False)
    approval_date = fields.Datetime(
        string="Date d'Approbation", copy=False)

    # ── Assignation ─────────────────────────────────────────────────
    gestionnaire_id = fields.Many2one(
        'res.users', string='Gestionnaire', tracking=True, index=True)
    chef_pole_id = fields.Many2one(
        'res.users', string='Chef de Pôle', tracking=True)

    # ── Dates ───────────────────────────────────────────────────────
    date_reception = fields.Date(
        string='Date de Réception', default=fields.Date.context_today,
        tracking=True)
    date_creation = fields.Date(
        string='Date de Création', default=fields.Date.context_today)
    date_cloture = fields.Date(
        string='Date de Clôture', tracking=True, copy=False)

    # ── Archive ─────────────────────────────────────────────────────
    box_number = fields.Char(
        string='N° Boîte Archive',
        help="Numéro de la boîte d'archivage physique.")
    archive_number = fields.Char(
        string="N° d'Archive", readonly=True, copy=False,
        help="Numéro d'archive généré automatiquement.")

    # ── Documents ───────────────────────────────────────────────────
    document_ids = fields.One2many(
        'documents.document', 'sinistre_dossier_id',
        string='Documents')
    document_count = fields.Integer(
        string='Nombre de Documents', compute='_compute_document_count')
    document_type_ids = fields.Many2many(
        'dms.document.type', string='Types de Documents Reçus',
        help="Types de documents reçus dans ce dossier (Modèle F).")
    reception_folder_id = fields.Many2one(
        'documents.document', string='Dossier Réception / BO',
        compute='_compute_reception_folder_id', store=False)

    # ── Notes ───────────────────────────────────────────────────────
    notes = fields.Html(string='Notes')

    # ══════════════════════════════════════════════════════════════════
    # Default / Group expand
    # ══════════════════════════════════════════════════════════════════

    def _default_stage_id(self):
        return self.env['dms.workflow.stage'].search([], order='sequence', limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show all stages in kanban (even if empty)."""
        return self.env['dms.workflow.stage'].search([])

    # ══════════════════════════════════════════════════════════════════
    # Compute methods
    # ══════════════════════════════════════════════════════════════════

    @api.depends('stage_id', 'stage_id.state_mapping')
    def _compute_state(self):
        for rec in self:
            rec.state = rec.stage_id.state_mapping if rec.stage_id else 'brouillon'

    @api.depends('amount')
    def _compute_approval_level(self):
        for rec in self:
            if rec.amount > 100000:
                rec.approval_level = 'direction_generale'
            elif rec.amount > 20000:
                rec.approval_level = 'chef_pole'
            else:
                rec.approval_level = 'none'

    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def _compute_reception_folder_id(self):
        # Chercher le dossier 'Réception / BO' (type folder)
        folder = self.env['documents.document'].search([
            ('name', 'ilike', 'Réception'),
            ('type', '=', 'folder')
        ], limit=1)
        for rec in self:
            rec.reception_folder_id = folder.id if folder else False

    # ══════════════════════════════════════════════════════════════════
    # CRUD
    # ══════════════════════════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'dms.sinistre.dossier') or _('Nouveau')
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.state == 'archive' and not rec.archive_number:
                rec.archive_number = self.env['ir.sequence'].next_by_code('dms.sinistre.archive')
        return res

    # ══════════════════════════════════════════════════════════════════
    # Workflow Actions
    # ══════════════════════════════════════════════════════════════════

    def action_receive(self):
        """Réceptionner le dossier au Bureau d'Ordre."""
        stage = self.env.ref(
            'dms_optimisation.stage_bureau_ordre', raise_if_not_found=False)
        if stage:
            self.write({'stage_id': stage.id})

    def action_assign(self):
        """Transférer au Pôle Assistance."""
        stage = self.env.ref(
            'dms_optimisation.stage_pole_assistance', raise_if_not_found=False)
        if stage:
            self.write({'stage_id': stage.id})

    def action_process(self):
        """Assigner au Gestionnaire pour traitement."""
        stage = self.env.ref(
            'dms_optimisation.stage_gestionnaire', raise_if_not_found=False)
        if stage:
            self.write({'stage_id': stage.id})

    def action_request_approval(self):
        """Demander l'approbation (Chef de Pôle / Direction Générale)."""
        for rec in self:
            if rec.approval_level == 'none':
                raise UserError(_(
                    "Ce dossier ne nécessite pas d'approbation "
                    "(montant ≤ 20 000 DT)."))
            if rec.approval_level == 'chef_pole':
                stage = self.env.ref(
                    'dms_optimisation.stage_chef_pole',
                    raise_if_not_found=False)
            else:
                stage = self.env.ref(
                    'dms_optimisation.stage_direction_generale',
                    raise_if_not_found=False)
            if stage:
                rec.stage_id = stage.id

    def action_approve(self):
        """Approuver le dossier."""
        for rec in self:
            rec.write({
                'is_approved': True,
                'approved_by_id': self.env.uid,
                'approval_date': fields.Datetime.now(),
            })
            # After approval, move to Pôle Assistance for settlement
            stage = self.env.ref(
                'dms_optimisation.stage_pole_assistance',
                raise_if_not_found=False)
            if stage:
                rec.stage_id = stage.id

    def action_transfer_convention(self):
        """Transférer au Pôle Convention."""
        stage = self.env.ref(
            'dms_optimisation.stage_pole_convention',
            raise_if_not_found=False)
        if stage:
            self.write({'stage_id': stage.id})

    def action_archive_dossier(self):
        """Archiver le dossier."""
        stage = self.env.ref(
            'dms_optimisation.stage_archive', raise_if_not_found=False)
        if stage:
            self.write({'stage_id': stage.id})

    def action_close(self):
        """Clôturer le dossier (Statut T = Terminé)."""
        stage = self.env.ref(
            'dms_optimisation.stage_archive', raise_if_not_found=False)
        vals = {
            'date_cloture': fields.Date.context_today(self),
        }
        if stage:
            vals['stage_id'] = stage.id
        self.write(vals)

    def action_reset_draft(self):
        """Remettre en brouillon."""
        stage = self._default_stage_id()
        self.write({
            'stage_id': stage.id if stage else False,
            'is_approved': False,
            'approved_by_id': False,
            'approval_date': False,
            'date_cloture': False,
        })

    # ══════════════════════════════════════════════════════════════════
    # Smart button actions
    # ══════════════════════════════════════════════════════════════════

    def action_view_documents(self):
        """Open linked documents."""
        self.ensure_one()
        return {
            'name': _('Documents du Dossier'),
            'type': 'ir.actions.act_window',
            'res_model': 'documents.document',
            'view_mode': 'list,form',
            'domain': [('sinistre_dossier_id', '=', self.id)],
            'context': {'default_sinistre_dossier_id': self.id},
        }
